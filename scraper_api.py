import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from fastapi import FastAPI
from pydantic import BaseModel
import fitz  # PyMuPDF
from openpyxl import Workbook

app = FastAPI()

class ScrapeRequest(BaseModel):
    base_url: str
    save_path: str
    folder: str = "downloads"

visited = set()

file_types = {
    "pdf": [".pdf"],
    "word": [".doc", ".docx"],
    "excel": [".xls", ".xlsx"]
}

# ---------------- DOWNLOAD FILE ----------------
def download_file(url, folder):
    os.makedirs(folder, exist_ok=True)
    filename = url.split("/")[-1]
    filepath = os.path.join(folder, filename)

    if not os.path.exists(filepath):
        resp = requests.get(url)
        with open(filepath, "wb") as f:
            f.write(resp.content)
        print(f"Downloaded: {filename}")

# ---------------- SCRAPER ----------------
def scrape(url, base_url, save_path, main_folder):
    if url in visited:
        return
    visited.add(url)

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            file_url = urljoin(url, link["href"])
            lower = file_url.lower()

            for folder_name, extensions in file_types.items():
                if any(lower.endswith(ext) for ext in extensions):
                    target_folder = os.path.join(save_path, main_folder, folder_name)
                    download_file(file_url, target_folder)

            next_url = urljoin(url, link["href"])
            if next_url.startswith(base_url):
                scrape(next_url, base_url, save_path, main_folder)

    except Exception as e:
        print("Error:", e)

# ---------------- PDF → EXCEL REPORT ----------------
def generate_pdf_report(pdf_folder):
    excel_path = os.path.join(pdf_folder, "pdf_page_counts.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "PDF Page Count"
    ws.append(["Filename", "Number of Pages",'Result/Output'])

    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(pdf_folder, filename)
            try:
                doc = fitz.open(file_path)
                ws.append([filename, doc.page_count])
                doc.close()
            except Exception as e:
                ws.append([filename, "Error"])

    wb.save(excel_path)

# ---------------- API ENDPOINT ----------------
@app.post("/scrape_files")
def scrape_files(request: ScrapeRequest):
    visited.clear()

    scrape(
        request.base_url,
        request.base_url,
        request.save_path,
        request.folder
    )

    pdf_folder = os.path.join(request.save_path, request.folder, "pdf")
    if os.path.exists(pdf_folder):
        generate_pdf_report(pdf_folder)

    return {
        "message": "Download completed",
        "saved_at": os.path.join(request.save_path, request.folder)
    }



#uvicorn scraper_api:app --reload

