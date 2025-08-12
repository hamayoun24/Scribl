from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text, create_engine
from sqlalchemy.exc import OperationalError
from config import settings as env_settings
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


Base = declarative_base()

engine = create_engine(env_settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=15,
    pool_timeout=30
)

SessionLocal = sessionmaker(bind=engine,autoflush=False) 


def get_db():
    db = SessionLocal()
    try: 
        yield db
    finally:
        db.close()


def check_updates():
    """Run on Startup to patch missing schema fields."""
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            with engine.begin() as connection:
                result = connection.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='analysis_feedback' AND column_name='criteria_accurate'"
                ))
                if not result.fetchone():
                    connection.execute(text(
                        "ALTER TABLE analysis_feedback ADD COLUMN criteria_accurate BOOLEAN"
                    ))
                    logger.info("Added missing 'criteria_accurate' column to analysis_feedback table")
            break

        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay * (2 ** attempt))
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error updating database schema: {str(e)}")
        
        break