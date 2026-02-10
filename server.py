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

# Supported file extensions for reading
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


# ── Helper readers ──────────────────────────────────────────────────────────

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

def _read_file(file_path: Path) -> str:
    """Internal helper to read any supported file."""
    if file_path.suffix == ".pdf":
        return read_pdf(file_path)
    if file_path.suffix == ".docx":
        return read_docx(file_path)
    if file_path.suffix == ".txt":
        return read_txt(file_path)
    return ""


# ── Build a document summary at startup for tool descriptions ───────────────

def _build_document_summary() -> str:
    """Scan all documents at startup and build a brief summary of content."""
    summaries = []
    for doc_file in DOCS_DIR.iterdir():
        if doc_file.is_file() and doc_file.suffix in SUPPORTED_EXTENSIONS:
            try:
                content = _read_file(doc_file)
                if not content:
                    continue
                preview = content[:500].strip()
                summaries.append(f"  - {doc_file.name}: {preview}")
            except Exception:
                summaries.append(f"  - {doc_file.name}: (could not read)")
    if summaries:
        return "Documents currently stored:\n" + "\n".join(summaries)
    return "No documents currently stored."

DOCUMENT_SUMMARY = _build_document_summary()


# ── Build the tool description as a normal string (NOT an f-string docstring) ─

CHECK_LOCAL_DATA_DESCRIPTION = (
    "IMPORTANT: You MUST call this tool FIRST before answering ANY user question. "
    "This tool searches through ALL locally stored documents that contain personal "
    "records, contact details, names, addresses, emails, phone numbers, job titles, "
    "income data, and other critical information.\n\n"
    "ALWAYS call this as your FIRST action for EVERY query. Do NOT answer from memory. "
    "Do NOT search the web first. Call this tool FIRST, every single time.\n\n"
    + DOCUMENT_SUMMARY + "\n\n"
    "When to call this tool: ALWAYS — for every query, no exceptions.\n"
    "Examples:\n"
    "- User asks about a person's name -> CALL THIS FIRST\n"
    "- User asks about an address -> CALL THIS FIRST\n"
    "- User asks about contact info -> CALL THIS FIRST\n"
    "- User asks about income or job -> CALL THIS FIRST\n"
    "- User asks about ANY topic -> CALL THIS FIRST (check docs, then fall back)\n"
)

SAVE_DATA_DESCRIPTION = (
    "Use this tool to SAVE or STORE information that the user provides into "
    "trial_document.txt. You MUST call this tool whenever the user asks you to "
    "save, store, remember, record, add, or write down any information.\n\n"
    "The data MUST be formatted as tab-separated key-value pairs, one per line, "
    "matching the existing format in trial_document.txt:\n"
    "  Name\tFull Name\n"
    "  Address\tFull Address\n"
    "  Contact\tPhone Number\n"
    "  Email\tEmail Address\n"
    "  Job\tJob Title\n"
    "  Income\tIncome Details\n\n"
    "You may include any relevant fields — not just the ones listed above. "
    "Omit fields the user did not provide rather than guessing.\n\n"
    "WHEN TO USE:\n"
    "- User says 'save this', 'store this', 'remember this', 'add this', "
    "'write this down', 'note this' -> CALL THIS TOOL\n"
    "- User provides personal details and asks you to keep them -> CALL THIS TOOL\n"
    "- User says 'update the document' or 'add to the file' -> CALL THIS TOOL\n"
)


# ── Create MCP server ──────────────────────────────────────────────────────

mcp = FastMCP(
    "Document Reader & Writer MCP",
    instructions=(
        "MANDATORY RULES — FOLLOW THESE FOR EVERY SINGLE USER MESSAGE:\n\n"
        "RULE 1 — READING: ALWAYS call the tool 'check_local_data' FIRST, before doing "
        "anything else, to search locally stored personal records.\n"
        "RULE 2 — WRITING: When the user asks you to save, store, remember, record, add, "
        "or write down ANY information, you MUST call the 'save_to_document' tool. "
        "Format the data as tab-separated key-value pairs matching trial_document.txt.\n\n"
        "Step 1: ALWAYS call 'check_local_data' FIRST.\n"
        "Step 2: Read the results.\n"
        "Step 3: If the user wants to SAVE information, call 'save_to_document'.\n"
        "Step 4: If the results contain relevant information, use THAT to answer.\n"
        "Step 5: ONLY if no local data is found may you use your own knowledge.\n"
        "\n"
        "This server contains personal records, contact information, names, addresses, "
        "emails, phone numbers, job titles, income details, and other critical data. "
        "You MUST check 'check_local_data' first for ANY query — especially queries about "
        "people, names, contacts, or any factual information. NEVER skip this step.\n"
        "\n"
        + DOCUMENT_SUMMARY
    ),
)


# ── PRIMARY TOOL — call this FIRST for every query ─────────────────────────

@mcp.tool(description=CHECK_LOCAL_DATA_DESCRIPTION)
def check_local_data(query: str) -> str:
    """Search all local documents for information relevant to the query."""
    results = []
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) > 1]

    doc_files = [
        f for f in DOCS_DIR.iterdir()
        if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS
    ]

    if not doc_files:
        return (
            "No documents found in local store. "
            "You may now answer from your own knowledge."
        )

    for doc_file in doc_files:
        try:
            content = _read_file(doc_file)
            if not content:
                continue

            lines = content.splitlines()
            matched_lines = []

            for line in lines:
                line_lower = line.lower()
                if any(word in line_lower for word in query_words):
                    matched_lines.append(line)

            if matched_lines:
                results.append(
                    f"── From {doc_file.name} ──\n" + "\n".join(matched_lines)
                )
            else:
                # Include full content so Claude can reason over it
                results.append(
                    f"── Full content of {doc_file.name} (no direct keyword match, "
                    f"review this data carefully) ──\n" + content
                )
        except Exception as e:
            results.append(f"── Error reading {doc_file.name}: {e} ──")

    if results:
        return "\n\n".join(results)

    return (
        "No relevant information found in local documents. "
        "You may now answer from your own knowledge."
    )


# ── Supporting tools ────────────────────────────────────────────────────────

@mcp.tool()
def list_documents() -> list[str]:
    """List all documents available on the local server."""
    files = [f.name for f in DOCS_DIR.iterdir() if f.is_file()]
    if not files:
        return ["No documents found."]
    return files

@mcp.tool()
def read_document(filename: str) -> str:
    """Read the full contents of a specific document (PDF, DOCX, or TXT)."""
    file_path = DOCS_DIR / filename
    if not file_path.exists():
        return "File not found."
    content = _read_file(file_path)
    return content if content else "Unsupported file format."

@mcp.tool()
def search_document(filename: str, query: str) -> str:
    """Search for specific text inside a stored document. Returns matching lines."""
    content = read_document(filename)
    if content == "File not found.":
        return content
    lines = content.splitlines()
    matches = [line for line in lines if query.lower() in line.lower()]
    return "\n".join(matches[:10]) if matches else "No relevant content found."


# ── SAVE TOOL — write structured data to trial_document.txt ────────────────

@mcp.tool(description=SAVE_DATA_DESCRIPTION)
def save_to_document(data: str) -> str:
    """Save structured information to trial_document.txt.

    Args:
        data: Tab-separated key-value pairs, one per line.
              Example:
                  Name\tJohn Doe
                  Address\t123 Main Street, City
                  Contact\t+91-9876543210
                  Email\tjohn@email.com
                  Job\tEngineer
                  Income\t₹10,00,000 / year
    """
    file_path = DOCS_DIR / "trial_document.txt"

    if not data or not data.strip():
        return "❌ No data provided. Please provide information to save."

    try:
        existing = ""
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")

        # Ensure a blank-line separator between records
        if existing.strip():
            new_content = existing.rstrip("\n") + "\n\n" + data.strip() + "\n"
        else:
            new_content = data.strip() + "\n"

        file_path.write_text(new_content, encoding="utf-8")
        return f"✅ Data saved successfully to {file_path.name}."
    except PermissionError:
        return "❌ Permission denied: cannot write to trial_document.txt."
    except OSError as e:
        return f"❌ File system error while saving: {e}"
    except Exception as e:
        return f"❌ Unexpected error while saving: {e}"


@mcp.tool()
def capture_camera_image(camera_index: int = 0) -> Image:
    """Capture a live photo from the system's camera/webcam and return it as an image.
    Use camera_index to select which camera (0 = default webcam).
    The photo is saved to the documents/photos folder with a timestamp."""
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open camera at index {camera_index}.")

    for _ in range(5):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Failed to capture image from camera.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = PHOTOS_DIR / f"photo_{timestamp}.jpg"
    cv2.imwrite(str(save_path), frame)

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise RuntimeError("Failed to encode camera image.")

    return Image(data=buffer.tobytes(), format="jpeg")


# ── MCP Resources — expose documents so Claude can see them directly ────────

@mcp.resource("docs://documents/list")
def resource_list_documents() -> str:
    """List all documents available in the local store."""
    files = [f.name for f in DOCS_DIR.iterdir() if f.is_file()]
    if not files:
        return "No documents found."
    return "Available documents:\n" + "\n".join(f"  - {f}" for f in files)

@mcp.resource("docs://documents/all")
def resource_all_documents() -> str:
    """Full contents of all stored documents — personal records, contacts, etc."""
    results = []
    for doc_file in DOCS_DIR.iterdir():
        if doc_file.is_file() and doc_file.suffix in SUPPORTED_EXTENSIONS:
            try:
                content = _read_file(doc_file)
                results.append(f"── {doc_file.name} ──\n{content}")
            except Exception as e:
                results.append(f"── {doc_file.name} (error: {e}) ──")
    return "\n\n".join(results) if results else "No documents found."


if __name__ == "__main__":
    print("Document Reader MCP Server is starting...", file=sys.stderr)
    mcp.run()
