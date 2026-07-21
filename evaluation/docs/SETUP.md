# RAG Evaluation Framework - Technical Setup

## Overview

This evaluation framework measures retrieval performance using **curriculum_generated.csv** benchmark. This benchmark is auto-generated from CBSE curriculum chunks, ensuring ground truth always matches the actual corpus structure.

## Benchmark Composition (Verified)

Auto-generated from curriculum chunks. **200 queries** distributed as:

| Dimension        | Distribution                                      |
| ---------------- | ------------------------------------------------- |
| Subjects         | Mathematics, Science, Social Science              |
| Query Category   | Curriculum-generated (auto-generated from chunks) |
| Difficulty Level | Medium (all queries)                              |
| Total Queries    | 200                                               |


### Distribution by Subject

- **Mathematics**: 93 queries
- **Science**: 74 queries
- **Social Science**: 33 queries

**Note**: Previous documentation mentioned 100 queries across 7 subjects with varying difficulty levels. This was based on an older manual benchmark design. The current system uses **curriculum_generated.csv** which is programmatically generated to match corpus content, ensuring 100% ground truth accuracy.

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
│   └── curriculum_generated.csv (from benchmark generation)
│
├── scripts/                 # Evaluation executables
│   ├── run_eval.py                    # Unified evaluation runner (primary entry point)
│   ├── run_retrieval_eval.py          # Retrieval evaluation module
│   ├── generate_curriculum_benchmark.py  # Generate benchmark from curriculum chunks
│   └── (other evaluation modules)
│
├── logs/                    # Execution logs
│   ├── retrieval_YYYY-MM-DD_HH-MM-SS.log    # Retrieval evaluation logs
│   └── (other evaluation logs)
│
├── results/                 # Generated outputs
│   ├── retrieval_metrics.json           # Full retrieval metrics + breakdowns
│   └── (other evaluation results)
│
├── docs/
│   ├── SETUP.md             # This file (technical setup)
│   └── README.md            # Usage instructions
│
└── README.md                # Quick reference
```

## Running Evaluations

### Unified Evaluation Entry Point

All evaluations are run through the unified `run_eval.py` script:

```bash
python -m evaluation.scripts.run_eval --mode <MODE>
```

### Available Modes

#### 1. Retrieval Evaluation (Default Mode)

Measures Recall@k, Precision@k, MRR, nDCG@k on 100-query benchmark:

```bash
python -m evaluation.scripts.run_eval --mode retrieval
```

**Output**: `evaluation/results/retrieval_metrics.json`

**Runtime**: Approximately 5-10 minutes (depends on corpus size and retrieval speed)

**What it does**:
- Loads all benchmark queries from CSV files
- Runs retrieval for each query
- Calculates metrics per query and aggregates
- Generates category, difficulty, and subject breakdowns
- Saves detailed results to JSON

#### 2. Benchmark Generation Mode

Generate benchmark from curriculum chunks:

```bash
python -m evaluation.scripts.run_eval --mode generate-bm
```

**Output**: `evaluation/benchmarks/curriculum_generated.csv`

**Usage**: Create new benchmark from existing curriculum data

### Benchmark Options

Specify a custom benchmark file:

```bash
python -m evaluation.scripts.run_eval --mode retrieval --benchmark path/to/custom_benchmark.csv
```

Default: `evaluation/benchmarks/curriculum_generated.csv`

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

| Column              | Description                                   |
| ------------------- | --------------------------------------------- |
| query_id            | Unique identifier (e.g., P001, C020, SS010)   |
| subject             | Subject area (Physics, Chemistry, etc.)       |
| chapter             | Curriculum chapter reference                  |
| query_text          | The query string to evaluate                  |
| ground_truth_answer | Expected answer text                          |
| query_category      | Category of query (Factual, Concept, etc.)    |
| difficulty          | Easy/Medium/Hard                              |
| expected_chunks     | Comma-separated doc IDs expected in retrieval |

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

## Benchmark Management

### Benchmark Sources

Benchmarks can come from two sources:

1. **Manual Benchmarks**: Pre-written CSV files with queries and expected chunks
   - Located in `evaluation/benchmarks/`
   - Can be edited directly
   - Version controlled

2. **Generated Benchmarks**: Auto-generated from curriculum chunks
   ```bash
   python -m evaluation.scripts.run_eval --mode generate-bm
   ```
   - Creates `curriculum_generated.csv`
   - Useful for large-scale evaluation
   - Based on actual corpus content

### Ground Truth Validation

If retrieval metrics seem anomalous:

1. **Verify data loads**: Check that chunks are indexed in Milvus
   ```bash
   python scripts/view_chunks.py --stats
   ```

2. **Test manual search**: Run a query directly
   ```bash
   python scripts/view_chunks.py --search "query_text"
   ```

3. **Compare results**: Check if expected chunks appear in manual search

4. **Regenerate if needed**: Create fresh benchmark from current corpus
   ```bash
   python -m evaluation.scripts.run_eval --mode generate-bm
   ```

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
