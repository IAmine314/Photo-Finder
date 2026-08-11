# 📸 Event Photo Finder

An AI-powered event photo search platform. This application allows users to submit a selfie or capture an image via webcam to find all photos containing their face across large Google Drive event albums.

Powered by **FastAPI**, **InsightFace (`buffalo_l` / ArcFace)**, **SQLite**, and **Asyncio**.

---

## 🌟 Key Features

* **Facial Recognition Engine**: Uses InsightFace (`buffalo_l`) to extract 512-dimensional feature embeddings and perform accurate cosine similarity search across crowd shots.
* **Recursive Google Drive Indexing**: Traverses parent folders and all nested subfolders to stream and index images in parallel memory pipelines.
* **Webcam & File Upload UI**: Clean browser UI for real-time selfie capture and instant match previews.
* **Asynchronous Background Processing**: Offloads large album scanning to FastAPI background tasks with real-time status tracking.
* **Docker Ready**: Pre-configured `Dockerfile` for seamless deployment to container hosting providers.

---

## 📂 Project Structure

```text
event-photo-finder/
├── static/
│   ├── index.html        # Web interface layout
│   ├── css/styles.css    # Responsive styling
│   └── js/app.js         # Frontend webcam & API orchestration
├── data/                 # Auto-created SQLite vector storage
├── config.py             # App configurations & settings
├── database.py           # SQLAlchemy ORM models & session management
├── drive_service.py      # Google Drive API traversal & streaming pipeline
├── ml_pipeline.py        # InsightFace embedding extractions
├── main.py               # FastAPI endpoints & background tasks
├── Dockerfile            # Container build specification
├── requirements.txt      # Python dependencies
└── README.md
