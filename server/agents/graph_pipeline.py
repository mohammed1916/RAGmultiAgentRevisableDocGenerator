"""Multi-agent knowledge-graph pipeline over ingested corpus data.

Three cooperating LLM agents turn a profile's ingested Milvus chunks into a
prerequisite knowledge graph:

1. ConceptExtractorAgent - reads sampled chunks and extracts the distinct
   concepts/topics actually present in the material.
2. PrerequisiteMapperAgent - orders those concepts into prerequisite edges.
3. GraphCriticAgent - validates the edges (removes cycles, dangling ids,
   duplicates, and self-loops) and returns a clean graph.

There is no fabricated fallback: if the LLM is unavailable or returns nothing
usable, the pipeline raises so the caller can surface a real error.
"""

import json
from typing import Any, Dict, List, Optional

from ..base.exceptions import AgentException
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class GraphPipelineException(AgentException):
    """Raised when the multi-agent graph pipeline cannot produce a graph."""


def _extract_json(text: str) -> Dict[str, Any]:
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= 0:
        raise GraphPipelineException("No JSON object in LLM response")
    return json.loads(text[start:end])


def _node_id(label: str) -> str:
    return "-".join(str(label).lower().split())[:64]


class ConceptExtractorAgent:
    SYSTEM_PROMPT = (
        "You are a curriculum analyst. From the study material excerpts, extract the "
        "distinct concepts/topics that a learner must understand. "
        'Return ONLY JSON: {"concepts": [{"label": "<concept>", "subject": "<subject or null>"}]}. '
        "Merge duplicates, keep concepts concise (2-4 words), and return at most 18."
    )

    def __init__(self, llm):
        self.llm = llm

    def run(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Sample chunk text to keep the prompt bounded.
        excerpts = []
        for chunk in chunks[:40]:
            content = (chunk.get("content") or "").strip().replace("\n", " ")
            if content:
                subj = chunk.get("subject") or ""
                excerpts.append(f"[{subj}] {content[:400]}")
        if not excerpts:
            return []
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": "Material excerpts:\n" + "\n---\n".join(excerpts) + "\n\nReturn the concepts JSON now."},
        ]
        result = self.llm.chat(messages)
        parsed = _extract_json(result.get("message", {}).get("content", ""))
        concepts, seen = [], set()
        for item in parsed.get("concepts", []):
            label = (item.get("label") or "").strip()
            if not label:
                continue
            node_id = _node_id(label)
            if node_id in seen:
                continue
            seen.add(node_id)
            concepts.append({"id": node_id, "label": label, "kind": "concept", "subject": item.get("subject"), "progress": 0.0})
        logger.info("ConceptExtractor: %d concepts", len(concepts))
        return concepts


class PrerequisiteMapperAgent:
    SYSTEM_PROMPT = (
        "You are a curriculum sequencing expert. Given a list of concept ids/labels, "
        "produce prerequisite edges: which concept should be learned before another. "
        'Return ONLY JSON: {"edges": [{"source": "<id>", "target": "<id>", "label": "requires"}]}. '
        "'source' is the prerequisite. Use only the provided ids. Keep edges minimal and acyclic."
    )

    def __init__(self, llm):
        self.llm = llm

    def run(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(concepts) < 2:
            return []
        summary = "\n".join(f'- id="{c["id"]}" label="{c["label"]}"' for c in concepts)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Concepts:\n{summary}\n\nReturn the prerequisite edges JSON now."},
        ]
        result = self.llm.chat(messages)
        parsed = _extract_json(result.get("message", {}).get("content", ""))
        valid = {c["id"] for c in concepts}
        edges = [
            {"source": e["source"], "target": e["target"], "label": e.get("label", "requires")}
            for e in parsed.get("edges", [])
            if e.get("source") in valid and e.get("target") in valid and e.get("source") != e.get("target")
        ]
        logger.info("PrerequisiteMapper: %d edges", len(edges))
        return edges


class GraphCriticAgent:
    """Deterministic validator: drop self-loops, duplicates, and break cycles."""

    def run(self, concepts: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid = {c["id"] for c in concepts}
        seen, cleaned = set(), []
        adjacency: Dict[str, set] = {c["id"]: set() for c in concepts}

        def creates_cycle(src, dst):
            # Would adding src->dst make dst reach src? (DFS over existing edges)
            stack, visited = [dst], set()
            while stack:
                node = stack.pop()
                if node == src:
                    return True
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(adjacency.get(node, ()))
            return False

        for edge in edges:
            src, dst = edge["source"], edge["target"]
            key = (src, dst)
            if src not in valid or dst not in valid or src == dst or key in seen:
                continue
            if creates_cycle(src, dst):
                continue
            seen.add(key)
            adjacency[src].add(dst)
            cleaned.append(edge)
        logger.info("GraphCritic: kept %d/%d edges", len(cleaned), len(edges))
        return {"nodes": concepts, "edges": cleaned}


class GraphPipeline:
    """Orchestrates ConceptExtractor -> PrerequisiteMapper -> GraphCritic."""

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        self.llm = llm_client
        self.extractor = ConceptExtractorAgent(llm_client)
        self.mapper = PrerequisiteMapperAgent(llm_client)
        self.critic = GraphCriticAgent()

    def build_from_corpus(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.llm is None:
            raise GraphPipelineException("No LLM client configured for graph pipeline")
        if not chunks:
            return {"nodes": [], "edges": []}
        try:
            concepts = self.extractor.run(chunks)
            if not concepts:
                return {"nodes": [], "edges": []}
            edges = self.mapper.run(concepts)
            return self.critic.run(concepts, edges)
        except GraphPipelineException:
            raise
        except Exception as error:
            raise GraphPipelineException(f"Graph pipeline failed: {error}") from error
