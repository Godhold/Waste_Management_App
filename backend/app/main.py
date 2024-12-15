from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine
import logging
from app.model import Base
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

# Import routes after database initialization to avoid circular imports
try:
    from app.routes import driver, management, tracking
    logger.info("Route modules imported successfully")
except ImportError as e:
    logger.error(f"Error importing route modules: {str(e)}")
    raise

app = FastAPI(
    title="Waste Management Tracking API",
    description="API for managing waste collection routes and drivers",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with tags for better API documentation
app.include_router(
    driver.router,
    prefix="/api/driver",
    tags=["Driver Operations"]
)

app.include_router(
    management.router,
    prefix="/api/management",
    tags=["Management Operations"]
)

app.include_router(
    tracking.router,
    prefix="/api/tracking",
    tags=["Tracking Operations"]
)

@app.get("/")
async def root():
    return {
        "message": "Waste Management Tracking API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Try to make a simple query to check database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": str(e),
            "version": "1.0.0"
        }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)