from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import get_settings
from .core.scheduler import lifespan
from .core.database import init_database
from .api.routes import dashboard, api, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app with lifespan for background tasks
app = FastAPI(
    title=settings.app_name,
    description="Kubernetes Resource Monitoring Dashboard",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
init_database()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(api.router, prefix="/api", tags=["API"])
app.include_router(health.router, prefix="/health", tags=["Health"])

@app.get("/")
async def root():
    """Root endpoint redirects to dashboard"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)