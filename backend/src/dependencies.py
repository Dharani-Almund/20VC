from fastapi import Depends, HTTPException, Header, Request
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
from typing import Union
import jwt
import logging
from backend.src.services.chroma_db import ChromaDBHandler
from backend.src.services.scraper import WebScraper
from backend.src.services.transcriber import PodcastTranscriber
from backend.src.services.youtube_service import YouTubeService  # Make sure this exists

from backend.src.config import config, configure_logging
logger = configure_logging()

# Authentication exception classes
# class AuthenticationError(HTTPException):
#     """Custom exception for authentication-related errors."""
#     def __init__(self, detail: str):
#         super().__init__(status_code=401, detail=detail)

# class AuthorizationError(HTTPException):
#     """Custom exception for authorization-related errors."""
#     def __init__(self, detail: str):
#         super().__init__(status_code=403, detail=detail)

# def get_current_user(
#         request: Request,
#         credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
# ) -> Dict[str, Any]:
#     """
#     Extract and validate user from JWT token.
#     """
#     # Check for token in different locations
#     token = None

#     # Try getting token from Authorization header
#     if credentials:
#         token = credentials.credentials

#     # Fallback to manual header check
#     if not token:
#         auth_header = request.headers.get("Authorization")
#         if auth_header:
#             try:
#                 _, token = auth_header.split()
#             except ValueError:
#                 raise AuthenticationError("Invalid Authorization header format")

#     if not token:
#         raise AuthenticationError("No authentication token provided")

#     try:
#         payload = jwt.decode(
#             token,
#             config.SECRET_KEY,
#             algorithms=[config.JWT_ALGORITHM]
#         )

#         # Validate required claims
#         required_claims = ["sub", "role"]
#         if not all(claim in payload for claim in required_claims):
#             raise AuthenticationError("Token is missing required claims")

#         return {
#             "user_id": payload.get("sub"),
#             "role": payload.get("role"),
#             "email": payload.get("email")
#         }

#     except jwt.ExpiredSignatureError:
#         raise AuthenticationError("Token has expired")
#     except jwt.InvalidTokenError:
#         raise AuthenticationError("Invalid token")
#     except Exception as e:
#         logger.error(f"Unexpected authentication error: {str(e)}")
#         raise AuthenticationError("Authentication failed")

# class RoleChecker:
#     """
#     Dependency to check user roles with granular access control.
#     """
#     def __init__(self, allowed_roles: Union[List[str], str]):
#         """
#         Initialize RoleChecker with allowed roles.
#         """
#         if isinstance(allowed_roles, str):
#             self.allowed_roles = [allowed_roles]
#         else:
#             self.allowed_roles = allowed_roles

#     def __call__(self, user: Dict[str, Any] = Depends(get_current_user)):
#         """
#         Check if user's role is in the allowed roles.
#         """
#         if user.get("role") not in self.allowed_roles:
#             raise AuthorizationError(
#                 f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
#             )
#         return user

# Commonly used role checker instances
# admin_required = RoleChecker(["admin"])
# user_required = RoleChecker(["user", "admin"])

# Service dependency functions
def get_chroma_handler():
    return ChromaDBHandler()

def get_web_scraper():
    return WebScraper()

def get_transcriber():
    return PodcastTranscriber()

def get_youtube_service(transcriber=Depends(get_transcriber)):
    return YouTubeService(transcriber_service=transcriber)
