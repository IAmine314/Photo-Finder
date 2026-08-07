import io
import base64
import numpy as np
import cv2
from PIL import Image
from typing import List, Optional
import torch
import insightface
from insightface.app import FaceAnalysis

from config import settings

device = 0 if torch.cuda.is_available() else 'cpu'

# ==========================================
# Global Model Initialization
# ==========================================
print("Loading InsightFace high-accuracy recognition model (buffalo_l)...")
recognizer = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
recognizer.prepare(ctx_id=0, det_thresh=0.50, det_size=(640, 640))


# ==========================================
# Image Decoding Utilities
# ==========================================
def decode_bytes_to_cv2(image_bytes: bytes) -> Optional[np.ndarray]:
    """Decodes raw HTTP response bytes into an OpenCV BGR frame."""
    if not image_bytes:
        return None
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            return img
            
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"Error decoding image bytes: {e}")
        return None


def decode_base64_to_cv2(base64_str: str) -> Optional[np.ndarray]:
    """
    Decodes HTML5 canvas base64 data URLs into a clean 3-channel OpenCV BGR frame.
    Strips alpha channel to avoid zero-vector generation in InsightFace.
    """
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        image_bytes = base64.b64decode(base64_str)
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB") # Drops Alpha Channel
        frame_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return frame_bgr
    except Exception as e:
        print(f"Error decoding base64 image: {e}")
        return None


# ==========================================
# Core Embedding Extraction Pipeline
# ==========================================
def extract_all_face_embeddings(frame: np.ndarray) -> List[np.ndarray]:
    """
    Detects faces, filters invalid/zero embeddings, and returns L2-normalized vectors.
    """
    if frame is None or frame.size == 0:
        return []

    faces = recognizer.get(frame)
    embeddings = []

    for face in faces:
        if face.embedding is None:
            continue

        bbox = face.bbox
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w < 40 or h < 40:
            continue

        emb = np.array(face.embedding, dtype=np.float32).copy()
        
        # Guard against dead/zero embeddings
        if np.std(emb) < 0.01:
            continue

        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
            embeddings.append(emb)

    return embeddings


def extract_primary_face_embedding(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    Extracts valid L2-normalized embedding for the largest face in a query selfie.
    """
    if frame is None or frame.size == 0:
        return None

    faces = recognizer.get(frame)
    if not faces:
        print("No faces detected in selfie frame.")
        return None

    # Sort faces by bounding box area (largest first)
    faces = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

    for primary_face in faces:
        w = primary_face.bbox[2] - primary_face.bbox[0]
        h = primary_face.bbox[3] - primary_face.bbox[1]
        if w < 50 or h < 50:
            continue

        if primary_face.embedding is None:
            continue

        emb = np.array(primary_face.embedding, dtype=np.float32).copy()
        emb_std = np.std(emb)

        # Check for uninitialized zero vectors
        if emb_std < 0.01:
            print(f"Warning: Extracted embedding has near-zero variance (std={emb_std:.6f}). Skipping invalid detection.")
            continue

        norm = np.linalg.norm(emb)
        if norm > 0:
            return emb / norm

    return None