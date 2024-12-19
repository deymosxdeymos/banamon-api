from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.storage import FirestoreHandler
from app.utils.auth import AuthHandler
from app.utils.logger import logger
from typing import Dict

router = APIRouter()
storage = FirestoreHandler()
security = HTTPBearer()
auth_handler = AuthHandler()

@router.get("/predict")
async def get_predictions(
    limit: int = 10,
    auth: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Get user's prediction history."""
    try:
        # Get user ID from token
        user_id = auth_handler.verify_token(auth.credentials)

        # Get predictions
        logger.info(f"Fetching predictions for user: {user_id}")
        predictions = await storage.get_user_predictions(user_id, limit)

        return {
            "status": "success",
            "data": predictions
        }
    except Exception as e:
        logger.error(f"Failed to get predictions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to get predictions",
                "error": str(e)
            }
        )
