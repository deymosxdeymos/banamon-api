from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import Dict
from datetime import datetime
import os
from app.utils.model import ModelHandler
from app.utils.storage import CloudStorageHandler, FirestoreHandler
from app.utils.auth import AuthHandler
from app.utils.logger import logger
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Constants
IMAGES_BUCKET = os.getenv("IMAGES_BUCKET", "banamon-images")

router = APIRouter()
model_handler = ModelHandler()
storage_handler = CloudStorageHandler()
firestore_handler = FirestoreHandler()
auth_handler = AuthHandler()
security = HTTPBearer()

@router.post("/predict")
async def predict(
    file: UploadFile = File(...),
    auth: HTTPAuthorizationCredentials = Depends(security),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict:
    """
    Predict banana leaf disease for mobile app
    Requires authentication
    """
    try:
        # Validate file type and size
        if file.content_type not in ['image/jpeg', 'image/png']:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG and PNG are supported."
            )

        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(
                status_code=400,
                detail="File extension does not match allowed types (JPEG, PNG)."
            )

        file.file.seek(0, 2)  # Move to end of file to calculate size
        file_size = file.file.tell()
        file.file.seek(0)  # Reset file pointer

        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 10MB."
            )

        # Authenticate user
        current_user = auth_handler.verify_token(auth.credentials)

        # Read file
        contents = await file.read()

        # Log details
        logger.info(f"Prediction request received from user {current_user}")
        logger.info(f"File name: {file.filename}")

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"mobile_predictions/{current_user}/{timestamp}_{file.filename}"

        # Upload to cloud storage
        image_url = await storage_handler.upload_image(
            image_bytes=contents,
            path=filename,
            bucket_name=IMAGES_BUCKET
        )

        # Predict
        result = await model_handler.predict(contents)
        if "prediction" not in result or "confidence" not in result:
            raise HTTPException(
                status_code=500,
                detail="Model prediction response is malformed."
            )

        # Save prediction in Firestore
        background_tasks.add_task(
            firestore_handler.save_prediction,
            user_id=current_user,
            prediction=result["prediction"],
            image_url=image_url
        )

        # Response
        return {
            "status": "success",
            "data": {
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "is_healthy": result["is_healthy"],
                "description": result.get("description", "No additional details"),
                "recommendations": result.get("recommendations", []),
                "image_url": image_url,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        logger.error(f"Prediction failed for user {current_user}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Prediction processing failed",
                "error": str(e)
            }
        )
