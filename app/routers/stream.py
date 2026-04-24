import logging
import re
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Song

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["stream"])

CHUNK_SIZE = 1024 * 64
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0, read=30.0)


async def get_song_audio_url(song_id: int, db: AsyncSession) -> str:
    stmt = select(Song).where(Song.id == song_id)
    result = await db.execute(stmt)
    song = result.scalar_one_or_none()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if not song.audio_url:
        raise HTTPException(status_code=404, detail="No audio URL available for this song")
    
    return song.audio_url


def parse_range_header(range_header: str, file_size: Optional[int] = None) -> tuple[int, int]:
    if not range_header or not range_header.startswith("bytes="):
        return 0, None
    
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header[6:])
    if not range_match:
        return 0, None
    
    start = int(range_match.group(1))
    end_str = range_match.group(2)
    
    if end_str:
        end = int(end_str)
    else:
        end = file_size - 1 if file_size else None
    
    return start, end


@router.get("/stream/{song_id}")
async def stream_audio(
    song_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    audio_url = await get_song_audio_url(song_id, db)
    
    range_header = request.headers.get("range")
    logger.info(f"Streaming song {song_id} from {audio_url}, range: {range_header}")
    
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            if range_header:
                start, end = parse_range_header(range_header)
                
                range_request_header = f"bytes={start}-{end if end is not None else ''}"
                
                async with client.stream(
                    "GET",
                    audio_url,
                    headers={"Range": range_request_header},
                    follow_redirects=True,
                ) as response:
                    if response.status_code == 206:
                        content_range = response.headers.get("content-range", "")
                        content_length = response.headers.get("content-length")
                        
                        return StreamingResponse(
                            response.aiter_bytes(chunk_size=CHUNK_SIZE),
                            status_code=206,
                            headers={
                                "Content-Type": "audio/mpeg",
                                "Content-Range": content_range,
                                "Accept-Ranges": "bytes",
                                "Cache-Control": "public, max-age=86400",
                                "Access-Control-Allow-Origin": "*",
                            } if content_length else {
                                "Content-Type": "audio/mpeg",
                                "Content-Range": content_range,
                                "Accept-Ranges": "bytes",
                                "Cache-Control": "public, max-age=86400",
                                "Access-Control-Allow-Origin": "*",
                            },
                        )
                    elif response.status_code == 200:
                        return StreamingResponse(
                            response.aiter_bytes(chunk_size=CHUNK_SIZE),
                            status_code=200,
                            headers={
                                "Content-Type": "audio/mpeg",
                                "Accept-Ranges": "bytes",
                                "Cache-Control": "public, max-age=86400",
                                "Access-Control-Allow-Origin": "*",
                            },
                        )
                    else:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Failed to stream audio: {response.reason_phrase}",
                        )
            else:
                async with client.stream(
                    "GET",
                    audio_url,
                    follow_redirects=True,
                ) as response:
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Failed to stream audio: {response.reason_phrase}",
                        )
                    
                    return StreamingResponse(
                        response.aiter_bytes(chunk_size=CHUNK_SIZE),
                        status_code=200,
                        headers={
                            "Content-Type": "audio/mpeg",
                            "Accept-Ranges": "bytes",
                            "Cache-Control": "public, max-age=86400",
                            "Access-Control-Allow-Origin": "*",
                        },
                    )
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error streaming audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to stream audio from source",
        )
    except Exception as e:
        logger.error(f"Error streaming audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.head("/stream/{song_id}")
async def stream_audio_head(
    song_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    audio_url = await get_song_audio_url(song_id, db)
    
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.head(audio_url, follow_redirects=True)
            
            return Response(
                status_code=200,
                headers={
                    "Content-Type": "audio/mpeg",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                },
            )
    
    except Exception as e:
        logger.error(f"Error in HEAD request for stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
