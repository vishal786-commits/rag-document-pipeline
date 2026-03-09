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

