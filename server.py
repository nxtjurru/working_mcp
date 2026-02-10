from mcp.server.fastmcp import FastMCP
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import sys

# Folder where docs are stored
DOCS_DIR = Path(__file__).parent / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("Document Reader MCP")

def read_pdf(file_path: Path) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def read_docx(file_path: Path) -> str:
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)

def read_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")

@mcp.tool()
def list_documents() -> list[str]:
    """
    List all available documents on the server
    """
    return [f.name for f in DOCS_DIR.iterdir() if f.is_file()]

@mcp.tool()
def read_document(filename: str) -> str:
    """
    Read the contents of a PDF, DOCX, or TXT file
    """
    file_path = DOCS_DIR / filename

    if not file_path.exists():
        return "File not found."

    if file_path.suffix == ".pdf":
        return read_pdf(file_path)

    if file_path.suffix == ".docx":
        return read_docx(file_path)

    if file_path.suffix == ".txt":
        return read_txt(file_path)

    return "Unsupported file format."

@mcp.tool()
def search_document(filename: str, query: str) -> str:
    """
    Search for relevant text inside a document
    """
    content = read_document(filename)
    if content == "File not found.":
        return content

    lines = content.splitlines()
    matches = [line for line in lines if query.lower() in line.lower()]

    return "\n".join(matches[:10]) if matches else "No relevant content found."

if __name__ == "__main__":
    print("Weather Server is starting...", file=sys.stderr)
    mcp.run()
