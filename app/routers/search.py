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
from app.services import JamendoClient, MusicDataService

logger = logging.getLogger(__name__)

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
            try:
                async with JamendoClient() as client:
                    jamendo_tracks = await client.search_tracks(q, limit)
                    data_service = MusicDataService(db)
                    cached_songs = await data_service.cache_jamendo_tracks(jamendo_tracks)
                    for song in cached_songs:
                        if song.artist:
                            artist_name = song.artist.name
                        else:
                            artist_name = None
                        if song.album:
                            album_name = song.album.name
                        else:
                            album_name = None
                        
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
            except Exception as e:
                logger.warning(f"External search failed: {e}")
                local_songs = await search_songs_local(db, q, limit, offset)
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
    
    if type in ["all", "artists"]:
        local_artists = await search_artists_local(db, q, limit, offset)
        
        if not local_artists and use_external:
            try:
                async with JamendoClient() as client:
                    jamendo_artists = await client.search_artists(q, limit)
                    data_service = MusicDataService(db)
                    for ja in jamendo_artists:
                        artist = await data_service.cache_jamendo_artist(ja)
                        response.artists.append(ArtistResponse(
                            id=artist.id,
                            external_id=artist.external_id,
                            source=artist.source,
                            name=artist.name,
                            image_url=artist.image_url,
                        ))
            except Exception as e:
                logger.warning(f"External artist search failed: {e}")
        
        for artist in local_artists:
            response.artists.append(ArtistResponse(
                id=artist.id,
                external_id=artist.external_id,
                source=artist.source,
                name=artist.name,
                image_url=artist.image_url,
            ))
    
    if type in ["all", "albums"]:
        local_albums = await search_albums_local(db, q, limit, offset)
        
        if not local_albums and use_external:
            try:
                async with JamendoClient() as client:
                    jamendo_albums = await client.search_albums(q, limit)
                    data_service = MusicDataService(db)
                    for ja in jamendo_albums:
                        album = await data_service.cache_jamendo_album(ja)
                        response.albums.append(AlbumResponse(
                            id=album.id,
                            external_id=album.external_id,
                            source=album.source,
                            name=album.name,
                            artist_name=album.artist.name if album.artist else None,
                            cover_url=album.cover_url,
                            release_date=album.release_date,
                        ))
            except Exception as e:
                logger.warning(f"External album search failed: {e}")
        
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
