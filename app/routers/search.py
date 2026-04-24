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
    PaginatedResponse,
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


async def search_external_sources(
    db: AsyncSession,
    query: str,
    limit: int,
) -> tuple[list[SongResponse], list[ArtistResponse], list[AlbumResponse]]:
    songs_responses: list[SongResponse] = []
    artists_responses: list[ArtistResponse] = []
    albums_responses: list[AlbumResponse] = []
    
    data_service = MusicDataService(db)
    seen_song_ids = set()
    seen_artist_ids = set()
    seen_album_ids = set()
    
    if settings.jamendo_client_id:
        try:
            async with JamendoClient() as client:
                jamendo_tracks = await client.search_tracks(query, limit)
                for track in jamendo_tracks[:limit]:
                    if track.id in seen_song_ids:
                        continue
                    seen_song_ids.add(track.id)
                    
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
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to cache Jamendo track: {e}")
        except Exception as e:
            logger.warning(f"Jamendo search failed: {e}")
    
    try:
        async with AudioDBClient() as client:
            audiodb_tracks = await client.search_tracks(query, limit)
            for track in audiodb_tracks[:limit]:
                if track.id in seen_song_ids:
                    continue
                seen_song_ids.add(track.id)
                
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
                    ))
                except Exception as e:
                    logger.warning(f"Failed to cache AudioDB track: {e}")
    except Exception as e:
        logger.warning(f"AudioDB search failed: {e}")
    
    if len(songs_responses) < 5:
        try:
            sample_generator = SampleDataGenerator()
            sample_tracks = sample_generator.search_tracks(query, limit)
            
            for track in sample_tracks[:limit]:
                if track.id in seen_song_ids:
                    continue
                seen_song_ids.add(track.id)
                
                try:
                    song = await data_service.cache_sample_track(track)
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
                    ))
                except Exception as e:
                    logger.warning(f"Failed to cache sample track: {e}")
        except Exception as e:
            logger.warning(f"Sample generator failed: {e}")
    
    if settings.jamendo_client_id:
        try:
            async with JamendoClient() as client:
                jamendo_artists = await client.search_artists(query, limit)
                for ja in jamendo_artists[:limit]:
                    if ja.id in seen_artist_ids:
                        continue
                    seen_artist_ids.add(ja.id)
                    
                    artist = await data_service.cache_jamendo_artist(ja)
                    artists_responses.append(ArtistResponse(
                        id=artist.id,
                        external_id=artist.external_id,
                        source=artist.source,
                        name=artist.name,
                        image_url=artist.image_url,
                    ))
        except Exception as e:
            logger.warning(f"Jamendo artist search failed: {e}")
    
    try:
        async with AudioDBClient() as client:
            audiodb_artists = await client.search_artists(query, limit)
            for aa in audiodb_artists[:limit]:
                if aa.id in seen_artist_ids:
                    continue
                seen_artist_ids.add(aa.id)
                
                artist = await data_service.cache_audiodb_artist(aa)
                artists_responses.append(ArtistResponse(
                    id=artist.id,
                    external_id=artist.external_id,
                    source=artist.source,
                    name=artist.name,
                    image_url=artist.image_url,
                ))
    except Exception as e:
        logger.warning(f"AudioDB artist search failed: {e}")
    
    if settings.jamendo_client_id:
        try:
            async with JamendoClient() as client:
                jamendo_albums = await client.search_albums(query, limit)
                for ja in jamendo_albums[:limit]:
                    if ja.id in seen_album_ids:
                        continue
                    seen_album_ids.add(ja.id)
                    
                    album = await data_service.cache_jamendo_album(ja)
                    if album.artist:
                        await db.refresh(album, ["artist"])
                    
                    albums_responses.append(AlbumResponse(
                        id=album.id,
                        external_id=album.external_id,
                        source=album.source,
                        name=album.name,
                        artist_name=album.artist.name if album.artist else None,
                        cover_url=album.cover_url,
                        release_date=album.release_date,
                    ))
        except Exception as e:
            logger.warning(f"Jamendo album search failed: {e}")
    
    try:
        async with AudioDBClient() as client:
            audiodb_albums = await client.search_albums(query, limit)
            for aa in audiodb_albums[:limit]:
                if aa.id in seen_album_ids:
                    continue
                seen_album_ids.add(aa.id)
                
                album = await data_service.cache_audiodb_album(aa)
                if album.artist:
                    await db.refresh(album, ["artist"])
                
                albums_responses.append(AlbumResponse(
                    id=album.id,
                    external_id=album.external_id,
                    source=album.source,
                    name=album.name,
                    artist_name=album.artist.name if album.artist else None,
                    cover_url=album.cover_url,
                    release_date=album.release_date,
                ))
    except Exception as e:
        logger.warning(f"AudioDB album search failed: {e}")
    
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
    offset = (page - 1) * limit
    
    response = SearchResultResponse()
    
    if type in ["all", "songs"]:
        local_songs = await search_songs_local(db, q, limit, offset)
        
        if not local_songs and use_external:
            external_songs, external_artists, external_albums = await search_external_sources(db, q, limit)
            response.songs = external_songs
            response.artists = external_artists
            response.albums = external_albums
        else:
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
                ))
    
    if type in ["all", "artists"] and not response.artists:
        local_artists = await search_artists_local(db, q, limit, offset)
        
        if not local_artists and use_external:
            _, external_artists, _ = await search_external_sources(db, q, limit)
            response.artists = external_artists
        else:
            for artist in local_artists:
                response.artists.append(ArtistResponse(
                    id=artist.id,
                    external_id=artist.external_id,
                    source=artist.source,
                    name=artist.name,
                    image_url=artist.image_url,
                ))
    
    if type in ["all", "albums"] and not response.albums:
        local_albums = await search_albums_local(db, q, limit, offset)
        
        if not local_albums and use_external:
            _, _, external_albums = await search_external_sources(db, q, limit)
            response.albums = external_albums
        else:
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
    )
