# app/db_init.py
from sqlalchemy_utils import database_exists, create_database
from app.database import engine, Base, SQLALCHEMY_DATABASE_URL
from app.model import Driver  # Import the models we actually have
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    try:
        # Create database if it doesn't exist
        if not database_exists(SQLALCHEMY_DATABASE_URL):
            create_database(SQLALCHEMY_DATABASE_URL)
            logger.info("Created database")

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Created all database tables successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def create_initial_data():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # Check if we already have drivers
        existing_drivers = db.query(Driver).count()
        if existing_drivers == 0:
            # Create some sample drivers
            sample_drivers = [
                Driver(name="John Doe", phone="+233123456789"),
                Driver(name="Jane Smith", phone="+233987654321")
            ]
            db.add_all(sample_drivers)
            db.commit()
            logger.info("Created initial sample drivers")
        else:
            logger.info("Skipping initial data creation - drivers already exist")
    except Exception as e:
        logger.error(f"Error creating initial data: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info("Creating initial data...")
    create_initial_data()
    logger.info("Database initialization complete")