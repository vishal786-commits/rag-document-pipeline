"""The corpus tools are pure lookups -- no LLM, no embedding, no network."""

from langchain_core.documents import Document

from rag.tools import make_tools


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.searches: list[dict] = []

    def policies(self):
        seen = {}
        for d in self.docs:
            m = d.metadata
            seen.setdefault(
                m["doc_id"],
                {
                    "doc_id": m["doc_id"],
                    "title": m["title"],
                    "audience": m["audience"],
                    "status": m["status"],
                    "version": m["version"],
                    "expiry": m.get("expiry"),
                },
            )
        return sorted(seen.values(), key=lambda r: r["title"])

    def search(self, query, **kwargs):
        self.searches.append({"query": query, **kwargs})
        return [(self.docs[0], 0.9)]


def doc(doc_id, title, section, **meta):
    base = {
        "id": f"{doc_id}#0",
        "doc_id": doc_id,
        "title": title,
        "source_file": f"{title}.pdf",
        "page": 1,
        "heading_path": f"{title} > {section}" if section else title,
        "audience": "staff",
        "status": "current",
        "version": "1.0",
        "expiry": "2027-01-01",
    }
    base.update(meta)
    return Document(page_content="text", metadata=base)


DOCS = [
    doc("pets-policy", "Pets Policy", "1 Scope"),
    doc("pets-policy", "Pets Policy", "2 Policy Statement"),
    doc("pets-policy", "Pets Policy", "2 Policy Statement"),  # repeated section
    doc("fire-safety-policy", "Fire Safety Policy", "1 Scope",
        status="expired", expiry="2026-05-31"),
    doc("decent-home", "A Decent Home", None, audience="reference"),
]


def tools():
    retriever = FakeRetriever(DOCS)
    return {t.name: t for t in make_tools(retriever)}, retriever


# ── list_policies ───────────────────────────────────────────────────────────
def test_list_policies_returns_every_document():
    t, _ = tools()
    result = t["list_policies"].invoke({})

    assert result["count"] == 3
    assert len(result["policies"]) == 3


def test_list_policies_returns_the_count_explicitly():
    """Asked 'how many policies are there', the model received all 36 rows and
    answered 39. The count must not be something it has to work out."""
    t, _ = tools()
    result = t["list_policies"].invoke({})

    assert result["count"] == len(result["policies"])


def test_list_policies_filters_by_status():
    """This is the question retrieval cannot answer: 'which are expired?'"""
    t, _ = tools()
    expired = t["list_policies"].invoke({"status": "expired"})

    assert expired["count"] == 1
    assert expired["policies"][0]["title"] == "Fire Safety Policy"
    assert expired["policies"][0]["expiry"] == "2026-05-31"


def test_list_policies_filters_by_audience():
    t, _ = tools()
    assert t["list_policies"].invoke({"audience": "reference"})["count"] == 1


# ── policy_sections ─────────────────────────────────────────────────────────
def test_policy_sections_lists_headings_without_the_title_and_without_repeats():
    t, _ = tools()
    result = t["policy_sections"].invoke({"doc_id": "pets-policy"})

    assert result["sections"] == ["1 Scope", "2 Policy Statement"]


def test_policy_sections_reports_an_unknown_doc_id_instead_of_returning_nothing():
    t, _ = tools()
    result = t["policy_sections"].invoke({"doc_id": "not-a-policy"})

    assert "error" in result
    assert "list_policies" in result["error"]


def test_policy_sections_handles_a_document_with_no_sections():
    t, _ = tools()
    assert t["policy_sections"].invoke({"doc_id": "decent-home"})["sections"] == []


# ── search_policies ─────────────────────────────────────────────────────────
def test_search_policies_returns_citable_fields():
    t, _ = tools()
    results = t["search_policies"].invoke({"query": "pets"})

    assert results[0]["source_file"] == "Pets Policy.pdf"
    assert results[0]["page"] == 1
    assert "text" in results[0]


def test_search_policies_scopes_to_one_document_when_asked():
    t, retriever = tools()
    t["search_policies"].invoke({"query": "noise", "doc_id": "pets-policy"})

    assert retriever.searches[0]["doc_id"] == "pets-policy"
