import json
import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JamendoTrack(BaseModel):
    id: str
    name: str
    artist_id: str
    artist_name: str
    album_id: Optional[str] = None
    album_name: Optional[str] = None
    audio: str
    duration: float
    image: Optional[str] = None
    image_small: Optional[str] = None
    musicinfo: Optional[dict[str, Any]] = None


class JamendoArtist(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    website: Optional[str] = None
    joindate: Optional[str] = None


class JamendoAlbum(BaseModel):
    id: str
    name: str
    artist_id: str
    artist_name: str
    image: Optional[str] = None
    releasedate: Optional[str] = None


class JamendoClient:
    BASE_URL = "https://api.jamendo.com/v3.0"

    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or settings.jamendo_client_id
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("JamendoClient must be used as an async context manager")
        return self._client

    async def _request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        method: str = "GET",
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        
        if params is None:
            params = {}
        
        if self.client_id:
            params["client_id"] = self.client_id
        params["format"] = "json"
        
        client = self._get_client()
        
        try:
            if method == "GET":
                response = await client.get(url, params=params)
            else:
                response = await client.post(url, params=params)
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("headers", {}).get("status") != "success":
                error_message = data.get("headers", {}).get("error_message", "Unknown error")
                raise Exception(f"Jamendo API error: {error_message}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Jamendo API HTTP error: {e.response.status_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Jamendo API request failed: {e}")
            raise

    async def search_tracks(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JamendoTrack]:
        params = {
            "namesearch": query,
            "limit": limit,
            "offset": offset,
            "audioformat": "mp32",
        }
        
        data = await self._request("/tracks", params=params)
        
        results = data.get("results", [])
        tracks = []
        
        for item in results:
            try:
                track = JamendoTrack(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    artist_id=str(item.get("artist_id", "")),
                    artist_name=item.get("artist_name", ""),
                    album_id=str(item.get("album_id")) if item.get("album_id") else None,
                    album_name=item.get("album_name"),
                    audio=item.get("audio", ""),
                    duration=float(item.get("duration", 0)),
                    image=item.get("image"),
                    image_small=item.get("image_small"),
                    musicinfo=item.get("musicinfo"),
                )
                tracks.append(track)
            except Exception as e:
                logger.warning(f"Failed to parse track: {e}")
                continue
        
        return tracks

    async def search_artists(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JamendoArtist]:
        params = {
            "namesearch": query,
            "limit": limit,
            "offset": offset,
        }
        
        data = await self._request("/artists", params=params)
        
        results = data.get("results", [])
        artists = []
        
        for item in results:
            try:
                artist = JamendoArtist(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    image=item.get("image"),
                    website=item.get("website"),
                    joindate=item.get("joindate"),
                )
                artists.append(artist)
            except Exception as e:
                logger.warning(f"Failed to parse artist: {e}")
                continue
        
        return artists

    async def search_albums(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JamendoAlbum]:
        params = {
            "namesearch": query,
            "limit": limit,
            "offset": offset,
        }
        
        data = await self._request("/albums", params=params)
        
        results = data.get("results", [])
        albums = []
        
        for item in results:
            try:
                album = JamendoAlbum(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    artist_id=str(item.get("artist_id", "")),
                    artist_name=item.get("artist_name", ""),
                    image=item.get("image"),
                    releasedate=item.get("releasedate"),
                )
                albums.append(album)
            except Exception as e:
                logger.warning(f"Failed to parse album: {e}")
                continue
        
        return albums

    async def get_track(self, track_id: str) -> Optional[JamendoTrack]:
        params = {"id": track_id}
        
        data = await self._request("/tracks", params=params)
        
        results = data.get("results", [])
        if not results:
            return None
        
        item = results[0]
        return JamendoTrack(
            id=str(item.get("id", "")),
            name=item.get("name", ""),
            artist_id=str(item.get("artist_id", "")),
            artist_name=item.get("artist_name", ""),
            album_id=str(item.get("album_id")) if item.get("album_id") else None,
            album_name=item.get("album_name"),
            audio=item.get("audio", ""),
            duration=float(item.get("duration", 0)),
            image=item.get("image"),
            image_small=item.get("image_small"),
            musicinfo=item.get("musicinfo"),
        )

    async def get_artist(self, artist_id: str) -> Optional[JamendoArtist]:
        params = {"id": artist_id}
        
        data = await self._request("/artists", params=params)
        
        results = data.get("results", [])
        if not results:
            return None
        
        item = results[0]
        return JamendoArtist(
            id=str(item.get("id", "")),
            name=item.get("name", ""),
            image=item.get("image"),
            website=item.get("website"),
            joindate=item.get("joindate"),
        )

    async def get_album(self, album_id: str) -> Optional[JamendoAlbum]:
        params = {"id": album_id}
        
        data = await self._request("/albums", params=params)
        
        results = data.get("results", [])
        if not results:
            return None
        
        item = results[0]
        return JamendoAlbum(
            id=str(item.get("id", "")),
            name=item.get("name", ""),
            artist_id=str(item.get("artist_id", "")),
            artist_name=item.get("artist_name", ""),
            image=item.get("image"),
            releasedate=item.get("releasedate"),
        )

    async def get_album_tracks(self, album_id: str) -> list[JamendoTrack]:
        params = {
            "album_id": album_id,
            "audioformat": "mp32",
        }
        
        data = await self._request("/tracks", params=params)
        
        results = data.get("results", [])
        tracks = []
        
        for item in results:
            try:
                track = JamendoTrack(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    artist_id=str(item.get("artist_id", "")),
                    artist_name=item.get("artist_name", ""),
                    album_id=str(item.get("album_id")) if item.get("album_id") else None,
                    album_name=item.get("album_name"),
                    audio=item.get("audio", ""),
                    duration=float(item.get("duration", 0)),
                    image=item.get("image"),
                    image_small=item.get("image_small"),
                    musicinfo=item.get("musicinfo"),
                )
                tracks.append(track)
            except Exception as e:
                logger.warning(f"Failed to parse track: {e}")
                continue
        
        return tracks

    async def get_artist_tracks(self, artist_id: str, limit: int = 50) -> list[JamendoTrack]:
        params = {
            "artist_id": artist_id,
            "limit": limit,
            "audioformat": "mp32",
        }
        
        data = await self._request("/tracks", params=params)
        
        results = data.get("results", [])
        tracks = []
        
        for item in results:
            try:
                track = JamendoTrack(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    artist_id=str(item.get("artist_id", "")),
                    artist_name=item.get("artist_name", ""),
                    album_id=str(item.get("album_id")) if item.get("album_id") else None,
                    album_name=item.get("album_name"),
                    audio=item.get("audio", ""),
                    duration=float(item.get("duration", 0)),
                    image=item.get("image"),
                    image_small=item.get("image_small"),
                    musicinfo=item.get("musicinfo"),
                )
                tracks.append(track)
            except Exception as e:
                logger.warning(f"Failed to parse track: {e}")
                continue
        
        return tracks
