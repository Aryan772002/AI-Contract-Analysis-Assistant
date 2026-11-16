"""FastAPI PDF upload and processing endpoint for the contract assistant."""

from pathlib import Path
import os
import sys

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from contract_assistant.ingest import chunk_pages, extract_pages
from contract_assistant.qa import answer_contract_question
from contract_assistant.risk_analysis import analyze_contract_risks
from contract_assistant.summarize import summarize_contract

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_local_env(path: Path) -> None:
    """Load simple KEY=value entries without a third-party package."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("\"'")
        os.environ.setdefault(key.strip(), value)


load_local_env(PROJECT_ROOT / ".env")

app = FastAPI(title="Contract Assistant API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 15 * 1024 * 1024


@app.get("/api/health")
def health():
    return {"status": "ok"}


async def read_uploaded_pdf(file: UploadFile):
    """Validate and process one PDF without writing it to disk."""
    try:
        if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Please upload a PDF file.")
        if file.content_type not in ("application/pdf", "application/octet-stream"):
            raise HTTPException(status_code=400, detail="The uploaded file must be a PDF.")

        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="PDF must be 15 MB or smaller.")
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The file does not look like a valid PDF.")

        pages = extract_pages(content)
        if not pages:
            raise HTTPException(status_code=422, detail="This PDF has no pages.")
        pages_with_text = sum(bool(text.strip()) for _, text in pages)
        if not pages_with_text:
            raise HTTPException(
                status_code=422,
                detail="No selectable text was found. This may be a scanned or blank PDF; OCR support is a later step.",
            )
        chunks = chunk_pages(pages)
    finally:
        await file.close()

    return Path(file.filename).name, pages, chunks


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Read a PDF in memory and return extraction metadata; do not persist it."""
    try:
        filename, pages, chunks = await read_uploaded_pdf(file)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this PDF. Try another file.") from exc

    return {
        "filename": filename,
        "page_count": len(pages),
        "pages_with_text": sum(bool(text.strip()) for _, text in pages),
        "chunk_count": len(chunks),
        "message": "Upload complete. Text is ready for the next processing step.",
    }


@app.post("/api/documents/summarize")
async def summarize_document(file: UploadFile = File(...)):
    """Extract a contract summary and key fields with the configured Groq model."""
    try:
        filename, pages, _chunks = await read_uploaded_pdf(file)
        full_text = "\n\n".join(text for _, text in pages if text.strip())
        summary = summarize_contract(full_text)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        status_code = 503 if "API key" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not generate a summary. Check the Groq configuration and try again.") from exc

    return {"filename": filename, "page_count": len(pages), **summary}


@app.post("/api/documents/ask")
async def ask_document(file: UploadFile = File(...), question: str = Form(...)):
    """Answer a contract question from retrieved page-aware chunks."""
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Enter a question about the document.")
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Questions must be 1,000 characters or fewer.")
    try:
        filename, _pages, chunks = await read_uploaded_pdf(file)
        result = answer_contract_question(question, chunks)
    except HTTPException:
        raise
    except RuntimeError as exc:
        status_code = 503 if "API key" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not process the question for this PDF.") from exc
    return {"filename": filename, **result}


@app.post("/api/documents/risks")
async def analyze_document_risks(file: UploadFile = File(...)):
    """Return preliminary risk review signals with original clause excerpts."""
    try:
        filename, _pages, chunks = await read_uploaded_pdf(file)
        result = analyze_contract_risks(chunks)
    except HTTPException:
        raise
    except RuntimeError as exc:
        status_code = 503 if "API key" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not analyze this PDF for risk signals.") from exc
    return {"filename": filename, **result}
