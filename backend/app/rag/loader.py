from pathlib import Path
import re


# Path to the knowledge base documents
KNOWLEDGE_BASE_DIR = (
    Path(__file__).resolve().parents[3]
    / "knowledge_base"
    / "documents"
)


def load_documents():
    """
    Load all Markdown documents from the knowledge base.
    """
    documents = []

    for file_path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        content = file_path.read_text(encoding="utf-8").strip()

        documents.append(
            {
                "filename": file_path.name,
                "content": content,
            }
        )

    return documents


def _split_long_section(
    heading: str,
    body: str,
    chunk_size: int,
):
    """
    Split a long Markdown section at paragraph boundaries.

    Unlike character-based chunking, this keeps headings attached to the
    relevant content and avoids cutting sentences in half.
    """
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", body)
        if paragraph.strip()
    ]

    if not paragraphs:
        return []

    chunks = []
    current = []

    def render(parts):
        text = "\n\n".join(parts).strip()
        if heading:
            return f"{heading}\n\n{text}".strip()
        return text

    for paragraph in paragraphs:
        candidate_parts = current + [paragraph]
        candidate = render(candidate_parts)

        if current and len(candidate) > chunk_size:
            chunks.append(render(current))
            current = [paragraph]
        else:
            current = candidate_parts

    if current:
        chunks.append(render(current))

    # Extremely long single paragraphs are split safely by sentence.
    final_chunks = []

    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
            continue

        sentences = re.split(r"(?<=[.!?])\s+", chunk)
        current_text = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            candidate = (
                f"{current_text} {sentence}".strip()
            )

            if current_text and len(candidate) > chunk_size:
                final_chunks.append(current_text)
                current_text = sentence
            else:
                current_text = candidate

        if current_text:
            final_chunks.append(current_text)

    return final_chunks


def chunk_markdown(
    text: str,
    chunk_size: int = 800,
):
    """
    Split Markdown by headings first, then by paragraphs.

    This produces semantic chunks such as:
        ## Return Window
        Customers can request...

    instead of arbitrary character slices that can produce:
        "Return Window Customers can request..."
    """
    text = text.replace("\r\n", "\n").strip()

    if not text:
        return []

    heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s*$",
        flags=re.MULTILINE,
    )

    matches = list(heading_pattern.finditer(text))
    sections = []

    if not matches:
        return _split_long_section(
            "",
            text,
            chunk_size,
        )

    # Preserve any introductory content before the first heading.
    if matches[0].start() > 0:
        intro = text[:matches[0].start()].strip()
        if intro:
            sections.append(("", intro))

    for index, match in enumerate(matches):
        heading = match.group(0).strip()

        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        body = text[start:end].strip()

        if body:
            sections.append((heading, body))

    chunks = []

    for heading, body in sections:
        chunks.extend(
            _split_long_section(
                heading,
                body,
                chunk_size,
            )
        )

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 0,
):
    """
    Backward-compatible wrapper.

    `overlap` is intentionally ignored for Markdown documents because
    overlapping character chunks were causing duplicate policy content.
    """
    return chunk_markdown(
        text=text,
        chunk_size=chunk_size,
    )


def load_and_chunk_documents():
    """
    Load all documents and create semantic Markdown chunks.
    """
    documents = load_documents()
    chunks = []

    for document in documents:
        document_chunks = chunk_markdown(
            document["content"],
            chunk_size=800,
        )

        for index, chunk in enumerate(document_chunks):
            chunks.append(
                {
                    "filename": document["filename"],
                    "chunk_id": index,
                    "content": chunk,
                }
            )

    return chunks
