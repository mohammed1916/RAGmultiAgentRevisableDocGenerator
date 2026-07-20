# Schemas

This directory contains database schema definitions.

## schema.json

**Purpose:** Milvus database schema definition

**Used By:** `server/tools/generation/document_chunker.py`

**What it is:** Defines the structure of the Milvus collection used to store document chunks.

**Contains:** 
- Collection name
- Field definitions
- Data types
- Index configuration

**When it's used:**
- During database initialization
- When loading documents into Milvus
- By document_chunker.py to understand chunk structure

**Example:**
```json
{
  "collection_name": "documents",
  "fields": [
    {
      "name": "id",
      "type": "int64",
      "is_primary": true
    },
    {
      "name": "content",
      "type": "varchar",
      "max_length": 65535
    },
    {
      "name": "embedding",
      "type": "float_vector",
      "dim": 768
    }
  ]
}
```

**Related Files:**
- `docs/guides/MILVUS_SETUP.md` - How to set up Milvus
- `server/tools/rag.py` - RAG implementation that uses this schema

**Do NOT edit** unless you're changing the Milvus schema structure.
