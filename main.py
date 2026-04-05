from fastapi import FastAPI, UploadFile, File
import uuid
import os
import shutil

from src.ingest import ingest
from src.query import answer

import time
app = FastAPI()


# Store memory per session
chat_memory = {}

# Directory to store uploaded PDFs
UPLOAD_DIR = "uploaded_pdfs"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "docmind", "timestamp": time.time()}

@app.get("/")
def root():
    return {"message": "Welcome! RAG API is running."}
# ---------------------------------------------------
# Upload PDF endpoint
# ---------------------------------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    # Create unique session id
    session_id = str(uuid.uuid4())

    # Save uploaded PDF
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Ingest PDF into Pinecone namespace, returns chunk count
    chunk_count = ingest(file_path, namespace=session_id)

    # Initialize chat memory with history and chunk count
    chat_memory[session_id] = {
        "history": [],
        "chunk_count": chunk_count
    }

    return {
        "message": "PDF uploaded and ingested successfully",
        "session_id": session_id
    }

# ---------------------------------------------------
# Ask question endpoint
# ---------------------------------------------------
@app.post("/ask")
async def ask_question(session_id: str, question: str):

    # Retrieve session — fallback if session not found
    session = chat_memory.get(session_id, {"history": [], "chunk_count": 20})
    history = session["history"]
    chunk_count = session["chunk_count"]

    # Get answer
    response = answer(question, session_id, history, chunk_count=chunk_count)

    # Update memory
    session["history"].append((question, response))
    chat_memory[session_id] = session

    return {
        "answer": response
    }