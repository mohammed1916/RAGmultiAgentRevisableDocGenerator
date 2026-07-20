"""Knowledge graph agent.

Builds a profile's prerequisite knowledge graph from real data instead of a
hardcoded payload:

- **Nodes** come from the chapters/subjects actually present in the profile's
  documents, with a ``progress`` value computed from subject mastery.
- **Edges** (prerequisite relationships) are produced by the LLM reasoning over
  the chapter list.

There is intentionally **no fallback**: if the LLM is unavailable or returns an
unusable result, :meth:`build` raises so the caller can surface a real error
rather than fabricated edges. The service persists successful results so the LLM
is not called on every dashboard load.
"""

import json
from typing import Any, Dict, List, Optional

from ..base.exceptions import AgentException
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class KnowledgeGraphException(AgentException):
    """Raised when the knowledge graph cannot be derived."""


class KnowledgeGraphAgent:
    """Derive a React-Flow-compatible knowledge graph for a learning profile."""

    SYSTEM_PROMPT = (
        "You are a curriculum knowledge-graph expert. Given a list of chapters/concepts "
        "for one subject, identify prerequisite relationships between them: which concept "
        "should be learned before another. "
        "Return ONLY valid JSON in this exact format:\n"
        '{"edges": [{"source": "<id>", "target": "<id>", "label": "requires"}]}\n'
        "Use only the provided node ids. 'source' is the prerequisite, 'target' is the "
        "concept that depends on it. Keep edges minimal and pedagogically sound."
    )

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        """Initialize the agent.

        Args:
            llm_client: An OllamaClient-like object with a ``chat`` method. Optional
                so nodes can still be built (with fallback edges) when no LLM is
                configured.
        """
        self.llm = llm_client

    @staticmethod
    def _node_id(label: str) -> str:
        return "-".join(label.lower().split())

    def build(
        self,
        subjects: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build ``{"nodes": [...], "edges": [...]}`` from real profile data.

        Args:
            subjects: Subject rows with ``name`` and ``mastery`` (0..1).
            documents: Document dicts exposing ``chapter`` and ``subject``.

        Returns:
            A graph payload, or an empty graph if there are no chapters yet.
        """
        mastery_by_subject = {
            (s.get("name") or "").lower(): float(s.get("mastery", 0.0)) for s in subjects
        }

        # Collect unique chapters (nodes) from the profile's documents.
        nodes: List[Dict[str, Any]] = []
        seen_ids = set()
        for doc in documents:
            chapter = doc.get("chapter")
            if not chapter:
                continue
            node_id = self._node_id(chapter)
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            subject = (doc.get("subject") or "").lower()
            nodes.append({
                "id": node_id,
                "label": chapter,
                "kind": "chapter",
                "subject": doc.get("subject"),
                "progress": round(mastery_by_subject.get(subject, 0.0), 2),
            })

        if not nodes:
            return {"nodes": [], "edges": []}

        edges = self._derive_edges(nodes)
        return {"nodes": nodes, "edges": edges}

    def _derive_edges(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ask the LLM for prerequisite edges. No fallback: raise on failure."""
        if len(nodes) < 2:
            # A single chapter has no prerequisite relationships.
            return []
        if self.llm is None:
            raise KnowledgeGraphException("No LLM client configured for knowledge graph derivation")

        node_summary = "\n".join(f'- id="{n["id"]}" label="{n["label"]}"' for n in nodes)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Chapters:\n{node_summary}\n\nReturn the prerequisite edges JSON now."},
        ]
        try:
            result = self.llm.chat(messages)
            text = result.get("message", {}).get("content", "").strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if start == -1 or end <= 0:
                raise KnowledgeGraphException("No JSON object in LLM response")
            parsed = json.loads(text[start:end])
        except KnowledgeGraphException:
            raise
        except Exception as error:
            raise KnowledgeGraphException(f"Knowledge graph edge derivation failed: {error}") from error

        valid_ids = {n["id"] for n in nodes}
        edges = [
            {
                "source": edge["source"],
                "target": edge["target"],
                "label": edge.get("label", "requires"),
            }
            for edge in parsed.get("edges", [])
            if edge.get("source") in valid_ids
            and edge.get("target") in valid_ids
            and edge.get("source") != edge.get("target")
        ]
        logger.info("Knowledge graph: LLM produced %d edges", len(edges))
        return edges
