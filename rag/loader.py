"""Read a PDF into one Markdown Document per page.

pymupdf4llm preserves the layout that plain text extraction destroys: headings
arrive as '#' markers and tables as '|'-delimited Markdown. That structure is
what rag/chunker.py splits on, so parsing and chunking stay separate concerns.
"""

import re
import unicodedata
from pathlib import Path

import pymupdf4llm
from langchain_core.documents import Document

# A page whose text begins one of these starts an internal workflow form.
# Everything from there to the end of the document is dropped: it is a process
# artifact for staff to fill in, not policy content anyone would ask about.
FORM_START_MARKERS = (
    "complete this form",
    "send copy of completed form",
)


class LoaderError(RuntimeError):
    """Raised when a PDF cannot be read or yields nothing usable."""


"""Inline HTML that pymupdf4llm leaves in table cells and superscripts.
Left alone it reaches the embedding as literal '<br>' tokens."""
INLINE_HTML = re.compile(r"</?(?:br|sup|sub)\s*/?>", re.IGNORECASE)


def clean(text: str) -> str:
    """Normalise Word-template noise.

    pymupdf4llm already resolves the fi/fl ligatures that plain pypdf left in
    place, so NFKC here is mostly for non-breaking spaces and smart quotes.
    """
    text = unicodedata.normalize("NFKC", text)
    text = INLINE_HTML.sub(" ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)  # Word-template run-on spacing
    text = re.sub(r"[ \t]+\n", "\n", text)  # trailing whitespace on every line
    text = re.sub(r"\n{3,}", "\n\n", text)  # runs of blank lines
    return text.strip()


def load_pages(path: Path) -> tuple[list[Document], list[int]]:
    """Return (non-empty page Documents, page numbers that were blank).

    Blank pages are image-only covers and dividers. They are returned rather
    than silently dropped so the ingest report can show them.
    """
    try:
        raw_pages = pymupdf4llm.to_markdown(str(path), page_chunks=True, show_progress=False)
    except Exception as e:
        raise LoaderError(f"Cannot read PDF {path.name}: {type(e).__name__}: {e}") from e

    docs: list[Document] = []
    blank: list[int] = []
    for raw in raw_pages:
        # NOTE: the key is 'page_number' (1-based). pymupdf4llm also exposes a
        # 'page' key, but it is always None -- using it would stamp every chunk
        # with a null page and silently destroy citations.
        page_no = raw["metadata"]["page_number"]
        text = clean(raw["text"])
        if not text:
            blank.append(page_no)
            continue
        docs.append(Document(page_content=text, metadata={"page": page_no}))

    if not docs:
        raise LoaderError(f"{path.name}: every page was empty; nothing to ingest.")
    return docs, blank


def detect_form_start(pages: list[Document]) -> int | None:
    """First page after the cover that begins the form tail, or None."""
    for doc in pages:
        if doc.metadata["page"] == 1:
            continue
        low = doc.page_content.lower()
        if any(marker in low for marker in FORM_START_MARKERS):
            return doc.metadata["page"]
    return None


def drop_form_tail(pages: list[Document], expected: bool, filename: str) -> tuple[list[Document], list[int]]:
    """Drop the trailing form pages. Returns (kept, dropped page numbers).

    If the catalogue says a document has a form but no marker is found, that is
    raised rather than guessed at -- silently keeping the form would put an
    internal approval workflow into the answer path.
    """
    start = detect_form_start(pages)
    if start is None:
        if expected:
            raise LoaderError(
                f"{filename}: catalogue flags this document as containing a form, but none of "
                f"the markers {FORM_START_MARKERS} was found. Refusing to guess where it starts."
            )
        return pages, []

    kept = [d for d in pages if d.metadata["page"] < start]
    dropped = [d.metadata["page"] for d in pages if d.metadata["page"] >= start]
    if not kept:
        raise LoaderError(f"{filename}: form tail starts at page {start}, leaving no content.")
    return kept, dropped
