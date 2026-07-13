# Milvus Chunk Viewer Guide

## Overview

`view_chunks.py` is a CLI tool to search, view, and manage chunks stored in your Milvus RAG database.

**Current Status**: ✓ Milvus connected, 0 chunks stored

---

## Commands

### 1. View Statistics
```bash
python scripts/view_chunks.py --stats
```

Shows:
- Milvus mode (MILVUS or MOCK)
- Total chunks stored
- Index status
- Collection name

**Example Output**:
```
Mode: MILVUS
Total Chunks: 0
Indexed: [OK]
Collection: documents
```

### 2. List All Chunks
```bash
python scripts/view_chunks.py --all
```

Shows all chunks in a table format with:
- Chunk ID
- Document Type
- Content Preview (first 60 chars)
- Topic

Add `-v` for full content:
```bash
python scripts/view_chunks.py --all -v
```

### 3. Search Chunks
```bash
python scripts/view_chunks.py --search "electric field"
```

Searches chunks by keywords. Returns top matches with:
- Chunk ID
- Relevance score (0-1)
- Full content

Customize number of results:
```bash
python scripts/view_chunks.py --search "coulomb" --top-k 10
```

**Example**: Search for physics concepts
```bash
python scripts/view_chunks.py --search "electrostatics"
python scripts/view_chunks.py --search "capacitance" --top-k 3
python scripts/view_chunks.py --search "electric field" --top-k 5
```

### 4. Filter by Document Type
```bash
python scripts/view_chunks.py --type jee_math
```

Shows only chunks of a specific document type.

**Example types**:
```bash
python scripts/view_chunks.py --type jee_physics
python scripts/view_chunks.py --type cbse_science
python scripts/view_chunks.py --type python_programming
```

### 5. Get Specific Chunk
```bash
python scripts/view_chunks.py --id jee_001
```

Shows full details of a specific chunk:
- Chunk ID
- Document Type
- Metadata
- Full Content

---

## Common Workflows

### Workflow 1: Check System Status
```bash
python scripts/view_chunks.py --stats
```

Response: How many chunks are stored and is Milvus indexed?

### Workflow 2: Verify Curriculum Data Loaded
After running `python load_curriculum.py`, check:
```bash
python scripts/view_chunks.py --stats
```

Should show: `Total Chunks: [number > 0]`

### Workflow 3: Search for Specific Topic
```bash
python scripts/view_chunks.py --search "Coulomb's law"
```

Shows relevant curriculum chunks for that topic.

### Workflow 4: Verify Search Quality
```bash
python scripts/view_chunks.py --search "electric field" --top-k 5
```

Check:
1. Are results relevant?
2. Are relevance scores high (>0.7)?
3. Is content useful for RAG?

### Workflow 5: Debug RAG Retrieval
Before running quality tests, verify retrieval works:
```bash
python scripts/view_chunks.py --search "electrostatics"
python scripts/view_chunks.py --search "point charges"
python scripts/view_chunks.py --search "Gauss's law"
```

If no results → curriculum may not be loaded or indexed properly.

### Workflow 6: Inspect Full Chunk Content
When you find relevant chunks via search, view full details:
```bash
python scripts/view_chunks.py --search "capacitance" --top-k 1
# Find the chunk ID from results, then:
python scripts/view_chunks.py --id [chunk_id]
```

---

## Output Formats

### Search Result Example
```
[SEARCH RESULTS: 'electrostatics']
[OK] Found 3 matching chunks

Chunk ID     | Type                      | Content Preview          | Topic
─────────────┼───────────────────────────┼──────────────────────────┼────────
elec_001     | jee_physics_fundamentals  | Electrostatics is...     | Physics
elec_002     | jee_physics_chapter_3     | Electric field defin...  | Physics
elec_003     | cbse_physics_class_12     | Coulomb's law states...  | Physics

Detailed Results:
1. elec_001 (Score: 0.95)
   Electrostatics is the branch of physics dealing with electric charges...

2. elec_002 (Score: 0.89)
   Electric field is defined as force per unit charge...

3. elec_003 (Score: 0.82)
   Coulomb's law states that the force between two charges...
```

### Statistics Output Example
```
[STORAGE STATISTICS]

Mode: MILVUS
Total Chunks: 847
Indexed: [OK]
Collection: documents
```

---

## Troubleshooting

### Problem: "No chunks found"
**Possible causes**:
1. Curriculum data not loaded yet
2. Search query too specific
3. Chunks not indexed

**Solution**:
```bash
# Check status
python scripts/view_chunks.py --stats

# If 0 chunks, load curriculum
python load_curriculum.py

# Retry search with broader keywords
python scripts/view_chunks.py --search "electric"
```

### Problem: "Low relevance scores" (< 0.5)
**Possible causes**:
1. Search query doesn't match chunk content well
2. Chunks may be poorly formatted
3. Retriever needs tuning

**Solution**:
```bash
# Try different keywords
python scripts/view_chunks.py --search "coulomb force"

# View full chunk content to understand format
python scripts/view_chunks.py --id [chunk_id] 

# Inspect multiple high-scoring results
python scripts/view_chunks.py --search "field" --top-k 10
```

### Problem: "Connection error"
**Possible causes**:
1. Milvus not running
2. Milvus server crashed
3. Wrong connection settings

**Solution**:
```bash
# Check Milvus is running
milvus status

# If not running, start it
milvus start

# Retry
python scripts/view_chunks.py --stats
```

---

## Integration with RAG Quality Testing

### Before Running Quality Tests
```bash
# 1. Check if curriculum loaded
python scripts/view_chunks.py --stats

# 2. Verify search works
python scripts/view_chunks.py --search "electrostatics" --top-k 3

# 3. If no chunks found, load curriculum
python load_curriculum.py

# 4. Run quality tests
python scripts/test_rag_quality.py
```

### After Quality Tests
```bash
# 1. Check chunks related to test prompts
python scripts/view_chunks.py --search "electric field"
python scripts/view_chunks.py --search "Coulomb law"
python scripts/view_chunks.py --search "equipotential"

# 2. Verify relevance scores (should be > 0.7)
# 3. Check if content is being used by retriever
```

---

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `--stats` | Check storage status | `python view_chunks.py --stats` |
| `--all` | List all chunks | `python view_chunks.py --all` |
| `--search QUERY` | Search chunks | `python view_chunks.py --search "field"` |
| `--type TYPE` | Filter by type | `python view_chunks.py --type jee_physics` |
| `--id ID` | Get specific chunk | `python view_chunks.py --id chunk_001` |
| `-v` | Show full content | `python view_chunks.py --all -v` |
| `--top-k N` | Limit search results | `python view_chunks.py --search "law" --top-k 5` |

---

## Next Steps

1. **Load curriculum data**:
   ```bash
   python load_curriculum.py
   ```

2. **Verify it loaded**:
   ```bash
   python scripts/view_chunks.py --stats
   ```

3. **Search for test topics**:
   ```bash
   python scripts/view_chunks.py --search "electrostatics"
   python scripts/view_chunks.py --search "Coulomb"
   python scripts/view_chunks.py --search "electric field"
   ```

4. **Run quality tests**:
   ```bash
   python scripts/test_rag_quality.py
   ```

5. **Analyze results**:
   ```bash
   cat quality_test_results.json
   ```
