# AI Learning Operating System
## 05 - Document Ingestion & Retrieval Pipeline

---

# Overview

The retrieval pipeline is the heart of the Learning Operating System.

Unlike traditional RAG systems that simply chunk a document and perform vector search, this platform continuously maintains an intelligent knowledge base that evolves whenever documents, notes, or user interactions change.

Every uploaded resource becomes searchable, connected, personalized, and continuously updated.

---

# High-Level Pipeline

```
Upload

↓

File Detection

↓

OCR (if required)

↓

Content Extraction

↓

Cleaning & Normalization

↓

Document Structure Analysis

↓

Metadata Extraction

↓

Chunking

↓

Embedding

↓

Vector Database

↓

Knowledge Graph

↓

Search Index

↓

Planner Update

↓

Memory Update

↓

Analytics
```

Every stage should be independently replaceable.

---

# Supported Input Types

The ingestion pipeline should support

## Documents

- PDF
- DOCX
- Markdown
- TXT
- HTML
- EPUB
- PPTX
- XLSX

---

## Images

- PNG
- JPG
- JPEG
- TIFF

Uses OCR when text exists.

---

## Audio

- MP3
- WAV
- AAC

Pipeline

```
Audio

↓

Speech-to-Text

↓

Paragraph Segmentation

↓

Chunking
```

---

## Video

Supported sources

- Uploaded video
- YouTube (future)
- Lecture recordings

Pipeline

```
Video

↓

Frame Extraction

↓

Speech Recognition

↓

Subtitle Alignment

↓

Chunking
```

---

# File Detection

Each uploaded file is classified before processing.

Example

```
report.pdf

↓

PDF Parser

lecture.docx

↓

DOCX Parser

notes.md

↓

Markdown Parser

image.png

↓

OCR Pipeline
```

Parser selection should be automatic.

---

# OCR Layer

OCR is required only when text extraction fails.

Recommended engines

- PaddleOCR
- Tesseract
- EasyOCR
- Azure OCR (optional)

Pipeline

```
Image

↓

OCR

↓

Layout Detection

↓

Reading Order

↓

Structured Text
```

---

# Content Extraction

Extract

- paragraphs
- headings
- tables
- lists
- code blocks
- equations
- images
- captions
- hyperlinks
- references

The goal is to preserve document structure rather than flattening everything into plain text.

---

# Layout Understanding

Each document should preserve

```
Document

├── Title

├── Heading

├── Subheading

├── Paragraph

├── Table

├── Figure

├── Equation

├── Code Block

└── References
```

This improves retrieval quality significantly.

---

# Metadata Extraction

Every document automatically receives metadata.

Example

```json
{
  "user_id":"...",
  "profile_id":"class12",
  "subject":"Physics",
  "chapter":"Electrostatics",
  "source":"NCERT",
  "language":"English",
  "created_at":"...",
  "difficulty":"Medium",
  "tags":[]
}
```

Additional metadata

- author
- upload source
- document type
- page count
- reading time
- keywords
- entities
- concepts
- language
- embeddings version

---

# Document Cleaning

Normalize

- whitespace
- encoding
- Unicode
- punctuation
- repeated headers
- repeated footers
- page numbers
- OCR artifacts

Cleaning should never remove semantic meaning.

---

# Chunking Strategies

The platform should support multiple chunking strategies.

Different document types require different approaches.

---

# Fixed-Length Chunking

Example

```
512 Tokens

↓

512 Tokens

↓

512 Tokens
```

Advantages

- simple
- fast

Disadvantages

- poor semantic boundaries

Use cases

- logs
- transcripts

---

# Recursive Chunking

Split by

```
Document

↓

Heading

↓

Paragraph

↓

Sentence

↓

Tokens
```

Advantages

- preserves structure
- widely used

Recommended for

- textbooks
- documentation

---

# Semantic Chunking

Split based on topic changes.

```
Paragraph

↓

Embedding Similarity

↓

Topic Boundary

↓

Chunk
```

Advantages

- concept preservation
- higher retrieval accuracy

Disadvantages

- slower indexing

---

# Parent-Child Chunking

Store two versions.

Parent

```
Entire Section
```

Child

```
Small Semantic Chunks
```

Retrieval

```
Search Child

↓

Return Parent
```

Advantages

- detailed retrieval
- broader context

---

# Hierarchical Chunking

```
Book

↓

Chapter

↓

Section

↓

Topic

↓

Paragraph
```

Best for

- educational books
- textbooks
- manuals

---

# Sliding Window Chunking

```
Chunk 1

Chunk 2 overlaps

Chunk 3 overlaps
```

Example

```
Tokens

0-500

250-750

500-1000
```

Advantages

- preserves context

Disadvantages

- duplicate embeddings

---

# Contextual Chunking

Chunks include surrounding summaries.

```
Chunk

+

Previous Summary

+

Section Summary
```

Improves LLM understanding.

---

# Agentic Chunking (Future)

LLM decides chunk boundaries.

Example

```
Read Document

↓

Find Concepts

↓

Find Relationships

↓

Generate Semantic Chunks
```

Best quality

Highest cost

---

# Recommended Chunking Strategy

| Content         | Strategy                    |
| --------------- | --------------------------- |
| Textbooks       | Hierarchical + Parent Child |
| PDFs            | Recursive                   |
| Markdown        | Heading-based               |
| Code            | Function/Class based        |
| Research Papers | Semantic                    |
| Lecture Notes   | Recursive                   |
| Conversations   | Sliding Window              |

---

# Chunk Metadata

Each chunk stores

```
Chunk ID

Document ID

Page

Heading

Section

Token Count

Character Count

Embedding ID

Source

Version

Language
```

---

# Embeddings

Supported models

### Cloud

- OpenAI text-embedding-3-small
- OpenAI text-embedding-3-large

Advantages

- excellent multilingual performance
- strong semantic retrieval

---

### Open Source

- BAAI BGE-M3
- BGE-Large
- Jina Embeddings
- E5-Mistral
- Nomic Embed

Recommended

BGE-M3

Advantages

- multilingual
- dense retrieval
- sparse retrieval
- multi-vector support

---

# Embedding Storage

```
Chunk

↓

Embedding

↓

Metadata

↓

Milvus
```

Embeddings never exist without metadata.

---

# Vector Database

Recommended

- Milvus
- Qdrant
- Weaviate

Each profile becomes its own namespace.

```
User

↓

Profile

↓

Collection

↓

Embeddings
```

---

# Hybrid Retrieval

The retrieval engine combines multiple strategies.

```
Question

↓

Metadata Filter

↓

BM25

↓

Vector Search

↓

Merge

↓

Reranker

↓

Context Compression

↓

LLM
```

Advantages

- better precision
- fewer hallucinations
- improved recall

---

# Metadata Filtering

Example

```
WHERE

profile = Class12

subject = Physics

chapter = Electrostatics
```

Metadata filtering happens before vector search.

---

# Sparse Search

BM25 retrieves

- exact keywords
- formulas
- abbreviations
- variable names

Useful for

- CUDA
- FPGA
- mathematics
- programming

---

# Dense Retrieval

Embeddings retrieve

- semantic similarity
- paraphrases
- related concepts

Useful for

- explanations
- concepts
- natural language

---

# Fusion

Results are merged using

- Reciprocal Rank Fusion (RRF)
- Weighted Fusion

Recommended

RRF

Advantages

- robust
- simple
- widely adopted

---

# Reranking

Initial retrieval

Top 50

↓

Reranker

↓

Top 10

↓

LLM

Recommended models

- BGE-Reranker-v2
- Cohere Rerank
- Jina Reranker

Benefits

- significantly higher relevance
- fewer irrelevant chunks

---

# Context Compression

Before reaching the LLM

```
Top Chunks

↓

Remove Duplicates

↓

Merge Similar Sections

↓

Summarize Long Context

↓

Final Prompt
```

Reduces token usage.

---

# Citation Generation

Every retrieved chunk contains

- page number
- heading
- paragraph
- source document

The AI response should reference these citations.

---

# Incremental Indexing

Editing a note should not rebuild the entire index.

Pipeline

```
Document Edited

↓

Detect Changed Region

↓

Re-chunk

↓

Re-embed

↓

Update Vector DB

↓

Update Graph

↓

Update Planner

↓

Update Memory
```

Only modified chunks are updated.

---

# Background Workers

Heavy operations execute asynchronously.

Examples

- OCR
- embeddings
- reranking cache
- graph extraction
- thumbnail generation
- concept extraction

---

# Quality Evaluation

The retrieval pipeline should be continuously evaluated.

Metrics

### Retrieval

- Recall@K
- Precision@K
- MRR
- nDCG
- Hit Rate

---

### Generation

- Faithfulness
- Context Precision
- Context Recall
- Answer Relevance
- Groundedness

Recommended tools

- RAGAS
- DeepEval
- LangSmith (optional)

---

# Event Flow

```
Document Uploaded

↓

Extract Text

↓

Chunk

↓

Embed

↓

Store

↓

Knowledge Graph

↓

Planner

↓

Memory

↓

Analytics

↓

Ready
```

---

# Design Principles

The ingestion pipeline should satisfy

✓ Incremental indexing

✓ Metadata-first retrieval

✓ Hybrid search

✓ Semantic chunking

✓ Profile isolation

✓ Version-aware indexing

✓ Citation support

✓ Background processing

✓ Continuous evaluation

✓ Event-driven synchronization

The objective is not simply to retrieve documents, but to retrieve the **right information, for the right user, in the right learning context**, while keeping the knowledge base continuously synchronized with every edit and interaction.