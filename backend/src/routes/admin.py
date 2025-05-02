import logging
import traceback
from fastapi import Request, status, Body, APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional

from backend.src.services.chroma_db import ChromaDBHandler
from backend.src.services.scraper import WebScraper
from backend.src.services.transcriber import PodcastTranscriber
from backend.src.services.youtube_transcriber import YouTubeTranscriber
from backend.src.config import configure_logging

# Configure logger
logger = configure_logging()

# Initialize FastAPI router
admin_router = APIRouter(prefix="/20VC-admin", tags=["20VC-admin"])


# Dependency injectors
def get_chroma_handler():
    return ChromaDBHandler()


def get_web_scraper():
    return WebScraper()


def get_transcriber():
    return PodcastTranscriber()


def get_youtube_transcriber():
    return YouTubeTranscriber()


# Custom exceptions
class ContentExtractionError(Exception):
    pass


class PodcastProcessingError(Exception):
    pass


# Request models
class BlogExtractRequest(BaseModel):
    url: HttpUrl


class PodcastProcessRequest(BaseModel):
    rss_feed_url: HttpUrl


class YouTubeRequest(BaseModel):
    youtube_url: HttpUrl
    language: Optional[str] = "en"


# Routes
@admin_router.get("/")
def get_admin_dashboard() -> Dict[str, str]:
    return {"message": "Admin Dashboard"}


@admin_router.get("/dashboard")
def get_admin_dashboard_legacy() -> Dict[str, str]:
    return {"message": "Admin Dashboard"}


@admin_router.get("/content")
async def admin_list_content(
        chroma_handler: ChromaDBHandler = Depends(get_chroma_handler)
) -> Dict[str, Any]:
    try:
        content = chroma_handler.list_content(content_type="all")
        return {"content": content, "total_count": len(content)}
    except Exception as e:
        logger.error(f"Error retrieving admin content: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving content")


@admin_router.post("/extract-blog")
def extract_blog(
        request: BlogExtractRequest,
        chroma_handler: ChromaDBHandler = Depends(get_chroma_handler),
        web_scraper: WebScraper = Depends(get_web_scraper)
) -> Dict[str, str]:
    try:
        content_dict = web_scraper.extract_blog_content(str(request.url))
        if not content_dict:
            raise ContentExtractionError("Failed to extract blog content")

        text_content = None
        metadata = {}
        for strategy in ['article', 'semantic', 'soup']:
            if strategy in content_dict and 'content' in content_dict[strategy]:
                text_content = content_dict[strategy]['content']
                metadata = {k: v for k, v in content_dict[strategy].items() if k != 'content'}
                break

        if not text_content:
            raise ContentExtractionError("No content found in any extraction strategy")

        chroma_handler.store_text(text_content, "blog", str(request.url), metadata=metadata)

        logger.info(f"Successfully extracted blog from {request.url}")
        return {"message": "Blog extracted and stored in ChromaDB"}

    except ContentExtractionError as e:
        logger.warning(f"Content extraction failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error extracting blog: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@admin_router.post("/process-podcast")
def process_podcast_endpoint(
        request: PodcastProcessRequest,
        chroma_handler: ChromaDBHandler = Depends(get_chroma_handler),
        transcriber: PodcastTranscriber = Depends(get_transcriber),
        web_scraper: WebScraper = Depends(get_web_scraper)
) -> Dict[str, str]:
    try:
        feed_data = web_scraper.parse_rss_feed(str(request.rss_feed_url))

        if 'error' in feed_data:
            raise PodcastProcessingError(f"Error parsing RSS feed: {feed_data['error']}")

        if not feed_data.get('entries'):
            raise PodcastProcessingError("No entries found in RSS feed")

        episode = feed_data['entries'][0]
        podcast_name = feed_data.get('title', 'Unknown Podcast')
        episode_title = episode.get('title', 'Untitled Episode')

        audio_url = None
        for media in episode.get('media', []):
            if media.get('type', '').startswith('audio/'):
                audio_url = media.get('url')
                break
        if not audio_url and episode.get('media'):
            audio_url = episode['media'][0].get('url')
        if not audio_url:
            raise PodcastProcessingError("No audio URL found in RSS feed")

        audio_path = transcriber.download_audio(audio_url)
        if not audio_path:
            raise PodcastProcessingError(f"Failed to download audio from URL: {audio_url}")

        transcription = transcriber.transcribe_audio(audio_path)
        if not transcription:
            raise PodcastProcessingError("Failed to transcribe audio")

        chroma_handler.store_podcast_transcription(
            transcription,
            episode_title,
            podcast_name,
            str(request.rss_feed_url),
            audio_url
        )

        logger.info(f"Successfully processed podcast from {request.rss_feed_url}")
        return {"message": "Podcast processed and stored successfully"}

    except PodcastProcessingError as e:
        logger.warning(f"Podcast processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error processing podcast: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@admin_router.get("/list-podcasts")
async def list_podcasts(
        chroma_handler: ChromaDBHandler = Depends(get_chroma_handler)
) -> Dict[str, Any]:
    try:
        podcasts = chroma_handler.get_podcasts()
        logger.info(f"Retrieved {len(podcasts)} podcasts")
        return {"podcasts": podcasts or []}
    except Exception as e:
        logger.error(f"Error fetching podcasts: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving podcasts")


@admin_router.post("/process-youtube")
async def process_youtube(
        request: YouTubeRequest,
        chroma_handler: ChromaDBHandler = Depends(get_chroma_handler),
        youtube_transcriber: YouTubeTranscriber = Depends(get_youtube_transcriber)
) -> Dict[str, Any]:
    """
    Process a YouTube video URL, transcribe it, and store in ChromaDB.
    """
    try:
        # Process the YouTube video
        result = youtube_transcriber.process_youtube_video(str(request.youtube_url), request.language)

        if result["success"]:
            # Store in ChromaDB using the correct method
            try:
                chroma_handler.store_youtube_transcription(
                    transcription=result["transcription"],
                    video_title=result.get("video_title", "Unknown Title"),
                    video_author=result.get("video_author", "Unknown Author"),
                    youtube_url=str(request.youtube_url),
                    video_id=result["video_id"]
                )
                logger.info(f"Successfully stored YouTube transcription in ChromaDB")
            except Exception as e:
                logger.error(f"Error storing YouTube video in ChromaDB: {str(e)}")
                # Continue despite storage error - we still have the transcription

            return {
                "status": "success",
                "message": "YouTube video processed successfully",
                "video_id": result.get("video_id", ""),
                "video_title": result.get("video_title", "Unknown Title")
            }
        else:
            error_msg = result.get("error", "Unknown error occurred")
            logger.error(f"Error processing YouTube video: {error_msg}")
            return {
                "status": "error",
                "message": f"Failed to process YouTube video: {error_msg}",
                "video_url": str(request.youtube_url)
            }

    except Exception as e:
        logger.error(f"Exception in process_youtube endpoint: {str(e)}")
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "video_url": str(request.youtube_url)
        }