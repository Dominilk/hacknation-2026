
import uvicorn
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader
from docx import Document
import io
import os
import xml.etree.ElementTree as ET
import datetime

from common import load_config, IngestAPIClient

CONFIG = load_config()

# It's good practice to ensure CONFIG.ingestion_endpoint is used for the client
# And CONFIG.ingestion_api_key might be None, which the IngestAPIClient handles.
INGEST_CLIENT = IngestAPIClient(CONFIG.ingestion_endpoint, CONFIG.ingestion_api_key)

app = FastAPI()

# Mount static files to serve the HTML frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the file upload frontend."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload") # Local upload endpoint for this FastAPI server, matches frontend
async def create_upload_file(file: UploadFile = File(...)):
    """
    Handle file uploads, validate document types, extract raw text,
    and forward the content as XML to the remote ingestion endpoint.
    """
    
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

    # --- XML Construction for Ingestion ---
    root = ET.Element("document")

    # Add metadata
    metadata_elem = ET.SubElement(root, "metadata")
    ET.SubElement(metadata_elem, "filename").text = file.filename
    ET.SubElement(metadata_elem, "content_type").text = content_type
    ET.SubElement(metadata_elem, "full_text_length").text = str(len(extracted_text))
    ET.SubElement(metadata_elem, "timestamp").text = datetime.datetime.now().isoformat() # Add timestamp

    # Add content
    content_elem = ET.SubElement(root, "content")
    content_elem.text = extracted_text

    xml_payload = ET.tostring(root, encoding="unicode", xml_declaration=True)

    try:
        # Send the XML payload to the remote ingestion endpoint
        # The IngestEvent expects 'content' as a string and 'metadata' as a dict.
        # Here, the entire XML is the 'content'.
        ingestion_response = await INGEST_CLIENT.ingest(xml_payload)
        
        return {
            "message": "File processed and forwarded for ingestion.",
            "filename": file.filename,
            "ingestion_status": "success",
            "remote_response": ingestion_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to forward file for ingestion: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host=CONFIG.hostname, port=CONFIG.port)
