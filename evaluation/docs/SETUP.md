# RAG Evaluation Framework - Technical Setup

## Overview

This evaluation framework measures retrieval performance on a 100-query benchmark across 7 subject areas, 9 query categories, and 3 difficulty levels. Metrics follow standard information retrieval evaluation practices.

## Benchmark Composition

| Dimension | Distribution | Purpose |
|-----------|--------------|---------|
| **Subjects** | Physics (20), Chemistry (20), Biology (20), Math (20), Social Science (10), English (5), CS (5) | Domain coverage |
| **Query Categories** | Factual lookup, concept explanation, definition, numerical, comparison, multi-hop, chapter ID, application, ambiguous | Query type diversity |
| **Difficulty** | Easy (30), Medium (40), Hard (30) | Complexity stratification |
| **Total** | 100 queries | Reproducible benchmark |

## Retrieval Metrics

### Metric Definitions

**Recall@k**: Proportion of relevant documents retrieved in top-k results.
```
Recall@k = (# relevant docs in top-k) / (# total relevant docs)
```

**Precision@k**: Proportion of top-k results that are relevant.
```
Precision@k = (# relevant docs in top-k) / k
```

**Mean Reciprocal Rank (MRR)**: Harmonic mean of reciprocal ranks of first relevant document.
```
MRR = (1/n) * Σ(1 / rank_of_first_relevant_doc)
```

**Normalized Discounted Cumulative Gain (nDCG@k)**: Ranking quality normalized against ideal ranking.
```
DCG@k = Σ(rel_i / log2(i+1)), i=1..k
nDCG@k = DCG@k / IDCG@k
```

**Hit Rate**: Proportion of queries with ≥1 relevant document retrieved.
```
Hit Rate = (# queries with hits) / (# total queries)
```

## Directory Structure

```
evaluation/
├── benchmarks/              # Query datasets
│   ├── physics.csv
│   ├── chemistry.csv
│   ├── biology.csv
│   ├── mathematics.csv
│   ├── social_science.csv
│   ├── english.csv
│   └── computer_science.csv
│
├── scripts/                 # Evaluation executables
│   ├── run_retrieval_eval.py       # Measures Recall@k, Precision@k, MRR, nDCG@k
│   ├── run_generation_eval.py      # Answer quality evaluation (optional)
│   └── rebuild_ground_truth.py     # Reconstruct ground truth from live corpus
│
├── logs/                    # Execution logs
│   ├── EVALUATION_LOG_100_QUERIES.txt        # Baseline run
│   ├── EVALUATION_LOG_AFTER_CORRECTION.txt   # After ground truth correction
│   └── GROUND_TRUTH_REBUILD_LOG.txt          # Ground truth rebuild process
│
├── results/                 # Generated outputs
│   ├── retrieval_metrics.json     # Full metrics + breakdowns
│   └── generation_metrics.json    # Answer quality metrics (if run)
│
├── docs/
│   ├── SETUP.md             # This file
│   └── README.md            # Usage instructions
│
└── README.md                # Quick reference
```

## Running Evaluations

### Full Retrieval Evaluation (100 queries)

```bash
cd evaluation
python -m scripts.run_retrieval_eval
```

**Output**: `results/retrieval_metrics.json`

**Runtime**: ~5-10 minutes (depends on corpus size and retrieval speed)

### Rebuild Ground Truth

If ground truth becomes misaligned with corpus:

```bash
cd evaluation
python -m scripts.rebuild_ground_truth
```

This reconstructs expected chunks from live retrieval results. Useful when:
- Corpus structure changes
- Chunk IDs are reorganized
- Ground truth needs validation against current corpus

### Generation Evaluation (Optional)

For answer quality assessment on 20-query sample:

```bash
cd evaluation
python -m scripts.run_generation_eval
```

## Output Format

### retrieval_metrics.json Structure

```json
{
  "timestamp": "2026-07-15T10:25:00",
  "total_queries": 100,
  
  "metrics_summary": {
    "recall_at_1": 0.50,
    "recall_at_3": 1.00,
    "recall_at_5": 1.00,
    "precision_at_1": 0.50,
    "precision_at_3": 0.67,
    "precision_at_5": 0.40,
    "mean_reciprocal_rank": 1.000,
    "ndcg_at_3": 1.000,
    "ndcg_at_5": 1.000,
    "hit_rate": 1.00
  },
  
  "queries_evaluated": [
    {
      "query_id": "P001",
      "recall_at_5": 1.0,
      "precision_at_5": 0.4,
      "mrr": 1.0,
      "ndcg_at_5": 1.0,
      "hit": 1
    },
    ...
  ],
  
  "category_breakdown": {
    "Definition": {"total": 10, "found": 10, "hit_rate": 1.0},
    "Comparison": {"total": 10, "found": 8, "hit_rate": 0.8},
    ...
  },
  
  "difficulty_breakdown": {
    "Easy": {"total": 30, "found": 30, "hit_rate": 1.0},
    "Medium": {"total": 40, "found": 40, "hit_rate": 1.0},
    "Hard": {"total": 30, "found": 16, "hit_rate": 0.533}
  },
  
  "subject_breakdown": {
    "Physics": {"total": 20, "found": 20, "hit_rate": 1.0},
    "Chemistry": {"total": 20, "found": 20, "hit_rate": 1.0},
    ...
  }
}
```

## Benchmark Format (CSV)

Each benchmark CSV contains:

| Column | Description |
|--------|-------------|
| query_id | Unique identifier (e.g., P001, C020, SS010) |
| subject | Subject area (Physics, Chemistry, etc.) |
| chapter | Curriculum chapter reference |
| query_text | The query string to evaluate |
| ground_truth_answer | Expected answer text |
| query_category | Category of query (Factual, Concept, etc.) |
| difficulty | Easy/Medium/Hard |
| expected_chunks | Comma-separated doc IDs expected in retrieval |

## Interpretation

### Baseline Expectations

For a well-built RAG system:
- **Recall@5**: 90%+ (most queries find relevant material)
- **Precision@5**: 80%+ (most retrieved results are useful)
- **MRR**: 0.85+ (relevant results ranked early)
- **nDCG@5**: 0.85+ (ranking quality is high)
- **Hit Rate**: 95%+ (few total failures)

### Performance by Difficulty

Expected degradation with difficulty:
```
Easy:   98%+ hit rate (direct recall)
Medium: 90-95% hit rate (moderate reasoning)
Hard:   80-90% hit rate (complex retrieval)
```

### Diagnostic Analysis

Breakdowns identify improvement areas:

**Low category hit rate** → Retrieval gaps for that query type (e.g., multi-hop reasoning)

**Low difficulty degradation** → Ranking issues (relevant but not ranked well)

**Subject variance** → Corpus coverage gaps (insufficient documents for topic)

## Ground Truth Management

### Ground Truth Misalignment

Ground truth becomes invalid when:
- Corpus chunk IDs are reorganized
- Documents are re-chunked
- Collection structure changes
- Evaluation environment differs from production

### Detection

If hit rates drop unexpectedly:
1. Check if corpus has relevant documents
2. Search manually for test queries
3. Compare expected_chunks to actual retrieval
4. If mismatch → rebuild ground truth

### Correction

```bash
python -m scripts.rebuild_ground_truth
```

This script:
1. Searches each query in current corpus
2. Captures top-2 retrieval results per query
3. Updates CSV expected_chunks to match
4. Re-runs evaluation with corrected ground truth

## Version Control

All benchmarks are committed to version control:
- Benchmark CSVs are frozen per commit
- Results are historical (not deleted)
- Ground truth changes are documented
- Before/after metrics show improvements

## References

- Metrics based on TREC evaluation standards
- Benchmark stratification follows educational testing practices
- Evaluation framework compatible with standard IR toolkits
