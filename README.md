
# 📸 Event Photo Finder

An AI-powered event photo search platform. Users can submit a selfie or capture an image via webcam to instantly find all photos containing their face across large, multi-folder Google Drive event albums.

Powered by **FastAPI**, **InsightFace (\`buffalo_l\` / ArcFace)**, **SQLite**, and **Asyncio**.

---

## 🌟 Key Features

* **Facial Recognition Engine**: Uses InsightFace (\`buffalo_l\`) to extract 512-dimensional feature vectors and perform cosine similarity searches across crowded event albums.
* **Recursive Google Drive Traversal**: Automatically scans parent folders and all nested subfolders using Breadth-First Search (BFS) to index photos stored at any depth.
* **Async In-Memory Pipeline**: Downloads and decodes image streams in parallel directly into OpenCV memory frames to maximize indexing throughput.
* **Webcam & File Upload UI**: Clean browser interface for real-time selfie capture and instant result previews.
* **Asynchronous Background Tasks**: Offloads album indexing to background wrappers with polling status endpoints to prevent server timeouts.
* **Fully Containerized**: Ready for single-command deployment via Docker without manually configuring machine learning dependencies.

---


## 🛠️ Prerequisites & API Setup

### 🔑 How to Get a Google Drive API Key

To fetch photo metadata from shared Google Drive folders, you need a Google Drive API key:

1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** at the top bar and create a **New Project**.
3. Open the left sidebar menu and navigate to **APIs & Services > Library**.
4. Search for **Google Drive API**, click it, and press **Enable**.
5. Go to **APIs & Services > Credentials**.
6. Click **+ Create Credentials** at the top and choose **API key**.
7. Copy your API Key to use during startup.

---

## 🚀 How to Launch

### Option 1: Using Docker (Recommended — No Setup Required)

Docker packages Python, OpenCV, C++ build tools, and all machine learning libraries into an isolated container. You **do not** need to install Python or any dependencies manually.

1. **Clone the repository:**
   \`\`\`bash
   git clone https://github.com/IAmine314/Photo-Finder.git
   cd Photo-Finder
   \`\`\`

2. **Build the Docker container:**
   \`\`\`bash
   docker build -t photo-finder .
   \`\`\`

3. **Run the application:**
   \`\`\`bash
   docker run -d -p 8000:8000 -e GOOGLE_API_KEY="YOUR_GOOGLE_DRIVE_API_KEY" photo-finder
   \`\`\`

4. **Access the web app:**
   Open \`http://localhost:8000\` in your browser.

---

### Option 2: Native Python Run (For Local Development)

If you want to modify or run the Python code directly:

1. **Prerequisites:**
   * Python 3.10+
   * Google Drive API Key

2. **Clone & enter directory:**
   \`\`\`bash
   git clone https://github.com/IAmine314/Photo-Finder.git
   cd Photo-Finder
   \`\`\`

3. **Set up environment variables:**
   Create a \`.env\` file in the project root:
   \`\`\`env
   GOOGLE_API_KEY=YOUR_GOOGLE_DRIVE_API_KEY
   \`\`\`

4. **Create a virtual environment & install dependencies:**
   \`\`\`powershell
   python -m venv venv
   .\venv\Scripts\Activate
   pip install --upgrade pip
   pip install -r requirements.txt
   \`\`\`

5. **Start the server:**
   \`\`\`bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   \`\`\`

6. **Access the web app:**
   Open \`http://127.0.0.1:8000\` in your browser. API docs are available at \`http://127.0.0.1:8000/docs\`.

---

## 📖 How to Use

1. **Index an Event Album**:
   * Paste a public Google Drive folder URL (e.g., \`https://drive.google.com/drive/folders/...\`) into the **Index Album** section.
   * Click **Start Indexing**. The server will recursively traverse all subfolders, extract face embeddings, and store them in SQLite.

2. **Search for Your Face**:
   * Switch to the **Search Face** section.
   * Capture a selfie using your webcam or upload a clear photo of your face.
   * Click **Search Photos** to find matching images across the indexed album.

---

## 🔗 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| \`GET\` | \`/\` | Serves the main web interface |
| \`POST\` | \`/api/index-drive\` | Initiates background Google Drive album traversal & indexing |
| \`GET\` | \`/api/index-status/{task_id}\` | Polls status for an ongoing background indexing task |
| \`POST\` | \`/api/search-face\` | Accepts base64 selfie data and returns matching photo URLs |

---
