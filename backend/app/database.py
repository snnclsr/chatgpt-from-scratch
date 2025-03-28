from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Get the directory where this file is located
BASEDIR = os.path.abspath(os.path.dirname(__file__))

# Create the SQLite URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASEDIR, 'chat.db')}"

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
