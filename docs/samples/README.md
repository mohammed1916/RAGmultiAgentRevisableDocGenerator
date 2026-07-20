# Samples

This directory contains sample/reference data files.

## jee_mathematics.json

**Purpose:** Sample JEE Mathematics curriculum document

**Status:** Reference only - not actively used in code

**Format:** Example of how curriculum documents should be structured

**Contains:** Sample math problems and concepts for JEE exam preparation

**Use Cases:**
- Reference for document format
- Understanding expected data structure
- Testing document chunking logic
- Reviewing sample curriculum data

**Example Structure:**
```json
{
  "document_id": "jee_math_001",
  "subject": "Mathematics",
  "level": "JEE",
  "chapters": [
    {
      "title": "Chapter 1: Vectors",
      "sections": [...]
    }
  ]
}
```

**When to Use:**
- Understanding the expected format for curriculum documents
- Testing RAG system with sample data
- Reference for creating similar documents

**When NOT to Use:**
- For production curriculum loading (use actual curriculum files)
- As reference - the actual format is in `output/documents/` or from `load_curriculum.py`

**Related Files:**
- `docs/guides/GETTING_STARTED.md` - How to load curriculum
- `docs/guides/CHUNK_VIEWER_GUIDE.md` - How to view loaded chunks
- `server/tools/generation/document_chunker.py` - How documents are processed

**To Load Real Curriculum:**
```bash
python load_curriculum.py
```

**To Load This Sample:**
```bash
```

---

## Adding More Samples

If you create sample documents for testing:
1. Save them in this directory
2. Follow the format of `jee_mathematics.json`
3. Document them in this README
4. Update `docs/INDEX.md` if adding new types

**Format Guidelines:**
- Use .json extension
- Follow curriculum document structure
- Include metadata (subject, level, chapter info)
- Add comprehensive comments for clarity
