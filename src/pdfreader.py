import os
from pypdf import PdfReader

def read_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        reader = PdfReader(pdf_path)
        pages = [page.extract_text() for page in reader.pages]
        return pages
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []