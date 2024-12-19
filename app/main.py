import os
from fastapi import FastAPI
from app.routers import predict, auth, history
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="BanaMon API",
    description="Banana Disease Detection API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(predict.router, tags=["Prediction"])
app.include_router(history.router, prefix="/history", tags=["History"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {
        "message": "BanaMon API is running",
        "version": "1.0.0",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
