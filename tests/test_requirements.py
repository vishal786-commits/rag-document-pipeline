"""Every third-party import must be declared in a requirements file.

langgraph was imported by rag/graph.py for two commits without ever being added
to requirements.txt. Local runs passed because the venv had it; a clean
environment could not import the graph at all. A test is the only thing that
catches that, because the developer machine is exactly where it is invisible.
"""

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STDLIB = set(sys.stdlib_module_names)
FIRST_PARTY = {"rag", "eval", "main", "frontend", "tests", "conftest"}

# Import name -> distribution name, where they differ.
DISTRIBUTION = {
    "dotenv": "python-dotenv",
    "langchain_core": "langchain-core",
    "langchain_openai": "langchain-openai",
    "langchain_text_splitters": "langchain-text-splitters",
    "langchain_pinecone": "langchain-pinecone",
    "rank_bm25": "rank-bm25",
}

SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git"}


def source_files() -> list[Path]:
    return [
        p
        for p in ROOT.rglob("*.py")
        if not SKIP_DIRS & set(p.parts)
    ]


def third_party_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        else:
            continue
        modules.update(n for n in names if n not in STDLIB and n not in FIRST_PARTY)
    return modules


@pytest.fixture(scope="module")
def declared() -> str:
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    return runtime + dev


def test_every_import_is_declared(declared):
    undeclared = {}
    for path in source_files():
        for module in third_party_imports(path):
            dist = DISTRIBUTION.get(module, module).lower()
            if dist not in declared:
                undeclared.setdefault(dist, []).append(path.relative_to(ROOT).as_posix())

    assert not undeclared, (
        "third-party imports missing from requirements: "
        + "; ".join(f"{dist} (in {', '.join(files)})" for dist, files in undeclared.items())
    )


def test_runtime_requirements_are_pinned_exactly():
    """A working build that breaks three weeks later is almost always this."""
    unpinned = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line and "==" not in line:
            unpinned.append(line)

    assert not unpinned, f"unpinned runtime dependencies: {unpinned}"


def test_the_graph_imports_in_isolation():
    """The specific failure: rag.graph could not be imported at all."""
    import rag.graph  # noqa: F401
