import logging
import random
from typing import Any, Optional
from datetime import datetime

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AudioDBTrack(BaseModel):
    id: str
    name: str
    artist_id: str
    artist_name: str
    album_id: Optional[str] = None
    album_name: Optional[str] = None
    duration: float = 0.0
    image: Optional[str] = None
    preview_url: Optional[str] = None
    genre: Optional[str] = None


class AudioDBArtist(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    bio: Optional[str] = None
    genre: Optional[str] = None


class AudioDBAlbum(BaseModel):
    id: str
    name: str
    artist_id: str
    artist_name: str
    image: Optional[str] = None
    release_date: Optional[str] = None
    genre: Optional[str] = None


class AudioDBClient:
    BASE_URL = "https://www.theaudiodb.com/api/v1/json"
    FREE_API_KEY = "123"
    
    SAMPLE_PREVIEW_URLS = [
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self.FREE_API_KEY
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("AudioDBClient must be used as an async context manager")
        return self._client
    
    async def _request(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.BASE_URL}/{self.api_key}/{endpoint}"
        
        if params is None:
            params = {}
        
        client = self._get_client()
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"AudioDB API HTTP error: {e.response.status_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"AudioDB API request failed: {e}")
            raise
    
    def _get_sample_audio_url(self, track_id: str) -> str:
        index = abs(hash(track_id)) % len(self.SAMPLE_PREVIEW_URLS)
        return self.SAMPLE_PREVIEW_URLS[index]
    
    async def search_tracks(self, query: str, limit: int = 20) -> list[AudioDBTrack]:
        tracks = []
        
        try:
            data = await self._request("searchtrack.php", {"s": query})
            
            if data.get("track"):
                for item in data["track"][:limit]:
                    try:
                        track_id = item.get("idTrack", "")
                        preview_url = item.get("strMusicVid") or self._get_sample_audio_url(track_id)
                        
                        if not preview_url or "youtube" in preview_url.lower() or "youtu.be" in preview_url.lower():
                            preview_url = self._get_sample_audio_url(track_id)
                        
                        duration = 0.0
                        duration_str = item.get("intDuration")
                        if duration_str:
                            try:
                                duration = float(duration_str) / 1000.0
                            except (ValueError, TypeError):
                                duration = random.uniform(180, 300)
                        
                        track = AudioDBTrack(
                            id=str(track_id),
                            name=item.get("strTrack", ""),
                            artist_id=str(item.get("idArtist", "")),
                            artist_name=item.get("strArtist", ""),
                            album_id=str(item.get("idAlbum")) if item.get("idAlbum") else None,
                            album_name=item.get("strAlbum"),
                            duration=duration,
                            image=item.get("strTrackThumb") or item.get("strAlbumThumb"),
                            preview_url=preview_url,
                            genre=item.get("strGenre"),
                        )
                        tracks.append(track)
                    except Exception as e:
                        logger.warning(f"Failed to parse AudioDB track: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"AudioDB track search failed: {e}")
        
        return tracks
    
    async def search_artists(self, query: str, limit: int = 20) -> list[AudioDBArtist]:
        artists = []
        
        try:
            data = await self._request("search.php", {"s": query})
            
            if data.get("artists"):
                for item in data["artists"][:limit]:
                    try:
                        artist = AudioDBArtist(
                            id=str(item.get("idArtist", "")),
                            name=item.get("strArtist", ""),
                            image=item.get("strArtistThumb") or item.get("strArtistLogo"),
                            bio=item.get("strBiographyEN"),
                            genre=item.get("strGenre"),
                        )
                        artists.append(artist)
                    except Exception as e:
                        logger.warning(f"Failed to parse AudioDB artist: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"AudioDB artist search failed: {e}")
        
        return artists
    
    async def search_albums(self, query: str, limit: int = 20) -> list[AudioDBAlbum]:
        albums = []
        
        try:
            data = await self._request("searchalbum.php", {"s": query})
            
            if data.get("album"):
                for item in data["album"][:limit]:
                    try:
                        album = AudioDBAlbum(
                            id=str(item.get("idAlbum", "")),
                            name=item.get("strAlbum", ""),
                            artist_id=str(item.get("idArtist", "")),
                            artist_name=item.get("strArtist", ""),
                            image=item.get("strAlbumThumb"),
                            release_date=item.get("intYearReleased"),
                            genre=item.get("strGenre"),
                        )
                        albums.append(album)
                    except Exception as e:
                        logger.warning(f"Failed to parse AudioDB album: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"AudioDB album search failed: {e}")
        
        return albums
    
    async def get_track(self, track_id: str) -> Optional[AudioDBTrack]:
        try:
            data = await self._request("track.php", {"h": track_id})
            
            if data.get("track") and len(data["track"]) > 0:
                item = data["track"][0]
                preview_url = item.get("strMusicVid") or self._get_sample_audio_url(track_id)
                
                if not preview_url or "youtube" in preview_url.lower():
                    preview_url = self._get_sample_audio_url(track_id)
                
                duration = 0.0
                duration_str = item.get("intDuration")
                if duration_str:
                    try:
                        duration = float(duration_str) / 1000.0
                    except (ValueError, TypeError):
                        duration = random.uniform(180, 300)
                
                return AudioDBTrack(
                    id=str(item.get("idTrack", "")),
                    name=item.get("strTrack", ""),
                    artist_id=str(item.get("idArtist", "")),
                    artist_name=item.get("strArtist", ""),
                    album_id=str(item.get("idAlbum")) if item.get("idAlbum") else None,
                    album_name=item.get("strAlbum"),
                    duration=duration,
                    image=item.get("strTrackThumb") or item.get("strAlbumThumb"),
                    preview_url=preview_url,
                    genre=item.get("strGenre"),
                )
        except Exception as e:
            logger.warning(f"AudioDB get track failed: {e}")
        
        return None
    
    async def get_artist(self, artist_id: str) -> Optional[AudioDBArtist]:
        try:
            data = await self._request("artist.php", {"i": artist_id})
            
            if data.get("artists") and len(data["artists"]) > 0:
                item = data["artists"][0]
                return AudioDBArtist(
                    id=str(item.get("idArtist", "")),
                    name=item.get("strArtist", ""),
                    image=item.get("strArtistThumb") or item.get("strArtistLogo"),
                    bio=item.get("strBiographyEN"),
                    genre=item.get("strGenre"),
                )
        except Exception as e:
            logger.warning(f"AudioDB get artist failed: {e}")
        
        return None
    
    async def get_album(self, album_id: str) -> Optional[AudioDBAlbum]:
        try:
            data = await self._request("album.php", {"m": album_id})
            
            if data.get("album") and len(data["album"]) > 0:
                item = data["album"][0]
                return AudioDBAlbum(
                    id=str(item.get("idAlbum", "")),
                    name=item.get("strAlbum", ""),
                    artist_id=str(item.get("idArtist", "")),
                    artist_name=item.get("strArtist", ""),
                    image=item.get("strAlbumThumb"),
                    release_date=item.get("intYearReleased"),
                    genre=item.get("strGenre"),
                )
        except Exception as e:
            logger.warning(f"AudioDB get album failed: {e}")
        
        return None
