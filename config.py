import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application Settings
    PROJECT_NAME: str = "Event Photo Finder"
    DEBUG: bool = False
    
    # Database Settings (Points to data/event_photos.db)
    DATABASE_URL: str = "sqlite:///./data/event_photos.db"
    
    # ML Weights & Parameters
    YOLO_WEIGHTS_PATH: str = r"D:\facedetectionproject\face_detection_runs\yolo11s_widerface\weights\best.pt"
    
    # Precision threshold for ArcFace buffalo_l (w600k_r50)
    # 0.52 eliminates false positives across multi-person crowd albums
    FACE_SIMILARITY_THRESHOLD: float = 0.52
    
    # Google Drive Integration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "YOUR_GOOGLE_DRIVE_API_KEY")
    MAX_CONCURRENT_DOWNLOADS: int = 6

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()