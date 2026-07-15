#!/usr/bin/env python
"""Generate evaluation benchmark directly from curriculum chunks.

Instead of manual 100-query benchmark, this:
1. Reads curriculum chunks from server/data/chunks/
2. Extracts topics from chunk content
3. Generates questions using Claude
4. Creates benchmark where ground_truth = chunk_id

This ensures evaluation is tied to actual curriculum.
"""

import sys
import json
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.llm.ollama_client import OllamaClient
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def extract_topics_from_content(content: str, max_topics: int = 3) -> list[str]:
    """Extract key topics/concepts from chunk content."""
    topics = []

    # Pattern 1: Chapter headings (e.g., "Chapter–1: Units and Measurements")
    chapter_matches = re.findall(r"Chapter[–-]\d+:\s*([^.\n]+)", content)
    topics.extend(chapter_matches[:max_topics])

    # Pattern 2: Section headings (e.g., "Unit I: Physical World")
    unit_matches = re.findall(r"Unit[–\s-]*[IVX]+:\s*([^.\n]+)", content)
    topics.extend(unit_matches[:max_topics])

    # Pattern 3: Bold/emphasized concepts (e.g., "Coulomb's law", "photoelectric effect")
    # Look for capitalized phrases
    concept_matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[a-z]+)*(?:\s*[''][s])?)\b", content)
    topics.extend(concept_matches[:max_topics])

    # Remove duplicates while preserving order
    seen = set()
    unique_topics = []
    for t in topics:
        if t not in seen and len(t) > 3:
            seen.add(t)
            unique_topics.append(t)

    return unique_topics[:max_topics]


def generate_questions_from_chunk(chunk_id: str, content: str, topics: list[str], llm_client) -> list[str]:
    """Generate 1-3 questions from chunk using Claude."""
    if not topics:
        return []

    topic_str = ", ".join(topics[:2])
    prompt = f"""Given this curriculum topic: {topic_str}

From this content: {content[:500]}...

Generate 1-3 clear, factual questions a student might ask about this topic.
Questions should:
- Be specific to the topic
- Be answerable from the provided content
- Range from easy to moderate difficulty
- NOT be trick questions

Format: Return ONLY the questions, one per line, no numbering."""

    try:
        response = llm_client.call(prompt)
        questions = [q.strip() for q in response.split("\n") if q.strip() and len(q) > 10]
        return questions[:3]
    except Exception as e:
        logger.error(f"Error generating questions for {chunk_id}: {e}")
        return []


def load_curriculum_chunks() -> dict:
    """Load all curriculum chunks from server/data/chunks/."""
    chunks_dir = Path(__file__).parent.parent.parent / "server" / "data" / "chunks"
    all_chunks = {}

    for json_file in sorted(chunks_dir.glob("*.json")):
        try:
            with open(json_file, encoding='utf-8') as f:
                chunks = json.load(f)
                for chunk in chunks:
                    chunk_id = chunk.get("id", "")
                    if chunk_id:
                        all_chunks[chunk_id] = chunk
        except Exception as e:
            logger.error(f"Error loading {json_file}: {e}")

    return all_chunks


def generate_curriculum_benchmark(output_csv: Path = None, max_questions: int = 200):
    """Generate benchmark from curriculum chunks."""

    print("="*70)
    print("CURRICULUM-GROUNDED BENCHMARK GENERATION")
    print("="*70)

    if output_csv is None:
        output_csv = Path(__file__).parent.parent / "benchmarks" / "curriculum_generated.csv"

    # Load chunks
    print(f"\nLoading curriculum chunks...")
    chunks = load_curriculum_chunks()
    print(f"Loaded {len(chunks)} chunks")

    # Initialize LLM for question generation
    print("Initializing LLM client...")
    llm = OllamaClient()

    # Generate questions
    print(f"\nGenerating questions (max {max_questions})...")
    benchmark_queries = []
    chunk_count = 0
    question_count = 0

    for chunk_id, chunk in sorted(chunks.items())[:max_questions]:
        if question_count >= max_questions:
            break

        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})

        if len(content) < 100:  # Skip very short chunks
            continue

        chunk_count += 1
        progress = f"[{chunk_count}/~{min(max_questions, len(chunks))}]"

        # Extract topics
        topics = extract_topics_from_content(content)
        if not topics:
            print(f"{progress} {chunk_id}: No topics extracted, skipping")
            continue

        # Generate questions
        questions = generate_questions_from_chunk(chunk_id, content, topics, llm)
        if not questions:
            print(f"{progress} {chunk_id}: No questions generated")
            continue

        # Create benchmark entries
        for q_idx, question_text in enumerate(questions, 1):
            if question_count >= max_questions:
                break

            benchmark_queries.append({
                "query_id": f"{chunk_id}_Q{q_idx}",
                "subject": metadata.get("subject", "Unknown"),
                "class": metadata.get("class", "Unknown"),
                "chapter": metadata.get("document", ""),
                "query_text": question_text,
                "ground_truth_answer": content[:200],  # First 200 chars as reference
                "query_category": "curriculum-generated",
                "difficulty": "Medium",  # Default; could infer from content length
                "expected_chunks": chunk_id,  # The chunk itself is the ground truth
                "source_chunk_id": chunk_id
            })
            question_count += 1

        topic_list = ", ".join(topics[:2])
        print(f"{progress} {chunk_id}: Generated {len(questions)} questions ({topic_list})")

    # Write benchmark
    print(f"\n{'='*70}")
    print(f"Generated {question_count} questions from {chunk_count} curriculum chunks")
    print(f"Writing to: {output_csv}")
    print(f"{'='*70}")

    # Write CSV
    import csv
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(benchmark_queries[0].keys()) if benchmark_queries else []

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(benchmark_queries)

    print(f"\n✓ Benchmark saved to: {output_csv}")
    print(f"✓ Total queries: {question_count}")
    print(f"✓ Ready to evaluate: python -m evaluation.scripts.run_retrieval_eval")

    return output_csv, benchmark_queries


if __name__ == "__main__":
    generate_curriculum_benchmark()
