import random
import hashlib
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class SampleTrack(BaseModel):
    id: str
    name: str
    artist_id: str
    artist_name: str
    album_id: Optional[str] = None
    album_name: Optional[str] = None
    audio_url: str
    duration: float
    image: Optional[str] = None
    genre: Optional[str] = None


class SampleArtist(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    genre: Optional[str] = None


class SampleAlbum(BaseModel):
    id: str
    name: str
    artist_id: str
    artist_name: str
    image: Optional[str] = None
    release_date: Optional[str] = None
    genre: Optional[str] = None


SAMPLE_SONGS = [
    {
        "name": "Acoustic Breeze",
        "artist": "Benjamin Tissot",
        "album": "Acoustic Collection",
        "genre": "Acoustic",
        "duration": 210,
    },
    {
        "name": "Summer",
        "artist": "Benjamin Tissot",
        "album": "Summer Vibes",
        "genre": "Pop",
        "duration": 180,
    },
    {
        "name": "Ukulele",
        "artist": "Benjamin Tissot",
        "album": "Happy Moments",
        "genre": "Happy",
        "duration": 240,
    },
    {
        "name": "Creative Minds",
        "artist": "Benjamin Tissot",
        "album": "Inspiration",
        "genre": "Ambient",
        "duration": 150,
    },
    {
        "name": "Going Higher",
        "artist": "Benjamin Tissot",
        "album": "Elevation",
        "genre": "Electronic",
        "duration": 200,
    },
    {
        "name": "Happy Rock",
        "artist": "Benjamin Tissot",
        "album": "Rock Collection",
        "genre": "Rock",
        "duration": 175,
    },
    {
        "name": "Jazzy Frenchy",
        "artist": "Benjamin Tissot",
        "album": "Jazz Nights",
        "genre": "Jazz",
        "duration": 220,
    },
    {
        "name": "Sunny Days",
        "artist": "Benjamin Tissot",
        "album": "Bright Future",
        "genre": "Upbeat",
        "duration": 195,
    },
    {
        "name": "Tenderness",
        "artist": "Benjamin Tissot",
        "album": "Soft Melodies",
        "genre": "Calm",
        "duration": 165,
    },
    {
        "name": "The Elevator Bossa Nova",
        "artist": "Benjamin Tissot",
        "album": "Bossa Collection",
        "genre": "Bossa Nova",
        "duration": 230,
    },
]

SAMPLE_ARTISTS = [
    {"name": "Benjamin Tissot", "genre": "Various"},
    {"name": "Free Music Archive", "genre": "Various"},
    {"name": "Jamendo Artists", "genre": "Various"},
    {"name": "Creative Commons", "genre": "Various"},
]

SAMPLE_ALBUMS = [
    {"name": "Acoustic Collection", "artist": "Benjamin Tissot", "genre": "Acoustic"},
    {"name": "Summer Vibes", "artist": "Benjamin Tissot", "genre": "Pop"},
    {"name": "Happy Moments", "artist": "Benjamin Tissot", "genre": "Happy"},
    {"name": "Inspiration", "artist": "Benjamin Tissot", "genre": "Ambient"},
    {"name": "Rock Collection", "artist": "Benjamin Tissot", "genre": "Rock"},
]

FREE_AUDIO_URLS = [
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
]


def generate_id(name: str, prefix: str = "sample") -> str:
    hash_obj = hashlib.md5(name.encode())
    return f"{prefix}_{hash_obj.hexdigest()[:12]}"


def get_audio_url_for_track(track_name: str) -> str:
    index = abs(hash(track_name)) % len(FREE_AUDIO_URLS)
    return FREE_AUDIO_URLS[index]


class SampleDataGenerator:
    SOURCE = "sample"
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
    
    def search_tracks(self, query: str, limit: int = 20) -> list[SampleTrack]:
        query_lower = query.lower()
        matched = []
        
        for song in SAMPLE_SONGS:
            if (
                query_lower in song["name"].lower()
                or query_lower in song["artist"].lower()
                or query_lower in song["genre"].lower()
            ):
                matched.append(song)
        
        if not matched:
            matched = SAMPLE_SONGS
        
        results = []
        for song in matched[:limit]:
            track = SampleTrack(
                id=generate_id(song["name"], "track"),
                name=song["name"],
                artist_id=generate_id(song["artist"], "artist"),
                artist_name=song["artist"],
                album_id=generate_id(song["album"], "album") if song.get("album") else None,
                album_name=song.get("album"),
                audio_url=get_audio_url_for_track(song["name"]),
                duration=float(song["duration"]),
                image=None,
                genre=song.get("genre"),
            )
            results.append(track)
        
        return results
    
    def search_artists(self, query: str, limit: int = 20) -> list[SampleArtist]:
        query_lower = query.lower()
        matched = []
        
        for artist in SAMPLE_ARTISTS:
            if query_lower in artist["name"].lower():
                matched.append(artist)
        
        if not matched:
            matched = SAMPLE_ARTISTS
        
        results = []
        for artist in matched[:limit]:
            sample_artist = SampleArtist(
                id=generate_id(artist["name"], "artist"),
                name=artist["name"],
                image=None,
                genre=artist.get("genre"),
            )
            results.append(sample_artist)
        
        return results
    
    def search_albums(self, query: str, limit: int = 20) -> list[SampleAlbum]:
        query_lower = query.lower()
        matched = []
        
        for album in SAMPLE_ALBUMS:
            if (
                query_lower in album["name"].lower()
                or query_lower in album["artist"].lower()
            ):
                matched.append(album)
        
        if not matched:
            matched = SAMPLE_ALBUMS
        
        results = []
        for album in matched[:limit]:
            sample_album = SampleAlbum(
                id=generate_id(album["name"], "album"),
                name=album["name"],
                artist_id=generate_id(album["artist"], "artist"),
                artist_name=album["artist"],
                image=None,
                release_date=None,
                genre=album.get("genre"),
            )
            results.append(sample_album)
        
        return results
    
    def get_random_tracks(self, count: int = 10) -> list[SampleTrack]:
        selected = random.sample(SAMPLE_SONGS, min(count, len(SAMPLE_SONGS)))
        return [
            SampleTrack(
                id=generate_id(song["name"], "track"),
                name=song["name"],
                artist_id=generate_id(song["artist"], "artist"),
                artist_name=song["artist"],
                album_id=generate_id(song["album"], "album") if song.get("album") else None,
                album_name=song.get("album"),
                audio_url=get_audio_url_for_track(song["name"]),
                duration=float(song["duration"]),
                image=None,
                genre=song.get("genre"),
            )
            for song in selected
        ]
    
    def get_all_tracks(self) -> list[SampleTrack]:
        return [
            SampleTrack(
                id=generate_id(song["name"], "track"),
                name=song["name"],
                artist_id=generate_id(song["artist"], "artist"),
                artist_name=song["artist"],
                album_id=generate_id(song["album"], "album") if song.get("album") else None,
                album_name=song.get("album"),
                audio_url=get_audio_url_for_track(song["name"]),
                duration=float(song["duration"]),
                image=None,
                genre=song.get("genre"),
            )
            for song in SAMPLE_SONGS
        ]
