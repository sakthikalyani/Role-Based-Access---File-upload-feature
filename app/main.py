#main.py
from typing import Dict
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import os
from pathlib import Path
import shutil
from app.services.rag_service import rag_answer
from app.services.document_processor import process_document, save_as_markdown
from scripts.index_data import index_documents

app = FastAPI()
security = HTTPBasic()

USERS_DB: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "c-level"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"}
}

UPLOAD_BASE_DIR = "./uploaded_documents"
MARKDOWN_BASE_DIR = "./markdown_documents"

os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)
os.makedirs(MARKDOWN_BASE_DIR, exist_ok=True)

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = USERS_DB.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}

@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}

@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest, user=Depends(authenticate)):
    role = user["role"]
    answer = rag_answer(req.message, role)
    return {"answer": answer}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...), department: str = Form(...), user=Depends(authenticate)):
    if user["role"] != "c-level":
        raise HTTPException(status_code=403, detail="Only c-level users can upload documents")

    try:
        dept_upload_dir = os.path.join(UPLOAD_BASE_DIR, department)
        dept_markdown_dir = os.path.join(MARKDOWN_BASE_DIR, department)
        os.makedirs(dept_upload_dir, exist_ok=True)
        os.makedirs(dept_markdown_dir, exist_ok=True)

        upload_path = os.path.join(dept_upload_dir, file.filename)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ext = Path(file.filename).suffix.lower()

        if ext in [".csv", ".xlsx", ".xls"]:
            # ✅ Save raw CSV/Excel only, Pandas agent will pick it up
            return {
                "message": "CSV/Excel file saved successfully. It will be available via Pandas agent.",
                "filename": file.filename,
                "department": department
            }

        # Process & convert other formats → markdown
        text_content = process_document(upload_path)
        md_filename = Path(file.filename).stem + ".md"
        md_path = os.path.join(dept_markdown_dir, md_filename)

        metadata = {"department": department, "original_filename": file.filename, "uploaded_by": user["username"]}
        save_as_markdown(text_content, md_path, metadata)

        index_documents(MARKDOWN_BASE_DIR)

        return {
            "message": "Document processed and indexed successfully",
            "filename": file.filename,
            "department": department
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
