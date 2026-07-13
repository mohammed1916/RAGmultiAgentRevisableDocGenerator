# Output Directory Structure

This directory contains all output files from the RAG system.

## Subdirectories

### `/documents/`
Generated DOCX files from document generation tests.
- Named: `document_YYYYMMDD_HHMMSS.docx`
- Created by: LangGraph orchestrator
- Updated: Every time a document is generated

Example:
```
output/documents/
├── document_20260713_094949.docx
├── document_20260713_100933.docx
└── document_20260713_101044.docx
```

### `/test_results/`
Quality test results and metrics in JSON format.
- `quality_test_results.json` - Results from comprehensive RAG quality tests
- Contains: Metrics for all test prompts, aggregated statistics, pass/fail analysis
- Updated: After running `python scripts/test_rag_quality.py`

Example:
```
output/test_results/
└── quality_test_results.json
    {
      "timestamp": "2026-07-13T10:10:45",
      "total_tests": 3,
      "successful": 3,
      "failed": 0,
      "results": [...]
    }
```

### `/metrics/` (Reserved)
For future metrics aggregation and analysis.

## Typical Workflow

```bash
# 1. Run quality tests
python scripts/test_rag_quality.py
# Creates: output/test_results/quality_test_results.json
# Creates: output/documents/document_*.docx

# 2. View test results
cat output/test_results/quality_test_results.json

# 3. Inspect generated documents
# Files: output/documents/document_*.docx
```

## JSON Results Format

```json
{
  "timestamp": "2026-07-13T10:10:45.020747",
  "total_tests": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "prompt": "...",
      "difficulty": "HARD",
      "run": 1,
      "success": true,
      "metrics": {
        "bleu": {...},
        "rouge": {...},
        "groundedness": {...},
        "context_utilization": {...},
        "overall_evaluation_score": 0.75
      },
      "iterations": 2,
      "sections": 1
    }
  ]
}
```

## Accessing Results Programmatically

```python
import json

# Load test results
with open("output/test_results/quality_test_results.json") as f:
    results = json.load(f)

# Get metrics
overall_score = results["results"][0]["metrics"]["overall_evaluation_score"]
print(f"Overall Score: {overall_score}")

# Check if all tests passed
all_passed = results["successful"] == results["total_tests"]
print(f"All Tests Passed: {all_passed}")
```

## Cleanup

To clean old test files:
```bash
# Remove all documents older than 7 days
find output/documents -name "*.docx" -mtime +7 -delete

# Keep only latest test result
ls -t output/test_results/quality_test_results.json | tail -n +2 | xargs rm
```

## Integration with CI/CD

For CI/CD pipelines, use:
```bash
# Run tests and capture exit code
python scripts/test_rag_quality.py
if [ $? -eq 0 ]; then
  echo "Tests passed"
  # Archive results
  cp output/test_results/quality_test_results.json ci_artifacts/
fi
```

## File Retention Policy

| Directory | Retention | Notes |
|-----------|-----------|-------|
| `/documents/` | 30 days | Generated documents, can be large |
| `/test_results/` | All | Keep for audit trail |
| `/metrics/` | - | For aggregated analysis |

---

**Last Updated**: 2026-07-13
