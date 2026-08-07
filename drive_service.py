import re
import asyncio
import aiohttp
from typing import List, Dict, Optional
from googleapiclient.discovery import build

from config import settings
from database import SessionLocal, EventPhoto, PhotoFaceEmbedding, clear_all_indexed_photos
from ml_pipeline import decode_bytes_to_cv2, extract_all_face_embeddings

# ==========================================
# Google Drive Helper Functions
# ==========================================
def extract_folder_id(drive_url_or_id: str) -> Optional[str]:
    drive_url_or_id = drive_url_or_id.strip()
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", drive_url_or_id)
    if match:
        return match.group(1)
    
    if re.match(r"^[a-zA-Z0-9_-]{25,}$", drive_url_or_id):
        return drive_url_or_id
        
    return None


def fetch_drive_image_metadata(folder_id: str) -> List[Dict[str, str]]:
    """
    Queries Google Drive API v3 for all image files and constructs 
    direct public media CDN URLs to avoid HTTP 403 restrictions.
    """
    drive_service = build('drive', 'v3', developerKey=settings.GOOGLE_API_KEY)
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    
    results = drive_service.files().list(
        q=query,
        pageSize=1000,
        fields="nextPageToken, files(id, name, thumbnailLink, webViewLink)"
    ).execute()
    
    files = results.get('files', [])
    items = []
    
    for f in files:
        # lh3 URL bypasses API 403 downloads for public shared files
        download_url = f"https://lh3.googleusercontent.com/d/{f['id']}"
        items.append({
            'id': f['id'],
            'name': f['name'],
            'url': download_url,
            'view_link': f['webViewLink']
        })
            
    return items


# ==========================================
# Async In-Memory Processing Pipeline
# ==========================================
async def process_single_image(
    session: aiohttp.ClientSession, 
    item: Dict[str, str], 
    semaphore: asyncio.Semaphore
):
    async with semaphore:
        try:
            # User-Agent header helps avoid unexpected bot blocks on CDN streams
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with session.get(item['url'], headers=headers, timeout=20) as response:
                if response.status != 200:
                    print(f"Failed to stream {item['name']}: HTTP {response.status}")
                    return

                img_bytes = await response.read()
                frame = decode_bytes_to_cv2(img_bytes)
                del img_bytes

                if frame is None:
                    print(f"Skipping {item['name']}: Could not decode image frame.")
                    return

                embeddings = extract_all_face_embeddings(frame)
                del frame

                if not embeddings:
                    print(f"No faces detected in: {item['name']}")
                    return

                print(f"Successfully indexed {len(embeddings)} face(s) from: {item['name']}")

                db = SessionLocal()
                try:
                    existing = db.query(EventPhoto).filter(EventPhoto.drive_file_id == item['id']).first()
                    if existing:
                        db.close()
                        return

                    photo = EventPhoto(
                        drive_file_id=item['id'],
                        file_name=item['name'],
                        view_link=item['view_link']
                    )
                    db.add(photo)
                    db.commit()
                    db.refresh(photo)

                    for vec in embeddings:
                        face_record = PhotoFaceEmbedding(photo_id=photo.id)
                        face_record.set_vector(vec)
                        db.add(face_record)

                    db.commit()
                except Exception as db_err:
                    db.rollback()
                    print(f"Database error while saving {item['name']}: {db_err}")
                finally:
                    db.close()

        except Exception as e:
            print(f"Error processing image stream '{item['name']}': {e}")


async def index_drive_folder_task(drive_url_or_id: str):
    folder_id = extract_folder_id(drive_url_or_id)
    if not folder_id:
        print(f"Invalid Google Drive folder link or ID: {drive_url_or_id}")
        return
    clear_all_indexed_photos()
    print(f"Fetching file list for Drive Folder ID: {folder_id}...")
    try:
        items = fetch_drive_image_metadata(folder_id)
    except Exception as err:
        print(f"Failed to retrieve Google Drive metadata: {err}")
        return

    print(f"Found {len(items)} images. Starting parallel in-memory stream indexing...")

    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_DOWNLOADS)

    async with aiohttp.ClientSession() as session:
        tasks = [process_single_image(session, item, semaphore) for item in items]
        await asyncio.gather(*tasks)

    print("Google Drive indexing complete! All vectors stored in database.")