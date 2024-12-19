from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
from typing import Dict
from dotenv import load_dotenv
from ..utils.storage import FirestoreHandler
from ..utils.logger import logger
from google.cloud import secretmanager

load_dotenv()

class AuthHandler:
    security = HTTPBearer()
    db = FirestoreHandler()
    secret = os.getenv("JWT_SECRET")

    # Constants
    ACCESS_TOKEN_EXPIRE = 24 * 60  # 24 hours
    REFRESH_TOKEN_EXPIRE = 30 * 24 * 60  # 30 days
    JWT_ALGORITHM = "HS256"

    def __init__(self):
        self.secret = self._get_jwt_secret()

    def _get_jwt_secret(self) -> str:
        """Get JWT secret from Secret Manager or environment variable"""
        # First, try environment variable
        env_secret = os.getenv("JWT_SECRET")
        if env_secret:
            return env_secret

        try:
            # Then try Secret Manager
            client = secretmanager.SecretManagerServiceClient()

            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")

            name = f"projects/{project_id}/secrets/jwt-secret/versions/latest"

            response = client.access_secret_version(request={"name": name})

            logger.info("Successfully retrieved JWT secret from Secret Manager")
            return response.payload.data.decode("UTF-8")

        except Exception as e:
            logger.error(f"Failed to access Secret Manager: {str(e)}")
            # If all else fails, you might want to raise an exception or provide a default
            raise ValueError("Could not access JWT secret")

    def create_access_token(self, user_id: str) -> str:
        """Create short-lived access token"""
        try:
            payload = {
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE),
                "iat": datetime.utcnow(),
                "type": "access"
            }
            return jwt.encode(payload, str(self.secret), algorithm=self.JWT_ALGORITHM)
        except Exception:
            raise HTTPException(status_code=500, detail="Could not create token")

    def create_refresh_token(self, user_id: str) -> str:
        """Create long-lived refresh token"""
        try:
            payload = {
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(minutes=self.REFRESH_TOKEN_EXPIRE),
                "iat": datetime.utcnow(),
                "type": "refresh"
            }
            return jwt.encode(payload, str(self.secret), algorithm=self.JWT_ALGORITHM)
        except Exception:
            raise HTTPException(status_code=500, detail="Could not create refresh token")

    def verify_token(self, token: str) -> str:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, str(self.secret), algorithms=[self.JWT_ALGORITHM])
            return payload["user_id"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def register(self, email: str, password: str) -> Dict:
        """Register a new user"""
        try:
            # Hash password
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password_bytes, salt)

            logger.debug(f"Registration - Password hash created: {type(hashed)}")

            # Create user (pass hashed password as bytes)
            user_id = await self.db.create_user(email=email, password=hashed)

            logger.info(f"User registered successfully: {email}")
            return {
                "user_id": user_id,
                "email": email,
                "message": "User registered successfully"
            }

        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Registration failed")

    async def authenticate(self, email: str, password: str) -> Dict:
        """Authenticate user and return tokens"""
        try:
            logger.info(f"Authenticating user with email: {email}")
            user = await self.db.get_user_by_email(email)

            if not user:
                logger.error(f"User not found for email: {email}")
                raise HTTPException(status_code=401, detail="Invalid credentials")

            logger.debug(f"User found: {user}")
            stored_password = user["password"]
            logger.debug(f"Stored password type: {type(stored_password)}")
            logger.debug(f"Input password: {password}")

            try:
                # Convert input password to bytes
                password_bytes = password.encode('utf-8')

                # Verify password
                password_matches = bcrypt.checkpw(password_bytes, stored_password)
                logger.debug(f"Password verification result: {password_matches}")

                if not password_matches:
                    logger.error("Password verification failed")
                    raise HTTPException(status_code=401, detail="Invalid credentials")

            except Exception as e:
                logger.error(f"Error during password verification: {str(e)}")
                logger.exception("Password verification exception:")
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Generate tokens
            access_token = self.create_access_token(user["id"])
            refresh_token = self.create_refresh_token(user["id"])

            logger.info(f"Authentication successful for user: {email}")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user_id": user["id"],
                "email": user["email"],
                "expires_in": self.ACCESS_TOKEN_EXPIRE * 60
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication failed")

    async def refresh(self, refresh_token: str) -> Dict:
        """Get new access token using refresh token"""
        try:
            # Verify refresh token
            payload = jwt.decode(refresh_token, str(self.secret), algorithms=[self.JWT_ALGORITHM])

            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")

            # Generate new access token
            access_token = self.create_access_token(payload["user_id"])

            return {
                "access_token": access_token,
                "expires_in": self.ACCESS_TOKEN_EXPIRE * 60
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

    async def get_current_user(
            self,
            credentials: HTTPAuthorizationCredentials
        ) -> str:
        """Get current user from token"""
        return self.verify_token(credentials.credentials)

    @staticmethod
    def hash_password(password: str) -> bytes:
        """Hash password"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt)
