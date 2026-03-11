import re
from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class Chunk:
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0

# Remove page numbers and clean up text
def clean_page(text: str) -> str:
    if not text:
        return ""
    # Remove page numbers (e.g., "Page 1 of 10")
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)

    text = re.sub(r"\n{3,}", "\n\n", text)  # Replace multiple newlines with a single newline
    
    lines = [line.rstrip() for line in text.splitlines()] # Remove trailing whitespace from each line

    return "\n".join(lines).strip()

# run clean_page on every page - Document level cleaning

def clean_pages(pages: List[str]) -> List[str]:

    cleaned = [clean_page(page) for page in pages]
    return "\n\n".join(c for c in cleaned if c)

# Regular expression to identify section headings (e.g., "SECTION I: Introduction")
RE_SECTION_HEADING = re.compile(
    r"^(SECTION\s+[IVXLCDM]+[\.\:]?\s+.+)$", re.IGNORECASE
)

# Regular expression to identify all-caps headings (e.g., "INTRODUCTION")
RE_ALL_CAPS_HEADING = re.compile(r"^[A-Z][A-Z\s\.\,]{8,}$")

# "1." or "1)" — top-level numbered items
RE_NUMBERED_ITEM = re.compile(r"^\s*(\d+)[\.\)]\s+(.+)$")

# "i." "ii." "iii." ... "x." — roman numeral sub-items
RE_ROMAN_ITEM = re.compile(
    r"^\s*(i{1,3}|iv|v|vi{1,3}|ix|x)[\.\)]\s+(.+)$", re.IGNORECASE
)

# "a." "b." "c." — lettered sub-items
RE_LETTERED_ITEM = re.compile(r"^\s*([a-zA-Z])[\.\)]\s+(.+)$")

# Table rows: lines containing two or more pipe characters OR a run of spaces
# that looks like tabular alignment (e.g. "Not exceeding 6 months    Nil")
RE_TABLE_ROW = re.compile(r"\|.+\||\s{4,}\S")

# Percentage values that appear in depreciation tables
RE_PERCENTAGE = re.compile(r"\d+%|Nil")

def classify_line(line: str) -> str:
    
    """
    Return a label for a single line
    labels:
    'section' - major section heading (e.g., "SECTION I: Introduction")
    'heading' - all-caps heading (e.g., "INTRODUCTION")
    'numbered' - top-level numbered item (e.g., "1. Introduction")
    'roman' - roman numeral sub-item (e.g., "i. Subsection")
    'lettered' - lettered sub-item (e.g., "a. Subsection")
    'table_row' - line that appears to be part of a table
    'blank' - empty line(paragraph break)
    'text' - regular prose
    """ 
    stripped = line.strip()
    if not stripped:
        return "blank"
    if RE_SECTION_HEADING.match(stripped):
        return "section"
    if RE_ALL_CAPS_HEADING.match(stripped):
        return "heading"
    if RE_NUMBERED_ITEM.match(stripped):
        return "numbered"
    if RE_ROMAN_ITEM.match(stripped):
        return "roman"
    if RE_LETTERED_ITEM.match(stripped):
        return "lettered"
    if RE_TABLE_ROW.search(stripped) or (
        RE_PERCENTAGE.search(stripped) and len(stripped) < 80
    ):
        return "table_row"
    return "text"

@dataclass
class Block:

    block_type: str
    lines: List[str] = field(default_factory=list)
    heading_stack: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()
    
def assemble_blocks(full_text: str) -> List[Block]:
    lines = full_text.splitlines()
    blocks: List[Block] = []
    heading_stack: List[str] = []
    current_block = Block | None = None
    table_buffer: List[str] = []

    def flush_table():
        nonlocal table_buffer
        if table_buffer:
            b = Block(block_type = "table",
                      lines = list(table_buffer),
                      heading_stack = list(heading_stack))
            blocks.append(b)
            table_buffer = []
    def flush_current():
        nonlocal current_block
        if current_block and current_block.lines:
            blocks.append(current_block)
        current_block = None

    for line in lines:
        label = classify_line(line)
        stripped = line.strip()

        if label == "table_row":
            flush_current()
            table_buffer.append(stripped)
            continue
        else:
            # Non-table line → flush any buffered table rows
            if table_buffer:
                flush_table()

        if label == "blank":
            if current_block and current_block.block_type in ("numbered_item",):
                flush_current()
            continue

        if label == "section":
            flush_current()
            heading_stack = [stripped]
            b = Block(block_type="section",
                      lines=[stripped],
                      heading_stack=list(heading_stack))
            blocks.append(b)
            continue

        if label == "heading":
            flush_current()
            heading_stack = [stripped]
            b = Block(block_type="heading",
                      lines=[stripped],
                      heading_stack=list(heading_stack))
            blocks.append(b)
            continue

        if label == "numbered":
            flush_current()
            heading_stack = heading_stack[:1] + [stripped]
            current_block = Block(block_type="numbered_item",
                                  lines=[stripped],
                                  heading_stack=list(heading_stack))
            continue

        # ---- ROMAN NUMERAL SUB-ITEMS (i. ii. iii.) ------------------------
        if label == "roman":
            flush_current()
            b = Block(block_type="list_group",
                      lines=[stripped],
                      heading_stack=list(heading_stack))
            blocks.append(b)
            continue

        # ---- LETTERED SUB-ITEMS (a. b. c.) --------------------------------
        if label == "lettered":
            flush_current()
            b = Block(block_type="list_group",
                      lines=[stripped],
                      heading_stack=list(heading_stack))
            blocks.append(b)
            continue

        if current_block and current_block.block_type == "prose":
            current_block.lines.append(stripped)
        else:
            flush_current()
            current_block = Block(block_type="prose",
                                  lines=[stripped],
                                  heading_stack=list(heading_stack))

    # Flush anything remaining
    flush_current()
    flush_table()

    return [b for b in blocks if b.text]


def blocks_to_chunks(blocks: List[Block], 
                     max_chunk_chars: int = 900, 
                     overlap_chars: int = 150) -> List[Chunk]:
    chunks: List[Chunk] = []

    def make_context_prefix(heading_stack: List[str]) -> str:
        return " > ".join(heading_stack) if heading_stack else ""
    
    def split_into_sentences(text: str) -> List[str]:
        # A simple sentence splitter based on punctuation. This can be improved with NLP libraries.
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [p.strip() for p in parts if p.strip()]
    
    for block in blocks:
        prefix = make_context_prefix(block.heading_stack)
        prefix_text = f"[Context: {prefix}]\n" if prefix else ""

        if block.block_type == "table":
            chunk_text = prefix_text + block.text
            chunks.append(Chunk(
                text=chunk_text,
                metadata={
                    "type": "table",
                    "section": block.heading_stack[0] if block.heading_stack else "",
                    "context": prefix,
                }
            ))
        elif block.block_type in ("section", "heading"):
            chunks.append(Chunk(
                text=block.text,
                metadata={
                    "type": "heading",
                    "section": block.text,
                    "context": prefix,
                }
            ))
        elif block.block_type in ("list_group", "numbered_item"):
            chunk_text = prefix_text + block.text
            chunks.append(Chunk(
                text=chunk_text,
                metadata={
                    "type": "list_item",
                    "section": block.heading_stack[0] if block.heading_stack else "",
                    "context": prefix,
                }
            ))

        # ----------------------------------------------------------------
        # PROSE — sentence-boundary splitting with overlap
        # ----------------------------------------------------------------
        else:
            full_prose = prefix_text + block.text
            if len(full_prose) <= max_chunk_chars:
                chunks.append(Chunk(
                    text=full_prose,
                    metadata={
                        "type": "prose",
                        "section": block.heading_stack[0] if block.heading_stack else "",
                        "context": prefix,
                    }
                ))
            else:
                # Split at sentence boundaries
                sentences = split_into_sentences(block.text)
                current_sentences: List[str] = []
                current_len = len(prefix_text)
                overlap_tail = ""  # tail of previous chunk for continuity

                for sentence in sentences:
                    sentence_len = len(sentence) + 1  # +1 for space
                    if current_len + sentence_len > max_chunk_chars and current_sentences:
                        # Emit current chunk
                        chunk_body = " ".join(current_sentences)
                        chunk_text = prefix_text + overlap_tail + chunk_body
                        chunks.append(Chunk(
                            text=chunk_text.strip(),
                            metadata={
                                "type": "prose",
                                "section": block.heading_stack[0] if block.heading_stack else "",
                                "context": prefix,
                            }
                        ))
                        # Compute overlap: take the last `overlap_chars` chars
                        # of the chunk body as a prefix for the next chunk
                        overlap_tail = chunk_body[-overlap_chars:] + " " if overlap_chars else ""
                        current_sentences = [sentence]
                        current_len = len(prefix_text) + len(overlap_tail) + sentence_len
                    else:
                        current_sentences.append(sentence)
                        current_len += sentence_len

                # Flush remaining sentences
                if current_sentences:
                    chunk_body = " ".join(current_sentences)
                    chunk_text = prefix_text + overlap_tail + chunk_body
                    chunks.append(Chunk(
                        text=chunk_text.strip(),
                        metadata={
                            "type": "prose",
                            "section": block.heading_stack[0] if block.heading_stack else "",
                            "context": prefix,
                        }
                    ))

    # Assign sequential index
    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i

    return chunks


# ---------------------------------------------------------------------------
# Public API — drop-in replacement for your original chunk_pages()
# ---------------------------------------------------------------------------

def chunk_pages(pages: List[str],
                chunk_size: int = 900,
                chunk_overlap: int = 150) -> List[str]:
    """
    Drop-in replacement for the original chunk_pages().

    Accepts the same arguments for backwards compatibility, but internally
    uses structural chunking instead of fixed-length slicing.

    Returns List[str] so embed_chunks() needs zero changes.
    """
    full_text = clean_pages(pages)
    blocks = assemble_blocks(full_text)
    chunks = blocks_to_chunks(blocks,
                               max_chunk_chars=chunk_size,
                               overlap_chars=chunk_overlap)
    return [c.text for c in chunks]


def chunk_pages_with_metadata(pages: List[str],
                               chunk_size: int = 900,
                               chunk_overlap: int = 150) -> List[Chunk]:
    """
    Extended version that returns Chunk objects with metadata.

    Use this when you want to store metadata in Pinecone alongside vectors,
    which enables filtered retrieval (e.g. only search within SECTION I).

    Usage in ingest.py:
        chunks = chunk_pages_with_metadata(pages)
        texts = [c.text for c in chunks]
        embeddings = embed_chunks(texts)
        store_in_pinecone(chunks, embeddings, namespace="")
    """
    full_text = clean_pages(pages)
    blocks = assemble_blocks(full_text)
    return blocks_to_chunks(blocks,
                             max_chunk_chars=chunk_size,
                             overlap_chars=chunk_overlap)


# ---------------------------------------------------------------------------
# Demo — run this file directly to see chunking output on sample text
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Simulated pypdf output from the insurance PDF in the screenshot
    sample_page_1 = """
Whereas the insured by a proposal and declaration dated as stated in the Schedule which
shall be the basis of this contract and is deemed to be incorporated herein has applied to the
Company for the insurance hereinafter contained and has paid the premium mentioned in the
schedule as consideration for such insurance in respect of accidental loss or damage occurring
during the period of insurance.

NOW THIS POLICY WITNESSETH

That subject to the Terms Exceptions and Conditions contained herein or endorsed or
expressed hereon;

SECTION I. LOSS OF OR DAMAGE TO THE VEHICLE INSURED

1.    The Company will indemnify the insured against loss or damage to the vehicle insured
hereunder and / or its accessories whilst thereon

    i.    By fire explosion self-ignition or lightning ;
    ii.   By burglary housebreaking or theft ;
    iii.  By riot and strike;
    iv.   By earthquake (fire and shock damage);
    v.    By flood typhoon hurricane storm tempest inundation cyclone hailstorm frost;
    vi.   By accidental external means;
    vii.  By malicious act;
    viii. By terrorist activity;
    ix.   Whilst in transit by road rail inland-waterway lift elevator or air;
    x.    By landslide rockslide.

Subject to a deduction for depreciation at the rates mentioned below in respect of parts replaced:
    a.    For all rubber/ nylon / plastic parts, tyres and tubes, batteries and air bags  -  50%
    b.    For fibre glass components  -  30%
    c.    For all parts made of glass  -  Nil

1
"""
    sample_page_2 = """
    d.    Rate of depreciation for all other parts including wooden parts will be as per the
following schedule.

AGE OF VEHICLE            % OF DEPRECIATION
Not exceeding 6 months                  Nil
Exceeding 6 months but not exceeding 1 year    5%
Exceeding 1 year but not exceeding 2 years     10%
Exceeding 2 years but not exceeding 3 years    15%
Exceeding 3 years but not exceeding 4 years    25%
Exceeding 4 years but not exceeding 5 years    35%
Exceeding 5 years but not exceeding 10 years   40%
Exceeding 10 years                      50%

    e.    Rate of Depreciation for Painting: In the case of painting, the depreciation rate of 50%
shall be applied only on the material cost of total painting charges.
"""

    print("=" * 70)
    print("STRUCTURAL CHUNKING DEMO")
    print("=" * 70)

    chunks = chunk_pages_with_metadata(
        [sample_page_1, sample_page_2],
        chunk_size=900,
        chunk_overlap=150
    )

    for i, chunk in enumerate(chunks):
        print(f"\n{'─'*70}")
        print(f"CHUNK {i+1} | type={chunk.metadata.get('type')} | "
              f"chars={len(chunk.text)}")
        print(f"{'─'*70}")
        print(chunk.text)

    print(f"\n\nTotal chunks produced: {len(chunks)}")
    print("\nComparison: fixed-length would produce "
          f"~{len(sample_page_1 + sample_page_2) // 900 + 1} chunks "
          "with no structural awareness.")

