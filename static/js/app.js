let currentQueryBase64 = null;
let webcamStream = null;
let indexPollInterval = null;

// Tab Switching Mechanism
function switchTab(tabId) {
  document
    .querySelectorAll(".tab-pane")
    .forEach((el) => el.classList.remove("active"));
  document
    .querySelectorAll(".segment-btn")
    .forEach((el) => el.classList.remove("active"));

  document.getElementById(tabId).classList.add("active");

  if (tabId === "uploadTab") {
    document.getElementById("btnUploadTab").classList.add("active");
    stopWebcam();
  } else {
    document.getElementById("btnWebcamTab").classList.add("active");
    startWebcam();
  }
}

// Drag and Drop Handling
const dropZone = document.getElementById("dropZone");
if (dropZone) {
  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(
      eventName,
      (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
      },
      false
    );
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(
      eventName,
      (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
      },
      false
    );
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      document.getElementById("selfieFileInput").files = files;
      handleFileSelect({ target: { files: files } });
    }
  });
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (e) {
    setQueryImage(e.target.result);
  };
  reader.readAsDataURL(file);
}

// Webcam Stream Management
async function startWebcam() {
  try {
    const video = document.getElementById("webcam");
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    });
    video.srcObject = webcamStream;
  } catch (err) {
    showStatus("indexStatus", "Webcam access error: " + err.message, "error");
  }
}

function stopWebcam() {
  if (webcamStream) {
    webcamStream.getTracks().forEach((track) => track.stop());
    webcamStream = null;
  }
}

function captureWebcam() {
  const video = document.getElementById("webcam");
  const canvas = document.getElementById("webcamCanvas");
  if (!video.srcObject) return;

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL("image/jpeg");
  setQueryImage(dataUrl);
}

function setQueryImage(dataUrl) {
  currentQueryBase64 = dataUrl;
  const preview = document.getElementById("selfiePreview");
  const previewContainer = document.getElementById("previewContainer");
  const searchBtn = document.getElementById("searchBtn");

  preview.src = dataUrl;
  previewContainer.style.display = "flex";
  searchBtn.disabled = false;
}

function clearPreview() {
  currentQueryBase64 = null;
  document.getElementById("selfiePreview").src = "";
  document.getElementById("previewContainer").style.display = "none";
  document.getElementById("searchBtn").disabled = true;
  document.getElementById("selfieFileInput").value = "";
}

// Status Display Helper
function showStatus(elementId, msg, type = "info") {
  const el = document.getElementById(elementId);
  el.className = `status-callout active ${type}`;
  if (elementId === "resultsStatus") {
    el.className = `status-banner active ${type}`;
  }
  el.innerText = msg;
}

// Backend API Operations with Task Status Polling
async function startIndexing() {
  const input = document.getElementById("driveLinkInput").value.trim();
  const indexBtn = document.getElementById("indexBtn");
  if (!input) {
    showStatus("indexStatus", "Paste a Drive folder URL or ID first.", "error");
    return;
  }

  indexBtn.disabled = true;
  showStatus("indexStatus", "Loading the roll…", "info");

  try {
    const response = await fetch("/api/index-drive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drive_link: input }),
    });

    const data = await response.json();

    if (response.ok && data.task_id) {
      showStatus("indexStatus", "Scanning frames and indexing faces…", "info");
      pollIndexStatus(data.task_id, indexBtn);
    } else {
      showStatus(
        "indexStatus",
        data.detail
          ? typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail)
          : "Indexing failed.",
        "error"
      );
      indexBtn.disabled = false;
    }
  } catch (err) {
    showStatus("indexStatus", "Couldn't reach the server.", "error");
    indexBtn.disabled = false;
  }
}

// Poll backend status endpoint until completion
function pollIndexStatus(taskId, indexBtn) {
  if (indexPollInterval) clearInterval(indexPollInterval);

  indexPollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/index-status/${taskId}`);
      const data = await res.json();

      if (data.status === "completed") {
        clearInterval(indexPollInterval);
        showStatus(
          "indexStatus",
          "Roll developed — folder indexed.",
          "success"
        );
        indexBtn.disabled = false;
      } else if (data.status === "failed") {
        clearInterval(indexPollInterval);
        showStatus("indexStatus", data.message || "Indexing failed.", "error");
        indexBtn.disabled = false;
      } else {
        const progressMsg =
          data.progress || "Scanning frames and indexing faces…";
        showStatus("indexStatus", progressMsg, "info");
      }
    } catch (err) {
      clearInterval(indexPollInterval);
      showStatus("indexStatus", "Error checking task status.", "error");
      indexBtn.disabled = false;
    }
  }, 2000);
}

async function performSearch() {
  if (!currentQueryBase64) return;

  const searchBtn = document.getElementById("searchBtn");
  const resultsGrid = document.getElementById("resultsGrid");
  const countBadge = document.getElementById("resultsCountBadge");

  searchBtn.disabled = true;
  resultsGrid.innerHTML = "";
  countBadge.style.display = "none";
  showStatus("resultsStatus", "Developing your contact sheet…", "info");

  try {
    const response = await fetch("/api/search-face", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: currentQueryBase64 }),
    });

    const data = await response.json();

    if (response.ok) {
      if (data.count === 0) {
        showStatus(
          "resultsStatus",
          "No frames matched your reference in this roll.",
          "info"
        );
      } else {
        showStatus(
          "resultsStatus",
          `Found you in ${data.count} photo${data.count === 1 ? "" : "s"}.`,
          "success"
        );
        countBadge.innerText = `${data.count} MATCH${
          data.count === 1 ? "" : "ES"
        }`;
        countBadge.style.display = "block";
        renderResults(data.results);
      }
    } else {
      showStatus("resultsStatus", data.detail || "Search failed.", "error");
    }
  } catch (err) {
    showStatus("resultsStatus", "Couldn't reach the server.", "error");
  } finally {
    searchBtn.disabled = false;
  }
}

function renderResults(photos) {
  const grid = document.getElementById("resultsGrid");
  grid.innerHTML = photos
    .map(
      (p) => `
    <div class="gallery-card">
      <div class="card-media">
        <img src="${p.preview_url}" alt="${p.file_name}" />
        <div class="card-overlay">
          <button class="overlay-btn" onclick="openLightbox('${p.preview_url}')">EXPAND</button>
          <a class="overlay-btn" href="${p.drive_link}" target="_blank" rel="noopener noreferrer">DRIVE</a>
        </div>
      </div>
      <div class="card-meta" title="${p.file_name}">${p.file_name}</div>
    </div>
  `
    )
    .join("");
}

// Lightbox Modal Controls
function openLightbox(src) {
  const lightbox = document.getElementById("lightbox");
  const img = document.getElementById("lightboxImg");
  img.src = src;
  lightbox.style.display = "flex";
}

function closeLightbox(e) {
  if (
    e.target.id === "lightbox" ||
    e.target.classList.contains("lightbox-close") ||
    e.target.classList.contains("lightbox-overlay")
  ) {
    document.getElementById("lightbox").style.display = "none";
  }
}
