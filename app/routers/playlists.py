from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Playlist, PlaylistSong, Song
from app.models.schemas import PlaylistResponse, PlaylistSongResponse, SongResponse

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class PlaylistCreate(BaseModel):
    name: str


class PlaylistUpdate(BaseModel):
    name: Optional[str] = None


class SongAdd(BaseModel):
    song_id: int


class SongReorder(BaseModel):
    order: list[int]


@router.get("", response_model=list[PlaylistResponse])
async def get_playlists(
    db: AsyncSession = Depends(get_db),
) -> list[PlaylistResponse]:
    stmt = select(Playlist).order_by(Playlist.updated_at.desc())
    result = await db.execute(stmt)
    playlists = result.scalars().all()
    
    responses = []
    for playlist in playlists:
        count_stmt = select(func.count(PlaylistSong.song_id)).where(
            PlaylistSong.playlist_id == playlist.id
        )
        count_result = await db.execute(count_stmt)
        song_count = count_result.scalar() or 0
        
        responses.append(PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            cover_url=playlist.cover_url,
            song_count=song_count,
        ))
    
    return responses


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    stmt = select(Playlist).options(
        selectinload(Playlist.songs).selectinload(PlaylistSong.song)
    ).where(Playlist.id == playlist_id)
    
    result = await db.execute(stmt)
    playlist = result.scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        cover_url=playlist.cover_url,
        song_count=len(playlist.songs),
    )


@router.get("/{playlist_id}/songs", response_model=list[PlaylistSongResponse])
async def get_playlist_songs(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[PlaylistSongResponse]:
    stmt = select(PlaylistSong).options(
        selectinload(PlaylistSong.song).selectinload(Song.artist)
    ).where(PlaylistSong.playlist_id == playlist_id).order_by(PlaylistSong.order_index)
    
    result = await db.execute(stmt)
    playlist_songs = result.scalars().all()
    
    responses = []
    for ps in playlist_songs:
        if ps.song:
            responses.append(PlaylistSongResponse(
                id=ps.song.id,
                name=ps.song.name,
                artist_name=ps.song.artist.name if ps.song.artist else None,
                duration=ps.song.duration,
                cover_url=ps.song.cover_url,
                order_index=ps.order_index,
            ))
    
    return responses


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    data: PlaylistCreate,
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    playlist = Playlist(name=data.name)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        cover_url=playlist.cover_url,
        song_count=0,
    )


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    data: PlaylistUpdate,
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    result = await db.execute(stmt)
    playlist = result.scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if data.name is not None:
        playlist.name = data.name
    
    await db.commit()
    await db.refresh(playlist)
    
    count_stmt = select(func.count(PlaylistSong.song_id)).where(
        PlaylistSong.playlist_id == playlist.id
    )
    count_result = await db.execute(count_stmt)
    song_count = count_result.scalar() or 0
    
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        cover_url=playlist.cover_url,
        song_count=song_count,
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    result = await db.execute(stmt)
    playlist = result.scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    await db.delete(playlist)
    await db.commit()


@router.post("/{playlist_id}/songs", status_code=status.HTTP_201_CREATED)
async def add_song_to_playlist(
    playlist_id: int,
    data: SongAdd,
    db: AsyncSession = Depends(get_db),
):
    playlist_stmt = select(Playlist).where(Playlist.id == playlist_id)
    playlist_result = await db.execute(playlist_stmt)
    playlist = playlist_result.scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    song_stmt = select(Song).where(Song.id == data.song_id)
    song_result = await db.execute(song_stmt)
    song = song_result.scalar_one_or_none()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    existing_stmt = select(PlaylistSong).where(
        PlaylistSong.playlist_id == playlist_id,
        PlaylistSong.song_id == data.song_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        return {"message": "Song already in playlist", "added": False}
    
    max_index_stmt = select(func.max(PlaylistSong.order_index)).where(
        PlaylistSong.playlist_id == playlist_id
    )
    max_index_result = await db.execute(max_index_stmt)
    max_index = max_index_result.scalar() or -1
    
    playlist_song = PlaylistSong(
        playlist_id=playlist_id,
        song_id=data.song_id,
        order_index=max_index + 1,
    )
    
    db.add(playlist_song)
    playlist.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Song added to playlist", "added": True}


@router.delete("/{playlist_id}/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PlaylistSong).where(
        PlaylistSong.playlist_id == playlist_id,
        PlaylistSong.song_id == song_id,
    )
    result = await db.execute(stmt)
    playlist_song = result.scalar_one_or_none()
    
    if not playlist_song:
        raise HTTPException(status_code=404, detail="Song not found in playlist")
    
    await db.delete(playlist_song)
    
    playlist_stmt = select(Playlist).where(Playlist.id == playlist_id)
    playlist_result = await db.execute(playlist_stmt)
    playlist = playlist_result.scalar_one_or_none()
    if playlist:
        playlist.updated_at = datetime.utcnow()
    
    await db.commit()


@router.put("/{playlist_id}/reorder")
async def reorder_playlist_songs(
    playlist_id: int,
    data: SongReorder,
    db: AsyncSession = Depends(get_db),
):
    playlist_stmt = select(Playlist).options(
        selectinload(Playlist.songs)
    ).where(Playlist.id == playlist_id)
    
    result = await db.execute(playlist_stmt)
    playlist = result.scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    song_id_to_ps = {ps.song_id: ps for ps in playlist.songs}
    
    for index, song_id in enumerate(data.order):
        if song_id in song_id_to_ps:
            song_id_to_ps[song_id].order_index = index
    
    playlist.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Playlist reordered successfully"}
