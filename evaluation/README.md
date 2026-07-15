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
python evaluation/run_retrieval_eval.py
```

Output: `evaluation/retrieval_metrics.json`

### Generation Evaluation
```bash
python evaluation/run_generation_eval.py
```

Output: `evaluation/generation_metrics.json`

### View Results
```bash
cat evaluation/retrieval_metrics.json
cat evaluation/generation_metrics.json
```

## Benchmark Files

- `physics.csv`: 20 physics questions
- `chemistry.csv`: 20 chemistry questions
- `biology.csv`: 20 biology questions
- `mathematics.csv`: 20 math questions
- `social_science.csv`: 10 social science questions
- `english.csv`: 5 English questions
- `computer_science.csv`: 5 computer science questions

Each CSV contains:
- query_id: Unique identifier
- subject: Subject area
- chapter: Specific chapter/topic
- query_text: The actual question
- ground_truth_answer: Expected answer
- query_category: Type of query (9 categories)
- difficulty: Easy/Medium/Hard
- expected_chunks: Expected document chunks to retrieve

## Interpretation

### Strong Performance Indicators
- Recall@5 > 80%: Excellent retrieval
- Recall@3 > 70%: Good retrieval
- MRR > 0.75: Strong ranking
- nDCG@5 > 0.80: Good relevance ordering

### Weakness Areas
- Low hit rate on specific categories → Need to improve for that query type
- Difficulty degradation → Hard questions need better retrieval

## Reproducibility

All benchmarks are versioned and committed to git:
```
evaluation/
├── benchmark/
│   ├── physics.csv
│   ├── chemistry.csv
│   ├── biology.csv
│   ├── mathematics.csv
│   ├── social_science.csv
│   ├── english.csv
│   └── computer_science.csv
├── run_retrieval_eval.py
├── run_generation_eval.py
├── retrieval_metrics.json (generated)
├── generation_metrics.json (generated)
└── README.md
```

## Baseline Results

To be filled in after first evaluation run.

## Future Improvements

1. **Include RAGAS metrics** for generation quality
2. **Expand to 500+ queries** for comprehensive evaluation
3. **A/B test retrieval algorithms** (COSINE vs L2 distance)
4. **Measure latency and throughput** at scale
5. **Cross-validation** across different LLM models
