import os
import json
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import settings

# Ensure the data/ folder exists for SQLite storage
os.makedirs("data", exist_ok=True)

# SQLite engine configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EventPhoto(Base):
    __tablename__ = "event_photos"

    id = Column(Integer, primary_key=True, index=True)
    drive_file_id = Column(String(100), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    view_link = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One-to-Many: A photo can contain multiple face embeddings
    faces = relationship("PhotoFaceEmbedding", back_populates="photo", cascade="all, delete-orphan")


class PhotoFaceEmbedding(Base):
    __tablename__ = "photo_face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("event_photos.id", ondelete="CASCADE"), nullable=False)
    embedding_data = Column(Text, nullable=False)  # Stored as serialized 512-D vector JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    photo = relationship("EventPhoto", back_populates="faces")

    def set_vector(self, vector: np.ndarray) -> None:
        """Converts a 1D NumPy array into a JSON string for SQLite storage."""
        self.embedding_data = json.dumps(vector.tolist())

    def get_vector(self) -> np.ndarray:
        """Deserializes JSON string back into a NumPy array."""
        return np.array(json.loads(self.embedding_data), dtype=np.float32)


def clear_all_indexed_photos():
    """Drops and re-creates all tables to completely purge vector data and reset sequences."""
    try:
        # Close any lingering connections attached to the engine before dropping
        engine.dispose()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Database purged and schema reset successfully.")
    except Exception as e:
        print(f"Error resetting database schema: {e}")


# Initialize DB tables on import
Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency yielding a clean DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()