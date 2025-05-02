import logging
from typing import Dict, Any, Optional

from backend.src.services.youtube_transcriber import YouTubeTranscriber
from backend.src.config import configure_logging
from backend.src.services.chroma_db import ChromaDBHandler

logger = configure_logging()

class YouTubeService:
    def __init__(self, transcriber_service: YouTubeTranscriber = None):
        self.transcriber_service = transcriber_service or YouTubeTranscriber()
        self.vector_store = ChromaDBHandler()

    def download_and_transcribe_video(self, youtube_url: str) -> Dict[str, Any]:
        try:
            return self.process_video(youtube_url)
        except Exception as e:
            logger.error(f"Error in download_and_transcribe_video: {str(e)}")
            return {"success": False, "error": str(e)}

    def process_video(self, youtube_url: str, language: str = 'en') -> Dict[str, Any]:
        try:
            if not youtube_url:
                logger.error("Empty YouTube URL provided")
                return {"success": False, "error": "Empty YouTube URL provided"}

            # Normalize URL
            if "youtu.be" in youtube_url:
                video_id = youtube_url.split("/")[-1].split("?")[0]
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            elif "youtube.com/shorts/" in youtube_url:
                video_id = youtube_url.split("/shorts/")[-1].split("?")[0]
                youtube_url = f"https://www.youtube.com/watch?v={video_id}"

            result = self.transcriber_service.process_youtube_video(youtube_url, language)

            if result["success"]:
                logger.info(f"Successfully processed YouTube video from {youtube_url}")
                self.vector_store.store_text(
                    video_id=result["video_id"],
                    text=result["transcription"],
                    metadata={"url": youtube_url}
                )
            else:
                logger.error(f"Failed to process YouTube video: {result['error']}")

            return result
        except Exception as e:
            logger.error(f"Error processing YouTube video: {str(e)}")
            return {"success": False, "error": f"Processing error: {str(e)}"}

    def get_video_info(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        try:
            import yt_dlp

            if not youtube_url:
                return None

            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return {
                    "title": info.get("title"),
                    "author": info.get("uploader"),
                    "description": info.get("description"),
                    "publish_date": info.get("upload_date"),
                    "length": info.get("duration"),
                    "views": info.get("view_count"),
                    "url": youtube_url,
                    "video_id": info.get("id"),
                    "thumbnail_url": info.get("thumbnail")
                }

        except Exception as e:
            logger.error(f"Error retrieving video info: {str(e)}")
            return None
