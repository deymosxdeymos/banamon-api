import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from app.utils.logger import logger
from google.cloud import storage, firestore
import os

class CloudStorageHandler:
    def __init__(self):
        # Initialize with explicit credentials for development
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        try:
            if credentials_path:
                self.storage_client = storage.Client.from_service_account_json(credentials_path)
            else:
                self.storage_client = storage.Client()
        except Exception as e:
            logger.error(f"Failed to initialize storage client: {e}")
            raise

        self._executor = ThreadPoolExecutor(max_workers=4)
        self.images_bucket_name = os.getenv('IMAGES_BUCKET', 'banamon-images')

    async def _run_in_executor(self, func):
        """Run blocking Storage operations in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func)

    async def upload_image(self, image_bytes: bytes, path: str, bucket_name: str) -> str:
        """Upload image and return public URL."""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(path)

            # Upload file
            await self._run_in_executor(
                lambda: blob.upload_from_string(
                    image_bytes,
                    content_type='image/jpeg'
                )
            )

            # Return the public URL for the uploaded file
            public_url = f"https://storage.googleapis.com/{bucket_name}/{path}"

            logger.info(f"File uploaded: {path}")
            return public_url

        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise

    async def save_user_image(self, image_bytes: bytes, user_id: str) -> str:
        """
        Save user's banana leaf image to Google Cloud Storage.

        Args:
            image_bytes (bytes): The image data to upload
            user_id (str): The ID of the user uploading the image

        Returns:
            str: The public URL of the uploaded image
        """
        try:
            # Generate a unique filename using user ID and timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"user_images/{user_id}/{timestamp}_banana_leaf.jpg"
            bucket_name = self.images_bucket_name

            # Upload file and get public URL
            public_url = await self.upload_image(
                image_bytes=image_bytes,
                path=filename,
                bucket_name=bucket_name
            )

            logger.info(f"User image saved: {filename}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to save user image: {str(e)}")
            raise

class FirestoreHandler:
    def __init__(self):
        self.db = firestore.Client()
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Collections
        self.users = self.db.collection('users')
        self.predictions = self.db.collection('predictions')
        self.tokens_blacklist = self.db.collection('tokens_blacklist')
        self.login_attempts = self.db.collection('login_attempts')

    async def _run_in_executor(self, func):
        """Run blocking Firestore operations in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func)

    async def create_user(self, email: str, password: bytes) -> str:
        """Create new user."""
        try:
            # Check if email exists using newer query syntax
            query = self.users.where("email", "==", email)
            existing = await self._run_in_executor(lambda: query.get())
            if len(list(existing)) > 0:
                raise ValueError("Email already registered")

            # Store user with password hash bytes directly
            user_ref = self.users.document()
            await self._run_in_executor(
                lambda: user_ref.set({
                    'email': email,
                    'password': password,  # Already hashed bytes from auth handler
                    'created_at': datetime.utcnow(),
                    'last_login': None
                })
            )
            return user_ref.id

        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            logger.exception("Create user exception:")
            raise

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        try:
            # Use simplified query
            query = self.users.where("email", "==", email)
            users = await self._run_in_executor(lambda: query.get())
            user_list = list(users)
            if not user_list:
                return None

            user = user_list[0]
            # Return raw password hash directly
            return {
                'id': user.id,
                'email': user.get('email'),
                'password': user.get('password'),  # Raw bytes from Firestore
                'created_at': user.get('created_at')
            }

        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            raise

    async def save_prediction(self, user_id: str, image_url: str, prediction: Dict) -> str:
        """Save prediction result."""
        try:
            doc_ref = self.predictions.document()
            await self._run_in_executor(
                lambda: doc_ref.set({
                    'user_id': user_id,
                    'image_url': image_url,
                    'prediction': prediction,
                    'created_at': datetime.utcnow()
                })
            )
            return doc_ref.id

        except Exception as e:
            logger.error(f"Failed to save prediction: {str(e)}")
            raise

    async def get_login_attempts(self, email: str, device_id: str) -> int:
        """Get number of failed login attempts."""
        try:
            key = f"{email}:{device_id}"
            doc = await self._run_in_executor(
                lambda: self.login_attempts.document(key).get()
            )
            return doc.get('attempts', 0) if doc.exists else 0

        except Exception as e:
            logger.error(f"Failed to get login attempts: {str(e)}")
            return 0

    async def record_login_attempt(self, email: str, device_id: str) -> None:
        """Record failed login attempt."""
        try:
            key = f"{email}:{device_id}"
            doc_ref = self.login_attempts.document(key)

            await self._run_in_executor(
                lambda: doc_ref.set({
                    'attempts': firestore.Increment(1),
                    'last_attempt': datetime.utcnow()
                }, merge=True)
            )

        except Exception as e:
            logger.error(f"Failed to record login attempt: {str(e)}")
            raise

    async def clear_login_attempts(self, email: str, device_id: str) -> None:
        """Clear login attempts after successful login."""
        try:
            key = f"{email}:{device_id}"
            await self._run_in_executor(
                lambda: self.login_attempts.document(key).delete()
            )

        except Exception as e:
            logger.error(f"Failed to clear login attempts: {str(e)}")
            raise
