# import jwt
# import os
# import datetime
# import logging
# from dotenv import load_dotenv
#
# # Load environment variables
# load_dotenv()
#
# # Get JWT secret from environment variables or use a default for development
# JWT_SECRET = os.getenv("JWT_SECRET", "development_secret_key_change_this_in_production")
# JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# TOKEN_EXPIRY = int(os.getenv("TOKEN_EXPIRY", "3600"))  # 1 hour default
#
# # Configure logging
# from backend.src.config import config, configure_logging
# logger = configure_logging()
#
# def generate_admin_token(username):
#     """Generate a JWT token for admin users"""
#     try:
#         payload = {
#             "sub": username,
#             "role": "admin",
#             "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=TOKEN_EXPIRY)
#         }
#         token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
#         logger.info(f"Generated admin token for {username}")
#         return token
#     except Exception as e:
#         logger.error(f"Error generating admin token: {str(e)}")
#         return None
#
# def generate_user_token(username):
#     """Generate a JWT token for regular users"""
#     try:
#         payload = {
#             "sub": username,
#             "role": "user",
#             "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=TOKEN_EXPIRY)
#         }
#         token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
#         logger.info(f"Generated user token for {username}")
#         return token
#     except Exception as e:
#         logger.error(f"Error generating user token: {str(e)}")
#         return None
#
# def validate_token(token):
#     """Validate a JWT token and return the payload"""
#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#         logger.info("Token validated successfully")
#         return payload
#     except jwt.ExpiredSignatureError:
#         logger.warning("Token has expired")
#         return None  # Token has expired
#     except jwt.InvalidTokenError:
#         logger.warning("Invalid token")
#         return None  # Invalid token
#     except Exception as e:
#         logger.error(f"Error validating token: {str(e)}")
#         return None
#
# def is_token_valid(token):
#     """Check if a token is valid"""
#     return validate_token(token) is not None
#
# def is_admin(token):
#     """Check if a token belongs to an admin user"""
#     payload = validate_token(token)
#     if payload:
#         return payload.get("role") == "admin"
#     return False
#
# # Generate test tokens for development - only runs when directly executed
# if __name__ == "__main__":
#     admin_token = generate_admin_token("admin")
#     user_token = generate_user_token("user")
#
#     print(f"Admin token: {admin_token}")
#     print(f"User token: {user_token}")
