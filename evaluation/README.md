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

## Running the Evaluation

### Retrieval Evaluation
```bash
cd evaluation
python -m scripts.run_retrieval_eval
```

Output: `results/retrieval_metrics.json`

### Generation Evaluation (Optional)
```bash
cd evaluation
python -m scripts.run_generation_eval
```

Output: `results/generation_metrics.json`

### View Results
```bash
cat evaluation/results/retrieval_metrics.json | jq '.metrics_summary'
```

## Directory Structure

```
evaluation/
├── benchmarks/                          # 100 curated questions
│   ├── physics.csv (20 queries)
│   ├── chemistry.csv (20 queries)
│   ├── biology.csv (20 queries)
│   ├── mathematics.csv (20 queries)
│   ├── social_science.csv (10 queries)
│   ├── english.csv (5 queries)
│   └── computer_science.csv (5 queries)
│
├── scripts/                             # Evaluation scripts
│   ├── run_retrieval_eval.py           # Measures Recall@k, Precision@k, MRR, nDCG@k
│   ├── run_generation_eval.py          # Answer quality (optional)
│   └── rebuild_ground_truth.py         # Reconstruct ground truth from corpus
│
├── results/                             # Generated outputs
│   ├── retrieval_metrics.json          # Full metrics + breakdowns
│   └── generation_metrics.json         # Answer quality metrics (if run)
│
├── logs/                                # Execution logs
│   ├── EVALUATION_LOG_100_QUERIES.txt
│   ├── EVALUATION_LOG_AFTER_CORRECTION.txt
│   └── GROUND_TRUTH_REBUILD_LOG.txt
│
├── docs/
│   ├── SETUP.md                        # Technical specification
│   └── README.md                        # This file
└── README.md                            # Quick start
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

## Baseline Results

To be filled in after first evaluation run.

## Future Improvements

1. **Include RAGAS metrics** for generation quality
2. **Expand to 500+ queries** for comprehensive evaluation
3. **A/B test retrieval algorithms** (COSINE vs L2 distance)
4. **Measure latency and throughput** at scale
5. **Cross-validation** across different LLM models
