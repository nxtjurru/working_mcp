from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from datetime import datetime
import sys
import cv2

# Folder where docs are stored
DOCS_DIR = Path(__file__).parent / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Folder where captured photos are saved
PHOTOS_DIR = DOCS_DIR / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

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

@mcp.tool()
def capture_camera_image(camera_index: int = 0) -> Image:
    """
    Capture a photo from the system's camera/webcam and return it as an image.
    Use camera_index to select which camera to use (0 = default webcam).
    The photo is also saved to the documents folder as 'captured_photo.jpg'.
    """
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open camera at index {camera_index}. Make sure a camera is connected.")

    # Allow camera to warm up by reading a few frames
    for _ in range(5):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Failed to capture image from camera.")

    # Save a copy to disk with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = PHOTOS_DIR / f"photo_{timestamp}.jpg"
    cv2.imwrite(str(save_path), frame)

    # Encode frame as JPEG raw bytes
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise RuntimeError("Failed to encode camera image.")

    return Image(data=buffer.tobytes(), format="jpeg")

if __name__ == "__main__":
    print("Weather Server is starting...", file=sys.stderr)
    mcp.run()
