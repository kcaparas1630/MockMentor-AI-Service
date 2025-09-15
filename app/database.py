"""Database Configuration and Connection Management Module

This module handles database connectivity, session management, and table operations
for the MockMentor application. It provides PostgreSQL connection with connection
pooling and comprehensive database utilities.

The module contains functions for database session management, table creation,
and connection configuration. It serves as the primary interface for database
operations in the application's data access layer.

Dependencies:
- sqlalchemy: For database ORM and connection management.
- dotenv: For environment variable loading.
- loguru: For logging operations.
- app.models.user_models: For database model definitions.

Author: @kcaparas1630
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from loguru import logger
from app.models.user_models import Base
load_dotenv()

# Load database connection details from environment variables
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DBNAME = os.getenv("DB_NAME")

# Validate required database configuration
required_vars = {
    "DB_USER": USER,
    "DB_PASSWORD": PASSWORD,
    "DB_HOST": HOST,
    "DB_PORT": PORT,
    "DB_NAME": DBNAME
}
missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Create a new SQLAlchemy engine instance
engine = create_engine(
    DATABASE_URL,
    echo=False, # Log SQL queries for debugging
    pool_pre_ping=True, # verify connections before using
    pool_recycle=300 # Recycle connections every 5 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """FastAPI dependency for database session management.
    
    Creates a new database session for each request and ensures proper
    cleanup after the request is completed. Use as a FastAPI dependency
    to inject database sessions into route handlers.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/users")
        async def get_users(db: Session = Depends(get_db_session)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables defined in the models.
    
    Uses SQLAlchemy's metadata to create all tables that don't already exist.
    This is typically called during application startup.
    
    Raises:
        Exception: If table creation fails
        
    Note:
        This operation is idempotent - existing tables won't be modified
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database table: {e}")
        raise

def drop_tables():
    """Drop all database tables defined in the models.
    
    WARNING: This will permanently delete all data in the tables.
    Use with extreme caution and only in development/testing environments.
    
    Raises:
        Exception: If table deletion fails
        
    Note:
        This operation will cascade and delete all related data
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise
