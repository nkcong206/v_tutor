from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db
import os

# Create uploads directory if it doesn't exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.vector_store_dir, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.on_event("startup")
async def startup_event():
    """Initialize database and cache on startup"""
    init_db()
    
    # Initialize Semantic Cache (Custom)
    from app.services.semantic_cache import init_semantic_cache
    init_semantic_cache()
    
    print(f"🚀 {settings.app_name} is starting...")
    print(f"📚 Database: {settings.database_url}")
    print(f"🤖 AI Model: OpenAI")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.api_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Import and include routers
from app.routes import exam, tutor

app.include_router(exam.router, prefix="/api/exam", tags=["Exam"])
app.include_router(tutor.router, prefix="/api/tutor", tags=["Tutor"])
