import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import shutil
from fastapi.responses import FileResponse
import uuid

app = FastAPI()

class ScrapeRequest(BaseModel):
    base_url: str
    folder: str = "downloads"

visited = set()
MAX_PAGES = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

file_types = {
    "pdf": [".pdf"],
    "word": [".doc", ".docx"],
    "excel": [".xls", ".xlsx"]
}

# ---------------- DOWNLOAD FILE ----------------
def download_file(url, folder):
    os.makedirs(folder, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0]
    filepath = os.path.join(folder, filename)

    if os.path.exists(filepath):
        return

    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code == 200 and resp.content:
        with open(filepath, "wb") as f:
            f.write(resp.content)
        print("Downloaded:", filename)

# ---------------- SCRAPER ----------------
def scrape(url, base_url, base_folder, main_folder):
    if url in visited or len(visited) >= MAX_PAGES:
        return

    visited.add(url)
    print("Scraping:", url)

    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.find_all("a", href=True)

    print("Links found:", len(links))

    for link in links:
        file_url = urljoin(url, link["href"])
        lower = file_url.lower()

        for folder_name, exts in file_types.items():
            if any(lower.endswith(ext) for ext in exts):
                target = os.path.join(base_folder, main_folder, folder_name)
                download_file(file_url, target)

        if file_url.startswith(base_url):
            scrape(file_url, base_url, base_folder, main_folder)

# ---------------- API ----------------
@app.post("/scrape_files")
def scrape_files(request: ScrapeRequest):
    visited.clear()

    base_folder = os.path.join("/tmp", str(uuid.uuid4()))
    os.makedirs(base_folder, exist_ok=True)

    scrape(
        request.base_url,
        request.base_url,
        base_folder,
        request.folder
    )

    # ❗ CHECK IF FILES EXIST
    has_files = any(files for _, _, files in os.walk(base_folder))
    if not has_files:
        raise HTTPException(
            status_code=400,
            detail="No files found. Target site may block scraping."
        )

    zip_path = shutil.make_archive(base_folder, 'zip', base_folder)

    return FileResponse(
        zip_path,
        filename="downloaded_files.zip",
        media_type="application/zip",
        headers={"Content-Disposition": "attachment"}
    )
