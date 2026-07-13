# Milvus Collection Analyzer Guide

Production-grade tool for analyzing and validating your RAG collection in Milvus.

## What It Does

The analyzer provides deep insights into your Milvus collection:

- **Collection Statistics** - Total chunks, size distribution, character/token counts
- **Quality Metrics** - Detects empty chunks, duplicates, size anomalies
- **Metadata Analysis** - Document types, topics, custom field distribution
- **Token Estimation** - Rough token counts for budget planning
- **Embedding Analysis** - Vector quality, dimension, norms, nearest neighbors
- **Retrieval Quality** - Test searches with real queries and relevance scores

## Quick Start

### Basic Analysis
```bash
python scripts/analyze_milvus.py
```

Output:
```
======================================================================
MILVUS COLLECTION ANALYSIS
======================================================================

Collection: documents
Total Chunks: 34

Chunk Statistics
  Average Length       : 348.4 chars
  Total Content        : 11844 chars

Estimated Tokens
  Total               : 2961

Quality Report
  Empty Chunks         : 0
  Duplicate Chunks     : 0
  Chunks < 50 chars    : 0
```

### Test Retrieval Quality
```bash
python scripts/analyze_milvus.py --query "electrostatics" --query "derivatives"
```

### Skip Embedding Analysis (faster)
```bash
python scripts/analyze_milvus.py --no-embeddings
```

### Export to JSON
```bash
python scripts/analyze_milvus.py --output analysis.json
```

## Understanding the Report

### Chunk Statistics

| Metric | Meaning |
|--------|---------|
| **Total Chunks** | Number of document chunks in collection |
| **Min/Max/Avg Length** | Character count distribution |
| **Median Length** | 50th percentile chunk size |
| **Total Content** | Sum of all chunk characters |

Use this to understand your data distribution and identify outliers.

### Token Estimation

Rough estimate: **1 token ≈ 4 characters**

- **Average tokens/chunk** - Useful for LLM context planning
- **Total estimated tokens** - Total content volume
- **Min/Max** - Range of chunk complexity

**Note:** Actual token counts depend on tokenizer. Use for budget estimates only.

### Quality Report

| Metric | Issue | Action |
|--------|-------|--------|
| **Empty Chunks** | Chunks with 0 content | Remove or investigate |
| **Duplicate Chunks** | Identical content | Deduplicate or consolidate |
| **Chunks < 50 chars** | Very small chunks | May be noise or extraction errors |
| **Chunks > 1000 chars** | Very large chunks | Consider re-chunking for better retrieval |

A healthy collection has:
- ✅ 0 empty chunks
- ✅ 0 duplicates
- ✅ Few (< 5%) very small chunks
- ✅ Few (< 10%) very large chunks

### Metadata Analysis

Shows the distribution of:
- **Document Types** - How many of each type (jee_math, cbse_physics, etc.)
- **Topics** - Content categorization
- **Other Fields** - Custom metadata

Use to:
- Verify balanced data across types
- Identify missing document categories
- Understand metadata richness

Example:
```
Document Types
  cbse_physics                  12
  jee_maths                     10
  python_course                  8
  ...
```

### Embedding Analysis

| Metric | What It Means |
|--------|---------------|
| **Coverage** | % of chunks with embeddings (ideally 100%) |
| **Dimension** | Vector size (usually 384 or 768) |
| **Avg Norm** | Average vector magnitude (≈1.0 is normal) |
| **Avg NN Distance** | Average distance to nearest neighbor |

- **Coverage < 100%** - Some chunks missing embeddings (regenerate?)
- **Odd dimensions** - Check embedding model configuration
- **High NN distance** - Vectors may be too diverse or scattered

### Retrieval Analysis

Tests search quality with real queries:

```
Query: electrostatics
  Results Found    : 5
  Top Score        : 0.945
  Avg Score        : 0.823
```

- **Results Found** - How many matches (0 = no results)
- **Top Score** - Quality of best match (higher = better)
- **Avg Score** - Average match quality

**Interpretation:**
- `> 0.8` = Excellent match
- `0.5-0.8` = Good match  
- `0.2-0.5` = Partial match
- `< 0.2` = Poor match or irrelevant

Low scores indicate:
- Chunk content not relevant to query
- Poor embedding quality
- Needs better chunking/indexing

## Advanced Usage

### Multiple Test Queries

```bash
python scripts/analyze_milvus.py \
  --query "calculus" \
  --query "matrices" \
  --query "electrostatics" \
  --query "programming"
```

### Performance Tuning

For large collections, skip expensive analyses:

```bash
# Skip embedding analysis (slow for large collections)
python scripts/analyze_milvus.py --no-embeddings

# Quick stats only
python scripts/analyze_milvus.py --no-embeddings --output report.json
```

### Programmatic Usage

Use the analyzer classes in your own scripts:

```python
from server.tools.rag.milvus_rag import MilvusRAG
from server.tools.analyzers import ReportGenerator

rag = MilvusRAG()
generator = ReportGenerator(rag)

# Generate report
report = generator.generate_full_report(
    include_embeddings=True,
    test_queries=["your query here"]
)

# Access individual metrics
chunks = report['chunk_statistics']
print(f"Total: {chunks['total_chunks']}")
print(f"Avg size: {chunks['avg_length']}")

quality = report['quality_report']
print(f"Duplicates: {quality['duplicate_chunks']}")
```

### Modular Analyzers

Use individual analyzers for specific analysis:

```python
from server.tools.analyzers import ChunkAnalyzer, MetadataAnalyzer

chunks = rag.list_all_documents()

# Chunk analysis
chunk_analyzer = ChunkAnalyzer(chunks)
stats = chunk_analyzer.analyze()
quality = chunk_analyzer.get_quality_report()

# Metadata analysis
meta_analyzer = MetadataAnalyzer(chunks)
metadata = meta_analyzer.analyze()

print(f"Document types: {metadata['document_types']}")
print(f"Topics: {metadata['topics']}")
```

## Monitoring & Tracking

Export reports regularly to track collection health:

```bash
# Create timestamped report
python scripts/analyze_milvus.py --output "reports/analysis_$(date +%Y%m%d_%H%M%S).json"

# Monitor over time
ls -la reports/analysis_*.json
```

Create a monitoring script:

```bash
#!/bin/bash
for i in {1..5}; do
  echo "Run $i..."
  python scripts/analyze_milvus.py --output "reports/run_$i.json"
  sleep 300  # 5 min between runs
done
```

Then analyze trends:
- Is chunk count growing/shrinking?
- Are duplicates increasing?
- Is token usage stable?
- Search quality improving?

## Troubleshooting

### "Could not load chunks from Milvus"

**Cause:** Connection issue or no chunks in collection

**Solution:**
```bash
# Check if Milvus is running
python scripts/view_chunks.py --stats

# Load data if needed
python load_curriculum.py

# Verify connection
python scripts/verify_langsmith.py  # (or any script that uses MilvusRAG)
```

### "Empty Chunks" or "Missing Embeddings"

**Cause:** Data quality issues during loading

**Solution:**
```bash
# Review loaded data
python scripts/view_chunks.py --all

# Reload curriculum
python load_curriculum.py
```

### High "Chunks < 50 chars"

**Cause:** Poor chunking or extraction

**Solution:** Review chunking strategy in `DocumentChunker` or data source quality

### Low Retrieval Scores

**Cause:** Content not matching queries or embedding issues

**Solution:**
1. Check if embeddings are present (see Embedding Analysis)
2. Review query terms vs. chunk content
3. Test with different queries
4. Consider re-chunking or content preprocessing

## Integration with CI/CD

### Generate Report on Each Build

```bash
# In your CI/CD script
python scripts/analyze_milvus.py --output reports/latest.json

# Check thresholds
python -c "
import json
report = json.load(open('reports/latest.json'))
quality = report['quality_report']
if quality['duplicate_chunks'] > 0:
    print('ERROR: Duplicates detected')
    exit(1)
"
```

### Compare Builds

```bash
# Generate before & after
python scripts/analyze_milvus.py --output before.json
# ... do something ...
python scripts/analyze_milvus.py --output after.json

# Compare
python -c "
import json
before = json.load(open('before.json'))
after = json.load(open('after.json'))

before_tokens = before['token_estimation']['total_estimated_tokens']
after_tokens = after['token_estimation']['total_estimated_tokens']
change = ((after_tokens - before_tokens) / before_tokens) * 100

print(f'Token change: {change:+.1f}%')
"
```

## Architecture

```
server/tools/analyzers/
├── __init__.py
└── milvus_analyzer.py
    ├── ChunkAnalyzer          - Size, length, quality stats
    ├── MetadataAnalyzer       - Type/topic distribution
    ├── EmbeddingAnalyzer      - Vector quality analysis
    ├── RetrievalAnalyzer      - Search quality testing
    └── ReportGenerator        - Comprehensive reporting

scripts/
└── analyze_milvus.py          - CLI interface
```

## Performance Notes

- **ChunkAnalyzer**: O(n) where n = chunk count
- **MetadataAnalyzer**: O(n) metadata parsing
- **EmbeddingAnalyzer**: O(n²) for similarity (samples for large n > 1000)
- **RetrievalAnalyzer**: Depends on query complexity and index size

Typical times:
- 1K chunks: < 1 second
- 10K chunks: 2-5 seconds (with embeddings)
- 100K chunks: 30-60 seconds (with embeddings)

Use `--no-embeddings` for faster analysis on large collections.

---

**Last Updated:** 2026-07-13
**Version:** 1.0
