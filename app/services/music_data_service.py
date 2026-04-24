import json
import logging
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Artist, Album, Song, Genre, GraphEdge
from app.services.jamendo_client import JamendoTrack, JamendoArtist, JamendoAlbum
from app.services.audiodb_client import AudioDBTrack, AudioDBArtist, AudioDBAlbum
from app.services.sample_generator import SampleTrack, SampleArtist, SampleAlbum

logger = logging.getLogger(__name__)


class MusicDataService:
    SOURCE_JAMENDO = "jamendo"
    SOURCE_AUDIODB = "audiodb"
    SOURCE_SAMPLE = "sample"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_artist(
        self,
        external_id: str,
        source: str,
        name: str,
        bio: Optional[str] = None,
        image_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Artist:
        result = await self.db.execute(
            select(Artist).where(
                Artist.external_id == external_id,
                Artist.source == source,
            )
        )
        artist = result.scalar_one_or_none()

        if artist:
            return artist

        artist = Artist(
            external_id=external_id,
            source=source,
            name=name,
            bio=bio,
            image_url=image_url,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(artist)
        await self.db.commit()
        await self.db.refresh(artist)
        return artist

    async def get_or_create_album(
        self,
        external_id: str,
        source: str,
        name: str,
        artist_id: Optional[int] = None,
        release_date: Optional[str] = None,
        cover_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Album:
        result = await self.db.execute(
            select(Album).where(
                Album.external_id == external_id,
                Album.source == source,
            )
        )
        album = result.scalar_one_or_none()

        if album:
            return album

        album = Album(
            external_id=external_id,
            source=source,
            name=name,
            artist_id=artist_id,
            release_date=release_date,
            cover_url=cover_url,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(album)
        await self.db.commit()
        await self.db.refresh(album)
        return album

    async def get_or_create_genre(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Genre:
        name_lower = name.lower().strip() if name else ""
        if not name_lower:
            name_lower = "unknown"

        result = await self.db.execute(
            select(Genre).where(Genre.name == name_lower)
        )
        genre = result.scalar_one_or_none()

        if genre:
            return genre

        genre = Genre(name=name_lower, description=description)
        self.db.add(genre)
        await self.db.commit()
        await self.db.refresh(genre)
        return genre

    async def get_or_create_song(
        self,
        external_id: str,
        source: str,
        name: str,
        artist_id: Optional[int] = None,
        album_id: Optional[int] = None,
        duration: Optional[float] = None,
        audio_url: Optional[str] = None,
        cover_url: Optional[str] = None,
        genre_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Song:
        result = await self.db.execute(
            select(Song).where(
                Song.external_id == external_id,
                Song.source == source,
            )
        )
        song = result.scalar_one_or_none()

        if song:
            return song

        song = Song(
            external_id=external_id,
            source=source,
            name=name,
            artist_id=artist_id,
            album_id=album_id,
            duration=duration,
            audio_url=audio_url,
            cover_url=cover_url,
            genre_name=genre_name,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(song)
        await self.db.commit()
        await self.db.refresh(song)
        return song

    async def cache_jamendo_track(
        self,
        track: JamendoTrack,
    ) -> Song:
        artist = await self.get_or_create_artist(
            external_id=track.artist_id,
            source=self.SOURCE_JAMENDO,
            name=track.artist_name,
        )

        album: Optional[Album] = None
        if track.album_id:
            album = await self.get_or_create_album(
                external_id=track.album_id,
                source=self.SOURCE_JAMENDO,
                name=track.album_name or "Unknown Album",
                artist_id=artist.id,
                cover_url=track.image,
            )

        genre_name = None
        if track.musicinfo:
            tags = track.musicinfo.get("tags", {})
            if tags:
                genre_name = tags.get("genretags", "") or list(tags.values())[0] if tags else None

        song = await self.get_or_create_song(
            external_id=track.id,
            source=self.SOURCE_JAMENDO,
            name=track.name,
            artist_id=artist.id,
            album_id=album.id if album else None,
            duration=track.duration,
            audio_url=track.audio,
            cover_url=track.image or track.image_small,
            genre_name=genre_name,
            metadata={
                "track_id": track.id,
                "artist_id": track.artist_id,
                "album_id": track.album_id,
                "musicinfo": track.musicinfo,
            },
        )

        await self._create_graph_edges(song, artist, album, genre_name)

        return song

    async def cache_jamendo_tracks(
        self,
        tracks: list[JamendoTrack],
    ) -> list[Song]:
        cached_songs = []
        for track in tracks:
            try:
                song = await self.cache_jamendo_track(track)
                cached_songs.append(song)
            except Exception as e:
                logger.error(f"Failed to cache track {track.id}: {e}")
        return cached_songs

    async def cache_jamendo_artist(
        self,
        artist: JamendoArtist,
    ) -> Artist:
        return await self.get_or_create_artist(
            external_id=artist.id,
            source=self.SOURCE_JAMENDO,
            name=artist.name,
            image_url=artist.image,
            metadata={
                "website": artist.website,
                "joindate": artist.joindate,
            },
        )

    async def cache_jamendo_album(
        self,
        album: JamendoAlbum,
    ) -> Album:
        artist = await self.get_or_create_artist(
            external_id=album.artist_id,
            source=self.SOURCE_JAMENDO,
            name=album.artist_name,
        )

        return await self.get_or_create_album(
            external_id=album.id,
            source=self.SOURCE_JAMENDO,
            name=album.name,
            artist_id=artist.id,
            release_date=album.releasedate,
            cover_url=album.image,
        )

    async def _create_graph_edges(
        self,
        song: Song,
        artist: Artist,
        album: Optional[Album],
        genre_name: Optional[str],
    ) -> None:
        edges_to_create = []

        if artist.id:
            edges_to_create.append(GraphEdge(
                from_type="artist",
                from_id=artist.id,
                to_type="song",
                to_id=song.id,
                relation_type="artist_sings",
                weight=1.0,
            ))

        if album and album.id:
            edges_to_create.append(GraphEdge(
                from_type="album",
                from_id=album.id,
                to_type="song",
                to_id=song.id,
                relation_type="album_contains",
                weight=1.0,
            ))

        if genre_name:
            genre = await self.get_or_create_genre(genre_name)
            edges_to_create.append(GraphEdge(
                from_type="song",
                from_id=song.id,
                to_type="genre",
                to_id=genre.id,
                relation_type="song_has_genre",
                weight=1.0,
            ))

        for edge in edges_to_create:
            existing = await self.db.execute(
                select(GraphEdge).where(
                    GraphEdge.from_type == edge.from_type,
                    GraphEdge.from_id == edge.from_id,
                    GraphEdge.to_type == edge.to_type,
                    GraphEdge.to_id == edge.to_id,
                    GraphEdge.relation_type == edge.relation_type,
                )
            )
            if existing.scalar_one_or_none() is None:
                self.db.add(edge)

        await self.db.commit()

    async def cache_audiodb_track(self, track: AudioDBTrack) -> Song:
        artist = await self.get_or_create_artist(
            external_id=track.artist_id,
            source=self.SOURCE_AUDIODB,
            name=track.artist_name,
        )

        album: Optional[Album] = None
        if track.album_id:
            album = await self.get_or_create_album(
                external_id=track.album_id,
                source=self.SOURCE_AUDIODB,
                name=track.album_name or "Unknown Album",
                artist_id=artist.id,
                cover_url=track.image,
            )

        song = await self.get_or_create_song(
            external_id=track.id,
            source=self.SOURCE_AUDIODB,
            name=track.name,
            artist_id=artist.id,
            album_id=album.id if album else None,
            duration=track.duration or 180.0,
            audio_url=track.preview_url,
            cover_url=track.image,
            genre_name=track.genre,
            metadata={
                "track_id": track.id,
                "artist_id": track.artist_id,
                "album_id": track.album_id,
                "preview_url": track.preview_url,
            },
        )

        await self._create_graph_edges(song, artist, album, track.genre)

        return song

    async def cache_audiodb_tracks(self, tracks: list[AudioDBTrack]) -> list[Song]:
        cached_songs = []
        for track in tracks:
            try:
                song = await self.cache_audiodb_track(track)
                cached_songs.append(song)
            except Exception as e:
                logger.error(f"Failed to cache AudioDB track {track.id}: {e}")
        return cached_songs

    async def cache_audiodb_artist(self, artist: AudioDBArtist) -> Artist:
        return await self.get_or_create_artist(
            external_id=artist.id,
            source=self.SOURCE_AUDIODB,
            name=artist.name,
            bio=artist.bio,
            image_url=artist.image,
            metadata={
                "genre": artist.genre,
            },
        )

    async def cache_audiodb_album(self, album: AudioDBAlbum) -> Album:
        artist = await self.get_or_create_artist(
            external_id=album.artist_id,
            source=self.SOURCE_AUDIODB,
            name=album.artist_name,
        )

        return await self.get_or_create_album(
            external_id=album.id,
            source=self.SOURCE_AUDIODB,
            name=album.name,
            artist_id=artist.id,
            release_date=album.release_date,
            cover_url=album.image,
            metadata={
                "genre": album.genre,
            },
        )

    async def cache_sample_track(self, track: SampleTrack) -> Song:
        artist = await self.get_or_create_artist(
            external_id=track.artist_id,
            source=self.SOURCE_SAMPLE,
            name=track.artist_name,
        )

        album: Optional[Album] = None
        if track.album_id:
            album = await self.get_or_create_album(
                external_id=track.album_id,
                source=self.SOURCE_SAMPLE,
                name=track.album_name or "Unknown Album",
                artist_id=artist.id,
                cover_url=track.image,
            )

        song = await self.get_or_create_song(
            external_id=track.id,
            source=self.SOURCE_SAMPLE,
            name=track.name,
            artist_id=artist.id,
            album_id=album.id if album else None,
            duration=track.duration or 180.0,
            audio_url=track.audio_url,
            cover_url=track.image,
            genre_name=track.genre,
            metadata={
                "track_id": track.id,
                "artist_id": track.artist_id,
                "album_id": track.album_id,
            },
        )

        await self._create_graph_edges(song, artist, album, track.genre)

        return song

    async def cache_sample_tracks(self, tracks: list[SampleTrack]) -> list[Song]:
        cached_songs = []
        for track in tracks:
            try:
                song = await self.cache_sample_track(track)
                cached_songs.append(song)
            except Exception as e:
                logger.error(f"Failed to cache sample track {track.id}: {e}")
        return cached_songs

    async def cache_sample_artist(self, artist: SampleArtist) -> Artist:
        return await self.get_or_create_artist(
            external_id=artist.id,
            source=self.SOURCE_SAMPLE,
            name=artist.name,
            image_url=artist.image,
            metadata={
                "genre": artist.genre,
            },
        )

    async def cache_sample_album(self, album: SampleAlbum) -> Album:
        artist = await self.get_or_create_artist(
            external_id=album.artist_id,
            source=self.SOURCE_SAMPLE,
            name=album.artist_name,
        )

        return await self.get_or_create_album(
            external_id=album.id,
            source=self.SOURCE_SAMPLE,
            name=album.name,
            artist_id=artist.id,
            release_date=album.release_date,
            cover_url=album.image,
            metadata={
                "genre": album.genre,
            },
        )
