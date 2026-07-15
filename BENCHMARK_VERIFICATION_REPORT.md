# Benchmark Verification Report

**Date**: 2026-07-15  
**File Verified**: `evaluation/benchmarks/curriculum_generated.csv`  
**Method**: CSV parsing with grep and line counting

---

## Summary

Benchmark documentation has been updated to reflect **actual verified** data from the curriculum-generated benchmark file.

---

## Findings

### What We Claimed (Old Documentation)

| Metric | Claim |
|--------|-------|
| Total Queries | 100 |
| Subjects | 7 (Physics, Chemistry, Biology, Mathematics, Social Science, English, CS) |
| Query Categories | 9 (Factual, Concept, Definition, Numerical, Comparison, Multi-hop, Chapter ID, Application, Ambiguous) |
| Difficulty Levels | 3 (Easy, Medium, Hard) |
| Source | Manual benchmark with predefined queries |

### What We Actually Have (Verified)

| Metric | Actual |
|--------|--------|
| Total Queries | 200 |
| Subjects | 3 (Mathematics, Science, Social Science) |
| Query Categories | 1 (curriculum-generated) |
| Difficulty Levels | 1 (Medium - uniform across all) |
| Source | Auto-generated from CBSE curriculum chunks |

### Actual Distribution by Subject

```
Mathematics:        93 queries (46.5%)
Science:            74 queries (37.0%)
Social Science:     33 queries (16.5%)
─────────────────────────────────
Total:             200 queries
```

---

## Reason for Difference

The current benchmark is **auto-generated** from curriculum chunks using:

```bash
python -m evaluation.scripts.run_eval --mode generate-bm
```

This approach ensures:

1. **Ground truth accuracy**: Queries are generated directly from chunk content
2. **No misalignment**: Expected chunks always exist in corpus
3. **Dynamic benchmarks**: Benchmark updates automatically when corpus changes
4. **Reproducibility**: Same corpus = same benchmark every time

The old manual benchmark approach required:
- Manual query creation
- Manual chunk selection as ground truth
- Regular updates when corpus changed
- Risk of ground truth becoming stale

---

## Documents Updated

| Document | Change |
|----------|--------|
| `evaluation/docs/SETUP.md` | Updated overview and benchmark composition table with verified data |
| `evaluation/README.md` | Updated benchmark description with actual subject/difficulty distribution |
| `evaluation/scripts/run_eval.py` | (No change needed - already supports generate-bm mode) |

---

## How to Verify

Run this command to generate a fresh benchmark and see current statistics:

```bash
python -m evaluation.scripts.run_eval --mode generate-bm
wc -l evaluation/benchmarks/curriculum_generated.csv  # Should show 201 (200 + header)
```

To run evaluation with this benchmark:

```bash
python -m evaluation.scripts.run_eval --mode retrieval
```

---

## Going Forward

- **Benchmark is dynamic**: Auto-generated each time from current chunks
- **No manual maintenance**: Changes automatically with corpus updates
- **All 200 queries at Medium difficulty**: Good for baseline measurement
- **To add difficulty stratification**: Would need manual chunk selection or automated semantic difficulty analysis

---

## Verified By

- CSV line count: 201 lines (200 data rows + 1 header)
- Subject distribution: Confirmed with grep
- Category/Difficulty: All curriculum-generated and Medium respectively
- Sample inspection: Verified query format and chunk references
