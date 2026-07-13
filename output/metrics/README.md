# Metrics Directory

This directory contains RAG quality metrics and evaluation history.

## metrics_history.jsonl

**Format:** JSONL (JSON Lines) - one JSON object per line

**Purpose:** Historical record of all metrics runs over time

**Contents:** Each line contains:
- `timestamp` - ISO format timestamp of when metrics were run
- `test_type` - Type of test ("single_test" for show_metrics.py)
- `prompt` - The prompt used for testing
- `bleu` - BLEU scores (1-gram through 4-gram)
- `rouge` - ROUGE scores (1, 2, and L)
- `groundedness` - How well content is grounded in context
- `context_utilization` - How much retrieved context was used
- `semantic_similarity` - Jaccard similarity
- `overall_evaluation_score` - Weighted combination

## How It Works

### Single Test Metrics
```bash
python scripts/show_metrics.py
# Displays metrics to console AND appends to metrics_history.jsonl
```

### Comprehensive Test Results
```bash
python scripts/test_rag_quality.py
# Saves detailed JSON to output/test_results/quality_test_results.json
```

## Reading the History

### View all metrics entries
```bash
cat metrics_history.jsonl | python -m json.tool
```

### Count total runs
```bash
wc -l metrics_history.jsonl
```

### Extract just timestamps and scores
```bash
python -c "
import json
with open('metrics_history.jsonl') as f:
    for line in f:
        data = json.loads(line)
        print(f\"{data['timestamp']}: Overall={data['overall_evaluation_score']:.4f}\")
"
```

### Plot metrics over time
```python
import json
import matplotlib.pyplot as plt
from datetime import datetime

timestamps = []
scores = []

with open('metrics_history.jsonl') as f:
    for line in f:
        data = json.loads(line)
        timestamps.append(datetime.fromisoformat(data['timestamp']))
        scores.append(data['overall_evaluation_score'])

plt.plot(timestamps, scores)
plt.xlabel('Time')
plt.ylabel('Overall Evaluation Score')
plt.title('RAG Quality Metrics Over Time')
plt.show()
```

## Metrics Interpretation

### Overall Evaluation Score (0.0-1.0)
- **< 0.5**: Poor quality
- **0.5-0.7**: Acceptable
- **0.7+**: Good (production threshold)

### BLEU Score
- Measures n-gram precision
- Higher = more similar to reference
- Range: 0.0-1.0

### ROUGE Score
- Measures n-gram recall
- Higher = better coverage of reference
- Range: 0.0-1.0

### Groundedness (0.0-1.0)
- Percentage of generated content grounded in context
- **< 0.4**: High hallucination
- **0.6+**: Well grounded

### Context Utilization (0.0-1.0)
- Percentage of retrieved context used
- **< 0.3**: Poor retrieval
- **0.5+**: Good efficiency

## File Growth Management

The JSONL file will grow with each run. To manage size:

```bash
# Keep only last 100 entries
tail -100 metrics_history.jsonl > metrics_history.tmp && mv metrics_history.tmp metrics_history.jsonl

# Archive old entries
head -n -100 metrics_history.jsonl > metrics_history.archive.jsonl
tail -100 metrics_history.jsonl > metrics_history.jsonl
```

## Integration with CI/CD

Use metrics history to:
- Track quality improvements over time
- Detect regressions in RAG quality
- Validate curriculum data quality
- Monitor LLM consistency

Example: Create an alert if score drops 10% from average
```python
import json
import statistics

scores = []
with open('metrics_history.jsonl') as f:
    for line in f:
        data = json.loads(line)
        scores.append(data['overall_evaluation_score'])

avg = statistics.mean(scores[-10:])  # last 10 runs
current = scores[-1]

if current < avg * 0.9:
    print(f"ALERT: Score dropped from {avg:.4f} to {current:.4f}")
```

---

**Last Updated:** 2026-07-13
**Created By:** show_metrics.py auto-save feature
