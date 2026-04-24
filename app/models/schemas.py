from typing import Optional

from pydantic import BaseModel


class ArtistResponse(BaseModel):
    id: int
    external_id: str
    source: str
    name: str
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class AlbumResponse(BaseModel):
    id: int
    external_id: str
    source: str
    name: str
    artist_name: Optional[str] = None
    cover_url: Optional[str] = None
    release_date: Optional[str] = None

    class Config:
        from_attributes = True


class SongResponse(BaseModel):
    id: int
    external_id: str
    source: str
    name: str
    artist_name: Optional[str] = None
    album_name: Optional[str] = None
    duration: Optional[float] = None
    cover_url: Optional[str] = None
    genre_name: Optional[str] = None
    audio_url: Optional[str] = None

    class Config:
        from_attributes = True


class PlaylistResponse(BaseModel):
    id: int
    name: str
    cover_url: Optional[str] = None
    song_count: int = 0

    class Config:
        from_attributes = True


class PlaylistSongResponse(BaseModel):
    id: int
    name: str
    artist_name: Optional[str] = None
    duration: Optional[float] = None
    cover_url: Optional[str] = None
    order_index: int

    class Config:
        from_attributes = True


class SearchResultResponse(BaseModel):
    songs: list[SongResponse] = []
    artists: list[ArtistResponse] = []
    albums: list[AlbumResponse] = []
    total: int = 0


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    limit: int
    total_pages: int


class RecommendationResponse(BaseModel):
    song: SongResponse
    reason: str


class GraphRelationResponse(BaseModel):
    from_type: str
    from_id: int
    from_name: Optional[str] = None
    relation_type: str
    to_type: str
    to_id: int
    to_name: Optional[str] = None
