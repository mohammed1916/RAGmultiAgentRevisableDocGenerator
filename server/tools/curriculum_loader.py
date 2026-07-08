"""Load curriculum data into Milvus."""

import json
from pathlib import Path
from typing import List, Dict, Any
from .milvus_rag import MilvusRAG
from ..logger import setup_logger

logger = setup_logger(__name__)


def load_curriculum_data(data_file: str = None) -> MilvusRAG:
    """Load curriculum data from JSON file into Milvus.

    Args:
        data_file: Path to curriculum JSON file

    Returns:
        Initialized MilvusRAG with loaded data
    """
    if data_file is None:
        data_file = Path(__file__).parent.parent / "data" / "curriculum_data.json"

    logger.info(f"Loading curriculum data from {data_file}")

    # Initialize Milvus RAG
    rag = MilvusRAG(host="localhost", port=19530)

    # Load JSON data
    with open(data_file, "r") as f:
        documents = json.load(f)

    # Add each document to Milvus
    for doc in documents:
        rag.add_document(
            doc_id=doc["id"],
            content=doc["content"],
            doc_type=doc["document_type"],
            metadata=doc.get("metadata", {}),
        )
        logger.info(f"Added: {doc['id']}")

    logger.info(f"Loaded {len(documents)} curriculum documents into Milvus")
    return rag


def search_curriculum(query: str, doc_type: str = None, top_k: int = 5):
    """Search curriculum documents.

    Args:
        query: Search query
        doc_type: Filter by document type (e.g., 'cbse_12_physics')
        top_k: Number of results to return

    Returns:
        List of relevant documents
    """
    rag = MilvusRAG(host="localhost", port=19530)
    results = rag.search(query, doc_type=doc_type, top_k=top_k)

    logger.info(f"Search '{query}' returned {len(results)} results")
    return results


if __name__ == "__main__":
    # Load data
    rag = load_curriculum_data()

    # Example searches
    print("\n" + "=" * 80)
    print("EXAMPLE: Search for Electrostatics")
    print("=" * 80)
    results = rag.search("Electric field potential capacitor", top_k=3)
    for r in results:
        print(f"\n📄 {r['doc_id']}")
        print(f"   Type: {r['document_type']}")
        print(f"   Score: {r['relevance_score']:.2f}")
        print(f"   Content: {r['content'][:150]}...")

    print("\n" + "=" * 80)
    print("EXAMPLE: Search for JEE Maths")
    print("=" * 80)
    results = rag.search("quadratic equations derivatives integrals", doc_type="jee_mains_maths", top_k=3)
    for r in results:
        print(f"\n📄 {r['doc_id']}")
        print(f"   Type: {r['document_type']}")
        print(f"   Score: {r['relevance_score']:.2f}")
        print(f"   Content: {r['content'][:150]}...")

    print("\n" + "=" * 80)
    print(f"Total documents: {rag.get_stats()['total_documents']}")
    print("=" * 80)

    rag.close()
