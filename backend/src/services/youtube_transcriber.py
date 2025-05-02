import os
import logging
import tempfile
import yt_dlp
import whisper
from typing import Dict, Any
from backend.src.config import configure_logging

logger = configure_logging()


class YouTubeTranscriber:
    def __init__(self, model_size: str = "base",
                 ffmpeg_path: str = r"C:\Users\Admin\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin"):
        self.model = whisper.load_model(model_size)
        self.ffmpeg_path = ffmpeg_path

        # Ensure ffmpeg is in PATH or set explicitly for yt-dlp
        if self.ffmpeg_path:
            os.environ["PATH"] = f"{self.ffmpeg_path};{os.environ.get('PATH', '')}"

        # Verify ffmpeg executable exists
        ffmpeg_exe = os.path.join(self.ffmpeg_path, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            logger.warning(f"ffmpeg executable not found at {ffmpeg_exe}")

    def _download_audio(self, youtube_url: str) -> Dict[str, str]:
        try:
            temp_dir = tempfile.mkdtemp()
            audio_path_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

            ydl_opts = {
                'format': 'bestaudio/best',
                'ffmpeg_location': self.ffmpeg_path,
                'outtmpl': audio_path_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                video_id = info['id']
                video_title = info.get('title', 'Unknown Title')
                video_author = info.get('uploader', 'Unknown Author')
                downloaded_path = os.path.join(temp_dir, f"{video_id}.mp3")

            # Verify file exists after download
            if not os.path.exists(downloaded_path):
                raise FileNotFoundError(f"Downloaded audio file not found at {downloaded_path}")

            logger.info(f"Audio downloaded to: {downloaded_path}")
            return {
                "path": downloaded_path,
                "video_id": video_id,
                "video_title": video_title,
                "video_author": video_author
            }

        except Exception as e:
            logger.error(f"Error downloading YouTube audio: {str(e)}")
            raise

    def process_youtube_video(self, youtube_url: str, language: str = "en") -> Dict[str, Any]:
        try:
            # Download the audio and get video metadata
            result = self._download_audio(youtube_url)
            audio_path = result["path"]
            video_id = result["video_id"]
            video_title = result["video_title"]
            video_author = result["video_author"]

            # Double check file exists and has content
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found at {audio_path}")

            if os.path.getsize(audio_path) == 0:
                raise ValueError(f"Downloaded audio file is empty: {audio_path}")

            logger.info(f"Transcribing audio from {audio_path}")

            # Use absolute path for transcription
            abs_audio_path = os.path.abspath(audio_path)
            transcription_result = self.model.transcribe(abs_audio_path, language=language)

            logger.info(f"Successfully transcribed YouTube video {video_id}")

            # Clean up temp file after successful transcription
            try:
                os.remove(abs_audio_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")

            return {
                "success": True,
                "video_id": video_id,
                "video_title": video_title,
                "video_author": video_author,
                "youtube_url": youtube_url,
                "transcription": transcription_result["text"]
            }

        except Exception as e:
            logger.error(f"Error in process_youtube_video: {str(e)}")
            return {"success": False, "error": str(e)}