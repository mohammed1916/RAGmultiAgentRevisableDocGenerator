# RAG Evaluation Benchmark

## Overview

Comprehensive evaluation of the CBSE RAG system using a **100-query benchmark** spanning **7 subjects**, **9 query categories**, and **3 difficulty levels**.

## Benchmark Composition

### By Subject
- **Physics**: 20 queries
- **Chemistry**: 20 queries
- **Biology**: 20 queries
- **Mathematics**: 20 queries
- **Social Science**: 10 queries
- **English**: 5 queries
- **Computer Science**: 5 queries

### By Query Category
- Direct factual lookup (25)
- Concept explanation (20)
- Definition (10)
- Numerical/problem solving (10)
- Comparison (10)
- Multi-hop (10)
- Chapter identification (5)
- Application-based (5)
- Ambiguous wording (5)

### By Difficulty
- Easy: 30 queries
- Medium: 40 queries
- Hard: 30 queries

## Retrieval Metrics

Measured for each query:

### Core Metrics
- **Recall@1**: % of relevant documents in top 1 result
- **Recall@3**: % of relevant documents in top 3 results
- **Recall@5**: % of relevant documents in top 5 results
- **Precision@5**: Relevance of top 5 results
- **MRR (Mean Reciprocal Rank)**: Reciprocal of rank of first relevant document
- **nDCG@k**: Ranking quality metric (0-1 scale)
- **Hit Rate**: % of queries with at least one relevant result

### Breakdown By
- Query category
- Difficulty level
- Subject area

## Generation Metrics

Measured on 20-query sample (for cost efficiency):

- **Answer Similarity**: Lexical overlap with ground truth
- **Context Relevance**: Coverage of question context in retrieved docs
- **Quality Score**: Weighted combination of above metrics

## Running Evaluations

### Unified Evaluation Command

All evaluations use the unified entry point:

```bash
python -m evaluation.scripts.run_eval --mode <MODE>
```

### Retrieval Evaluation (Default)

Runs 100-query benchmark with full metrics:

```bash
python -m evaluation.scripts.run_eval --mode retrieval
```

Output: `evaluation/results/retrieval_metrics.json`

Runtime: 5-10 minutes

### Benchmark Generation

Generate new benchmark from curriculum chunks:

```bash
python -m evaluation.scripts.run_eval --mode generate-bm
```

Output: `evaluation/benchmarks/curriculum_generated.csv`

### View Results

```bash
cat evaluation/results/retrieval_metrics.json | jq '.metrics_summary'
```

## Directory Structure

```
evaluation/
├── benchmarks/                          # Evaluation datasets
│   ├── physics.csv (20 queries)
│   ├── chemistry.csv (20 queries)
│   ├── biology.csv (20 queries)
│   ├── mathematics.csv (20 queries)
│   ├── social_science.csv (10 queries)
│   ├── english.csv (5 queries)
│   ├── computer_science.csv (5 queries)
│   └── curriculum_generated.csv (auto-generated)
│
├── scripts/                             # Evaluation executables
│   ├── run_eval.py                      # Unified evaluation entry point
│   ├── run_retrieval_eval.py            # Retrieval evaluation module
│   ├── generate_curriculum_benchmark.py # Benchmark generation module
│   └── __init__.py
│
├── results/                             # Generated outputs
│   └── retrieval_metrics.json           # Full metrics + breakdowns
│
├── logs/                                # Execution logs (timestamped)
│   └── retrieval_YYYY-MM-DD_HH-MM-SS.log
│
├── docs/
│   ├── SETUP.md                        # Technical specification
│   └── README.md                        # (in docs/ directory)
│
└── README.md                            # This file
```

## Benchmark Format (CSV)

Each CSV in `benchmarks/` contains:
- **query_id**: Unique identifier (e.g., P001, C020, SS010)
- **subject**: Subject area
- **chapter**: Specific chapter/topic
- **query_text**: The actual question
- **ground_truth_answer**: Expected answer text
- **query_category**: Type of query (9 categories)
- **difficulty**: Easy/Medium/Hard
- **expected_chunks**: Comma-separated doc IDs expected in retrieval

## Interpretation

### Expected Baseline
- Recall@5: 90%+ (most queries find relevant material)
- Precision@5: 80%+ (most retrieved are useful)
- MRR: 0.85+ (relevant results ranked early)
- nDCG@5: 0.85+ (ranking quality is high)
- Hit Rate: 95%+ (very few total failures)

### Performance by Difficulty
- Easy: 98%+ hit rate
- Medium: 90-95% hit rate
- Hard: 80-90% hit rate

### Diagnostic Insights
- **Low category hit rate** → Query type gaps
- **Hard questions underperforming** → Ranking issues
- **Subject variance** → Corpus coverage gaps

## Quick Start Example

1. Verify Milvus is running with curriculum data:
```bash
python scripts/view_chunks.py --stats
```

2. Run retrieval evaluation:
```bash
python -m evaluation.scripts.run_eval --mode retrieval
```

3. Check results:
```bash
cat evaluation/results/retrieval_metrics.json | jq '.metrics_summary'
```

## Integration with RAG System

The evaluation framework integrates with the main RAG system:

1. **Uses live Milvus collection**: Tests actual retrieval performance
2. **Compatible with mock mode**: Falls back to in-memory chunks if Milvus unavailable
3. **Verifiable ground truth**: Benchmarks validate against actual corpus

## Future Enhancements

1. Generate metrics for generation quality (RAGAS)
2. Expand to 500+ queries for comprehensive coverage
3. A/B test retrieval algorithms (COSINE vs L2 distance)
4. Measure latency and throughput at scale
5. Cross-validation across different LLM models
