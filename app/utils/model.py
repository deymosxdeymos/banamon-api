import tensorflow as tf
from PIL import Image, UnidentifiedImageError
import io
import os
import logging
import numpy as np
from typing import Dict, Optional
from threading import Lock
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO if os.getenv('ENV', 'development') == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelHandler:
    IMG_SIZE = (224, 224)
    VALID_FORMATS = {'JPEG', 'PNG'}
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_QUEUE_SIZE = 50  # Reduced to prevent overload

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize model handler with flexible configuration
        """
        try:
            self.config = config or {}
            self.env = os.getenv('ENV', 'development')
            self.model_path = self.config.get('model_path', os.getenv("MODEL_PATH", "/app/model/banana_disease_model_vgg_v3.keras"))
            self.model_version = self.config.get('model_version', os.getenv("MODEL_VERSION", "1.0.0"))

            # Initialize queue and lock
            self._request_queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            self._executor = ThreadPoolExecutor(max_workers=4)
            self._lock = Lock()

            # Load model
            self._load_model()
            asyncio.create_task(self._process_queue())
        except Exception as e:
            logger.exception(f"Initialization error: {str(e)}")
            self._healthy = False
            raise

    def _load_model(self):
        """Load and warm up the model."""
        try:
            tf.keras.backend.clear_session()
            self.model = tf.keras.models.load_model(self.model_path, compile=False)
            self.classes = [
                'Banana Black Sigatoka Disease',
                'Banana Bract Mosaic Virus Disease',
                'Banana Healthy Leaf',
                'Banana Insect Pest Disease',
                'Banana Moko Disease',
                'Banana Panama Disease',
                'Banana Yellow Sigatoka Disease'
            ]
            self._validate_model()
            self._warm_up_model()
            self._healthy = True
            logger.info(f"Model v{self.model_version} loaded successfully in {self.env} environment")
        except Exception as e:
            logger.exception(f"Model loading error: {str(e)}")
            self._healthy = False
            raise

    def _warm_up_model(self):
        """Warm up model to improve first prediction performance."""
        try:
            dummy_input = np.zeros((1, *self.IMG_SIZE, 3), dtype=np.float32)
            self.model.predict(dummy_input, verbose=0)
            logger.info("Model warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warm-up failed: {str(e)}")

    async def predict(self, image_bytes: bytes) -> Dict:
        """Queue prediction request."""
        if not self._healthy:
            raise HTTPException(status_code=503, detail="Model is not available")
        if self._request_queue.full():
            raise HTTPException(status_code=429, detail="Prediction queue is full")
        future = asyncio.Future()
        await self._request_queue.put((image_bytes, future))
        return await future

    async def _process_queue(self):
        """Process prediction queue."""
        while True:
            try:
                image_data, future = await self._request_queue.get()
                try:
                    result = await self._predict(image_data)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    self._request_queue.task_done()
            except Exception as e:
                logger.error(f"Queue processing error: {str(e)}")
                await asyncio.sleep(1)

    async def _predict(self, image_bytes: bytes) -> Dict:
        """Perform prediction."""
        try:
            image_array = self.preprocess_image(image_bytes)
            with self._lock:
                predictions = self.model.predict(image_array, verbose=0)
            probs = predictions[0]
            class_idx = np.argmax(probs)
            predicted_class = self.classes[class_idx]
            return {
                "prediction": predicted_class,
                "confidence": float(probs[class_idx] * 100),
                "is_healthy": predicted_class == "Banana Healthy Leaf",
                "model_version": self.model_version,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            raise HTTPException(status_code=500, detail="Prediction error")

    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Preprocess and validate image."""
        try:
            if len(image_bytes) > self.MAX_IMAGE_SIZE:
                raise ValueError("Image size exceeds 10MB")

            try:
                image = Image.open(io.BytesIO(image_bytes))
                if image.format not in self.VALID_FORMATS:
                    raise ValueError("Unsupported image format")
            except UnidentifiedImageError:
                raise ValueError("Invalid or corrupted image file")

            image = image.convert("RGB")
            image = image.resize(self.IMG_SIZE)
            image_array = np.array(image) / 255.0
            return np.expand_dims(image_array, 0)
        except Exception as e:
            logger.error(f"Image preprocessing error: {str(e)}")
            raise ValueError("Invalid image")

    def _validate_model(self):
        """Validate model integrity."""
        if not self.model or not hasattr(self.model, 'predict'):
            raise ValueError("Invalid model format or model not loaded")

    def get_health_status(self) -> Dict:
        """Provide API health status."""
        queue_size = self._request_queue.qsize()
        return {
            "status": "healthy" if self._healthy else "unhealthy",
            "model_version": self.model_version,
            "environment": self.env,
            "queue_size": queue_size,
            "timestamp": datetime.utcnow().isoformat()
        }
