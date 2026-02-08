
import uvicorn
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader # For PDF text extraction
from docx import Document # For DOCX text extraction
import io # For handling file in memory
import os # For path operations
import yaml # For reading configuration file

# --- Configuration Loading ---
def load_config(config_path: str = "config.yaml"):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

app = FastAPI()

# Mount static files to serve the HTML frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the file upload frontend."""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "ingestion_endpoint": CONFIG["ingestion_endpoint"]}
    )

@app.post(CONFIG["ingestion_endpoint"])
async def create_upload_file(file: UploadFile = File(...)):
    """Handle file uploads, validate document types, and extract raw text."""
    
    # Define allowed document types and their corresponding MIME types/extensions
    ALLOWED_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt"
    }

    # Get file extension from filename or content type
    file_extension = os.path.splitext(file.filename)[1].lower().lstrip('.')
    content_type = file.content_type

    # Validate file type
    if content_type not in ALLOWED_MIME_TYPES or ALLOWED_MIME_TYPES[content_type] != file_extension:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only PDF, DOCX, and TXT documents are allowed. "
                   f"Received Content-Type: {content_type}, Extension: .{file_extension}"
        )
    
    extracted_text = ""
    try:
        # Read the file content into an in-memory buffer
        contents = await file.read()
        file_like_object = io.BytesIO(contents)

        if file_extension == "pdf":
            reader = PdfReader(file_like_object)
            for page in reader.pages:
                extracted_text += page.extract_text() or ""
        elif file_extension == "docx":
            document = Document(file_like_object)
            for para in document.paragraphs:
                extracted_text += para.text + "\n"
        elif file_extension == "txt":
            extracted_text = file_like_object.read().decode("utf-8")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

    

    return {
        "filename": file.filename,
        "content_type": content_type,
        "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
        "full_text_length": len(extracted_text)
    }

if __name__ == "__main__":
    uvicorn.run(app, host=CONFIG["hostname"], port=CONFIG["port"])
