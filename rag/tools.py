"""Tools for questions *about* the corpus rather than answerable *from* it.

"Which policies are expired?" and "what does the Pets Policy cover?" cannot be
answered by retrieval: the first is a fact about the collection, the second about
a document's structure. Both are plain lookups over metadata already in memory --
no embedding call, no Pinecone query, no LLM.
"""

from langchain_core.tools import tool

from rag.retriever import KBRetriever

MAX_TOOL_CALLS = 3


def make_tools(retriever: KBRetriever) -> list:
    """Bind the tools to a retriever instance."""

    @tool
    def list_policies(audience: str | None = None, status: str | None = None) -> dict:
        """List the policies in the knowledge base.

        Use for questions about the collection itself: which policies exist, how
        many there are, which are expired or past review. Filter by audience
        ('staff', 'tenant', 'reference') or status ('current', 'expired',
        'unknown').

        Returns a 'count' and a 'policies' list. Always quote 'count' directly
        for "how many" questions.
        """
        rows = retriever.policies()
        if audience:
            rows = [r for r in rows if r["audience"] == audience]
        if status:
            rows = [r for r in rows if r["status"] == status]

        # The count is returned explicitly because the model gets it wrong
        # otherwise: asked "how many policies are there", it called this tool,
        # received all 36 rows, and answered 39. A lookup tool that makes the
        # model count its own output is not a lookup tool.
        return {
            "count": len(rows),
            "policies": [
                {
                    "doc_id": r["doc_id"],
                    "title": r["title"],
                    "status": r["status"],
                    "version": r["version"],
                    "expiry": r["expiry"],
                }
                for r in rows
            ],
        }

    @tool
    def policy_sections(doc_id: str) -> dict:
        """List the section headings of one policy.

        Use when asked what a named policy covers, or to find the right section
        before searching it. Pass a doc_id from list_policies, e.g. 'pets-policy'.
        """
        sections: list[str] = []
        found = False
        for doc in retriever.docs:
            if doc.metadata["doc_id"] != doc_id:
                continue
            found = True
            # heading_path is "Title > Section > Subsection"; drop the title.
            path = doc.metadata["heading_path"]
            section = path.split(" > ", 1)[1] if " > " in path else None
            if section and section not in sections:
                sections.append(section)

        # "no such policy" and "that policy has no headings" are different
        # answers, and reporting the second as the first sends the model
        # looking for a doc_id that was right all along.
        if not found:
            return {"error": f"No policy with doc_id {doc_id!r}. Call list_policies first."}
        return {"doc_id": doc_id, "sections": sections}

    @tool
    def search_policies(query: str, doc_id: str | None = None) -> list[dict]:
        """Search the text of the policies.

        This is the tool for questions answered by policy content. Set doc_id to
        restrict the search to one named policy.
        """
        hits = retriever.search(query, doc_id=doc_id)
        return [
            {
                "source_file": doc.metadata["source_file"],
                "page": doc.metadata["page"],
                "section": doc.metadata["heading_path"],
                "status": doc.metadata["status"],
                "text": doc.page_content,
            }
            for doc, _score in hits
        ]

    return [list_policies, policy_sections, search_policies]
