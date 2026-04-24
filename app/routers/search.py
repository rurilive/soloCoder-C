import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Song, Artist, Album
from app.models.schemas import (
    SongResponse,
    ArtistResponse,
    AlbumResponse,
    SearchResultResponse,
)
from app.services import (
    JamendoClient,
    AudioDBClient,
    SampleDataGenerator,
    MusicDataService,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api", tags=["search"])


async def search_songs_local(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> list[Song]:
    search_pattern = f"%{query}%"
    
    stmt = (
        select(Song)
        .where(
            or_(
                Song.name.ilike(search_pattern),
                Song.genre_name.ilike(search_pattern),
            )
        )
        .order_by(Song.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    songs = result.scalars().all()
    
    for song in songs:
        if song.artist_id:
            await db.refresh(song, ["artist"])
        if song.album_id:
            await db.refresh(song, ["album"])
    
    return songs


async def search_artists_local(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> list[Artist]:
    search_pattern = f"%{query}%"
    
    stmt = (
        select(Artist)
        .where(Artist.name.ilike(search_pattern))
        .order_by(Artist.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def search_albums_local(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> list[Album]:
    search_pattern = f"%{query}%"
    
    stmt = (
        select(Album)
        .where(Album.name.ilike(search_pattern))
        .order_by(Album.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    albums = result.scalars().all()
    
    for album in albums:
        if album.artist_id:
            await db.refresh(album, ["artist"])
    
    return albums


async def search_from_samples(
    query: str,
    limit: int,
) -> list[SongResponse]:
    songs_responses: list[SongResponse] = []
    
    try:
        sample_generator = SampleDataGenerator()
        sample_tracks = sample_generator.search_tracks(query, limit)
        
        for i, track in enumerate(sample_tracks[:limit]):
            songs_responses.append(SongResponse(
                id=i + 1000000,
                external_id=track.id,
                source="sample",
                name=track.name,
                artist_name=track.artist_name,
                album_name=track.album_name,
                duration=track.duration,
                cover_url=track.image,
                genre_name=track.genre,
                audio_url=track.audio_url,
            ))
    except Exception as e:
        logger.warning(f"Sample generator failed: {e}")
    
    return songs_responses


async def search_external_sources(
    db: AsyncSession,
    query: str,
    limit: int,
) -> tuple[list[SongResponse], list[ArtistResponse], list[AlbumResponse]]:
    songs_responses: list[SongResponse] = []
    artists_responses: list[ArtistResponse] = []
    albums_responses: list[AlbumResponse] = []
    
    data_service = MusicDataService(db)
    seen_ids = set()
    
    if settings.jamendo_client_id:
        try:
            async with JamendoClient() as client:
                jamendo_tracks = await client.search_tracks(query, limit)
                for track in jamendo_tracks[:limit]:
                    track_id = f"jamendo_{track.id}"
                    if track_id in seen_ids:
                        continue
                    seen_ids.add(track_id)
                    
                    try:
                        song = await data_service.cache_jamendo_track(track)
                        if song.artist:
                            await db.refresh(song, ["artist"])
                        if song.album:
                            await db.refresh(song, ["album"])
                        
                        songs_responses.append(SongResponse(
                            id=song.id,
                            external_id=song.external_id,
                            source=song.source,
                            name=song.name,
                            artist_name=song.artist.name if song.artist else None,
                            album_name=song.album.name if song.album else None,
                            duration=song.duration,
                            cover_url=song.cover_url,
                            genre_name=song.genre_name,
                            audio_url=song.audio_url,
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to cache Jamendo track: {e}")
                        songs_responses.append(SongResponse(
                            id=len(songs_responses) + 2000000,
                            external_id=track.id,
                            source="jamendo",
                            name=track.name,
                            artist_name=track.artist_name,
                            album_name=track.album_name,
                            duration=track.duration,
                            cover_url=track.image,
                            genre_name=None,
                            audio_url=track.audio,
                        ))
        except Exception as e:
            logger.warning(f"Jamendo search failed: {e}")
    
    if len(songs_responses) < 5:
        try:
            async with AudioDBClient() as client:
                audiodb_tracks = await client.search_tracks(query, limit)
                for track in audiodb_tracks[:limit]:
                    track_id = f"audiodb_{track.id}"
                    if track_id in seen_ids:
                        continue
                    seen_ids.add(track_id)
                    
                    try:
                        song = await data_service.cache_audiodb_track(track)
                        if song.artist:
                            await db.refresh(song, ["artist"])
                        if song.album:
                            await db.refresh(song, ["album"])
                        
                        songs_responses.append(SongResponse(
                            id=song.id,
                            external_id=song.external_id,
                            source=song.source,
                            name=song.name,
                            artist_name=song.artist.name if song.artist else None,
                            album_name=song.album.name if song.album else None,
                            duration=song.duration,
                            cover_url=song.cover_url,
                            genre_name=song.genre_name,
                            audio_url=song.audio_url,
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to cache AudioDB track: {e}")
                        songs_responses.append(SongResponse(
                            id=len(songs_responses) + 3000000,
                            external_id=track.id,
                            source="audiodb",
                            name=track.name,
                            artist_name=track.artist_name,
                            album_name=track.album_name,
                            duration=track.duration,
                            cover_url=track.image,
                            genre_name=track.genre,
                            audio_url=track.preview_url,
                        ))
        except Exception as e:
            logger.warning(f"AudioDB search failed: {e}")
    
    if len(songs_responses) < 10:
        sample_songs = await search_from_samples(query, limit)
        for song in sample_songs:
            track_id = f"sample_{song.external_id}"
            if track_id not in seen_ids:
                seen_ids.add(track_id)
                song.id = len(songs_responses) + 4000000
                songs_responses.append(song)
    
    return songs_responses, artists_responses, albums_responses


@router.get("/search", response_model=SearchResultResponse)
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    type: str = Query("all", description="搜索类型: songs, artists, albums, all"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    page: int = Query(1, ge=1, description="页码"),
    use_external: bool = Query(True, description="是否使用外部API搜索"),
    db: AsyncSession = Depends(get_db),
) -> SearchResultResponse:
    response = SearchResultResponse()
    
    if type in ["all", "songs"]:
        local_songs = await search_songs_local(db, q, limit, (page - 1) * limit)
        
        if local_songs:
            for song in local_songs:
                artist_name = song.artist.name if song.artist else None
                album_name = song.album.name if song.album else None
                response.songs.append(SongResponse(
                    id=song.id,
                    external_id=song.external_id,
                    source=song.source,
                    name=song.name,
                    artist_name=artist_name,
                    album_name=album_name,
                    duration=song.duration,
                    cover_url=song.cover_url,
                    genre_name=song.genre_name,
                    audio_url=song.audio_url,
                ))
        elif use_external:
            external_songs, external_artists, external_albums = await search_external_sources(db, q, limit)
            response.songs = external_songs
            response.artists = external_artists
            response.albums = external_albums
    
    if type in ["all", "artists"] and not response.artists:
        local_artists = await search_artists_local(db, q, limit, (page - 1) * limit)
        
        if local_artists:
            for artist in local_artists:
                response.artists.append(ArtistResponse(
                    id=artist.id,
                    external_id=artist.external_id,
                    source=artist.source,
                    name=artist.name,
                    image_url=artist.image_url,
                ))
    
    if type in ["all", "albums"] and not response.albums:
        local_albums = await search_albums_local(db, q, limit, (page - 1) * limit)
        
        if local_albums:
            for album in local_albums:
                artist_name = album.artist.name if album.artist else None
                response.albums.append(AlbumResponse(
                    id=album.id,
                    external_id=album.external_id,
                    source=album.source,
                    name=album.name,
                    artist_name=artist_name,
                    cover_url=album.cover_url,
                    release_date=album.release_date,
                ))
    
    response.total = len(response.songs) + len(response.artists) + len(response.albums)
    
    return response


@router.get("/songs/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: int,
    db: AsyncSession = Depends(get_db),
) -> SongResponse:
    stmt = select(Song).where(Song.id == song_id)
    result = await db.execute(stmt)
    song = result.scalar_one_or_none()
    
    if not song:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Song not found")
    
    if song.artist_id:
        await db.refresh(song, ["artist"])
    if song.album_id:
        await db.refresh(song, ["album"])
    
    return SongResponse(
        id=song.id,
        external_id=song.external_id,
        source=song.source,
        name=song.name,
        artist_name=song.artist.name if song.artist else None,
        album_name=song.album.name if song.album else None,
        duration=song.duration,
        cover_url=song.cover_url,
        genre_name=song.genre_name,
        audio_url=song.audio_url,
    )
