# Retrieval Pipeline

## 1. Overview

The retrieval pipeline is responsible for finding the most relevant knowledge from the user's personal learning environment.

Unlike traditional RAG systems that perform global similarity search, this platform uses **identity-based retrieval**.

Every retrieval operation is aware of:

- User identity
- Active profile
- Subject
- Learning goal
- Current task
- Knowledge state
- Previous interactions

The retrieval pipeline acts as the intelligence layer between the knowledge base and AI agents.

---

# 2. Retrieval Architecture

```text
User Query
    |
    v
Context Analyzer
    |
    v
Identity Filter
    |
    v
Hybrid Retrieval Engine
    |
    +----------------+
    |                |
    v                v
Vector Search     Keyword Search
(Milvus)          (BM25)
    |                |
    +----------------+
             |
             v
        Reranking
             |
             v
      Context Builder
             |
             v
        AI Agents
```

---

# 3. Identity-Based Retrieval

Every stored object contains metadata.

This applies to:

- Documents
- Notes
- Embeddings
- Flashcards
- Progress records
- AI memories

Example metadata:

```json
{
  "user_id": "abdullah",
  "profile_id": "class12",
  "subject": "physics",
  "chapter": "electrostatics",
  "difficulty": "medium",
  "source": "NCERT",
  "created_at": "2026-07-20"
}
```

---

## 3.1 Metadata Filtering

The system does not search the complete knowledge base.

Retrieval is filtered by user context.

Example:

```text
Retrieve:

WHERE

user_id = Abdullah

AND

profile_id = class12

AND

subject = physics
```

This prevents information from unrelated profiles influencing responses.

---

# 4. Profile-Aware Retrieval

A single user can maintain multiple independent learning environments.

Example:

```text
User
 |
 +-- Class 10 Profile
 |       |
 |       +-- Maths
 |       +-- Science
 |
 +-- Class 12 Profile
 |       |
 |       +-- Physics
 |       +-- Chemistry
 |       +-- Mathematics
 |
 +-- JEE Preparation Profile
         |
         +-- Advanced Problems
```

The active profile determines the retrieval scope.

---

# 5. Retrieval Sources

The retrieval pipeline combines multiple sources of knowledge.

## 5.1 Document Knowledge

Sources:

- NCERT textbooks
- Reference books
- Uploaded PDFs
- Lecture notes
- Markdown documents

## 5.2 Personal Notes

User-generated knowledge:

- Obsidian notes
- AI-generated summaries
- Explanations
- Study notes

## 5.3 Long-Term Memory

Previous interactions become retrievable memory.

Example:

```text
User asked about Ohm's law multiple times.

↓

System identifies weak understanding.

↓

Revision priority increases.
```

## 5.4 Progress Data

Retrieval uses learning analytics:

- Completion percentage
- Accuracy
- Time spent
- Revision history
- Confidence score
- Concept mastery

---

# 6. Hybrid Retrieval System

The retrieval system combines semantic and keyword-based search.

## 6.1 Vector Retrieval

Vector search retrieves information based on meaning.

Example:

Query:

```text
Why does resistance increase with temperature?
```

Can retrieve:

```text
Temperature dependence of resistance
```

even when wording differs.

Recommended systems:

- Milvus
- Qdrant
- Weaviate

---

## 6.2 Keyword Retrieval

Keyword search handles exact matches.

Examples:

- Formula names
- Chapter names
- Definitions
- Specific terms

Technologies:

- BM25
- Elasticsearch
- OpenSearch

---

## 6.3 Combined Retrieval Score

```text
Retrieval Score =

Semantic Similarity

+

Keyword Relevance

+

User Context

+

Learning Priority
```

---

# 7. Reranking Layer

Initial retrieval returns many candidates.

```text
Top 50 retrieved documents

          |
          v

       Reranker

          |
          v

Top 5 most relevant documents
```

Recommended rerankers:

- BGE Reranker
- Cohere Rerank

---

# 8. Context Construction

The context builder prepares information for AI agents.

Final context contains:

```text
Retrieved Documents

+

User Profile

+

Learning History

+

Current Goal

+

Memory
```

---

# 9. Knowledge Graph Assisted Retrieval

The retrieval system uses concept relationships.

Example:

```text
Electrostatics

      |
      v

Capacitance

      |
      v

Current Electricity
```

The system can retrieve prerequisite concepts automatically.

Technologies:

- React Flow
- Cytoscape.js
- Neo4j

---

# 10. Query Understanding

Before retrieval, the query is analyzed.

Extracted information:

```text
Intent:
Concept Explanation

Subject:
Physics

Chapter:
Electrostatics

Difficulty:
Beginner
```

The query analyzer identifies:

- Intent
- Subject
- Topic
- Difficulty
- Required explanation depth

---

# 11. Retrieval Agents

Retrieval functionality is exposed as tools for specialized AI agents.

## Planner Agent

Retrieves:

- Syllabus information
- Progress state
- Remaining tasks
- Available time

## Tutor Agent

Retrieves:

- Textbooks
- Notes
- Examples
- Explanations

## Quiz Agent

Retrieves:

- Previous questions
- Weak concepts
- Practice history

## Revision Agent

Retrieves:

- FSRS schedule
- Memory state
- Revision priority

---

# 12. Embedding Strategy

Documents are converted into vector representations.

Recommended embedding models:

- BAAI BGE-M3
- text-embedding-3-large

Each vector stores:

```text
Embedding Vector

+

Metadata

+

Original Content

+

Source Information
```

---

# 13. Retrieval Storage Architecture

```text
                 Knowledge System

                       |
        +--------------+--------------+

        |                             |

 Vector Database              Graph Database

    Milvus                       Neo4j

        |                             |

 Embeddings                 Concept Relationships


                       |

              Metadata Database

                 PostgreSQL
```

---

# 14. Future Improvements

Potential extensions:

- Adaptive retrieval based on mistakes
- Retrieval confidence scoring
- Automatic query rewriting
- Multi-hop retrieval
- Personalized chunk selection
- Agent-controlled retrieval strategies

---

# 15. Design Goals

The retrieval pipeline should provide:

- Accurate information retrieval
- Profile isolation
- Personalized responses
- Learning-aware context
- Long-term memory integration
- Multi-agent support

The retrieval pipeline transforms traditional RAG into a personalized learning intelligence layer.