from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from loguru import logger
from app.models.user_models import Base
load_dotenv()

# Load database connection details from environment variables
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DBNAME = os.getenv("DBNAME")

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database table: {e}")
        raise

def drop_tables():
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables drop successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise
