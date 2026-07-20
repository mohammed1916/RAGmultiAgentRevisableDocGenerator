# Production Testing Guide - RAG Quality Metrics

## Overview

This guide explains how to validate your RAG (Retrieval-Augmented Generation) system for production use. Testing consists of:
1. **Demo Testing** (current state) - validates system works with perfect reference
2. **Real Testing** - validates system quality with actual curriculum data
3. **Quality Thresholds** - targets for production readiness

---

## Current Test Results (Demo Mode)

**Status**: ✅ All tests PASSED

```
Total Tests: 3 difficult prompts
Successful: 3/3 (100%)
Failed: 0

Metrics (all perfect because comparing content against itself):
  - Overall Score: 1.0000 ✓ GOOD
  - BLEU Score: 1.0000 ✓
  - ROUGE-1: 1.0000 ✓
  - Groundedness: 100% ✓
  - Context Utilization: 100% ✓
```

**⚠️ Important**: These are perfect scores because Milvus has NO curriculum data yet. The metrics compare the generated content against itself as a reference. This is useful for:
- ✓ Validating the system generates output successfully
- ✓ Checking document generation pipeline works
- ✓ Ensuring review/refinement logic works
- ✗ NOT useful for validating RAG quality or groundedness

---

## How to Test With Real Data (Production Validation)

### Step 1: Load Curriculum Data

```bash
python load_curriculum.py
```

This populates Milvus with actual curriculum chunks. After loading:

```bash
python scripts/show_metrics.py
```

You'll see metrics like:
```
[BLEU] Bilingual Evaluation Understudy Score
  BLEU-1: 0.45-0.65
  BLEU-2: 0.30-0.50
  BLEU-3: 0.15-0.35
  BLEU-4: 0.05-0.20
  Overall BLEU: 0.35-0.55

[GROUNDEDNESS] How well content is grounded in context
  Groundedness Score: 0.50-0.75 (realistic)
  Grounded Tokens: 60%−85%
```

### Step 2: Run Comprehensive Tests

```bash
python scripts/test_rag_quality.py
```

This runs 3 difficult prompts and collects:
- Multiple quality metrics per prompt
- Aggregated statistics (min/avg/max)
- Pass/fail analysis
- JSON results file for CI/CD integration

---

## Quality Metrics Explained

### BLEU (Bilingual Evaluation Understudy)
- **What it measures**: How many n-grams (word sequences) from generated text appear in reference text
- **Range**: 0.0 (no overlap) to 1.0 (perfect overlap)
- **Production threshold**: ≥ 0.5
- **What it means**:
  - 0.0-0.3: Poor - very different from reference
  - 0.3-0.5: Acceptable - some overlap with reference
  - 0.5-0.7: Good - significant overlap
  - 0.7+: Excellent - high similarity

### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
- **What it measures**: Recall of n-grams from reference text appearing in generated text
- **ROUGE-1**: Unigram (single word) recall
- **ROUGE-2**: Bigram (two-word phrases) recall
- **ROUGE-L**: Longest common subsequence recall
- **Production threshold**: ≥ 0.5
- **Interpretation**: Measures coverage of reference content in output

### Groundedness
- **What it measures**: What percentage of generated content tokens appear in the RAG context
- **Range**: 0.0 to 1.0 (as percentage: 0%-100%)
- **Production threshold**: ≥ 0.6 (at least 60%)
- **What it means**:
  - < 0.4: Hallucinating (content not grounded in context)
  - 0.4-0.6: Partially grounded (some hallucination)
  - 0.6-0.8: Well grounded
  - > 0.8: Highly grounded

### Context Utilization
- **What it measures**: How much of the retrieved context is actually used in generation
- **Range**: 0.0 to 1.0
- **Production threshold**: ≥ 0.5
- **What it means**:
  - < 0.3: Poor retrieval (wrong context retrieved)
  - 0.3-0.5: Partial use (retriever works but LLM ignores some)
  - 0.5-0.7: Good use of context
  - > 0.7: Efficient RAG

### Semantic Similarity
- **What it measures**: Jaccard similarity (word overlap) between texts
- **Range**: 0.0 to 1.0
- **Production threshold**: ≥ 0.3

### Overall Evaluation Score
- **Calculation**: Weighted average of all metrics
- **Weights**: 
  - 25% BLEU
  - 25% ROUGE-1
  - 25% Semantic Similarity
  - 25% Groundedness (if RAG context available)
- **Production threshold**: ≥ 0.7

---

## Production Readiness Checklist

### Phase 1: System Validation (Current Status ✓)
- [x] LangGraph orchestrator running
- [x] Document generation pipeline works
- [x] Review/refinement loop functions
- [x] Output document generation succeeds
- [x] Metrics calculation works

### Phase 2: Data Loading
- [ ] `python load_curriculum.py` completes
- [ ] Milvus confirms data loaded
- [ ] Retrieval returns relevant chunks
- [ ] Chunks have quality metadata

### Phase 3: Quality Validation
```bash
python scripts/test_rag_quality.py
```

Verify:
- [ ] All 3 tests pass (100% success rate)
- [ ] Overall Score ≥ 0.7
- [ ] BLEU Score ≥ 0.5
- [ ] ROUGE-1 Score ≥ 0.5
- [ ] Groundedness ≥ 0.6
- [ ] Context Utilization ≥ 0.5
- [ ] Consistent scores across runs (low variance)

### Phase 4: Edge Cases
Create and test edge cases:
- Long prompts (>500 words request)
- Ambiguous prompts (could match multiple topics)
- Out-of-domain prompts (not in curriculum)
- Complex multi-part questions

### Phase 5: Performance
- [ ] Document generation < 2 minutes per prompt
- [ ] Metrics calculation < 30 seconds
- [ ] No memory leaks after 10+ runs

---

## Interpreting Results

### If Overall Score < 0.5 (Fail)
**Problem**: RAG not working well
**Likely causes**:
1. Curriculum data not loaded
2. Retriever returning irrelevant chunks
3. LLM not respecting context
4. Prompt too ambiguous

**Action**:
- Check retrieved chunks: `python scripts/view_chunks.py`
- Verify curriculum loading: `python load_curriculum.py --check`
- Inspect generated content for hallucinations
- Try simpler prompts

### If Groundedness < 0.4 (High Hallucination)
**Problem**: Generated content not grounded in retrieved context
**Likely causes**:
1. LLM generating from training data instead of context
2. Context retrieval returning irrelevant data
3. Prompt not guiding LLM toward context use

**Action**:
- Add system prompt: "Use only information from the provided context"
- Improve retrieval: check keyword matching in prompts
- Validate retrieved chunks are relevant

### If Context Utilization < 0.3 (Low Usage)
**Problem**: Retrieved context not being used
**Likely causes**:
1. Retriever returning irrelevant chunks
2. LLM ignoring context
3. Retrieved chunks too verbose/unclear

**Action**:
- Chunk curriculum data more granularly
- Filter low-relevance chunks
- Improve chunk summaries/metadata

---

## Continuous Testing Strategy

### Daily Testing
Run quick sanity check:
```bash
python scripts/show_metrics.py
```

### Weekly Testing
Run comprehensive test suite:
```bash
python scripts/test_rag_quality.py
```

Check for:
- Score trends (should stay > 0.7)
- Latency increases
- New failure patterns

### Monthly Testing
Run extended tests:
- 20+ prompts (mixture of difficulties)
- Edge cases
- Performance benchmarks
- A/B comparison with previous version

### Before Deployment
```bash
# Full validation
python scripts/test_rag_quality.py

# Check results file
cat quality_test_results.json
```

Requires:
- ✅ 100% success rate
- ✅ Overall Score ≥ 0.7
- ✅ Groundedness ≥ 0.6
- ✅ All metrics stable

---

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Test RAG Quality
  run: |
    python scripts/test_rag_quality.py
    python -c "
    import json
    with open('quality_test_results.json') as f:
        results = json.load(f)
    overall = results['results'][0]['metrics']['overall_evaluation_score']
    assert overall >= 0.7, f'Overall score {overall} below 0.7 threshold'
    "
```

### JSON Output Format
Results saved to `quality_test_results.json`:
```json
{
  "timestamp": "2026-07-13T10:10:45",
  "total_tests": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "prompt": "...",
      "success": true,
      "metrics": {
        "overall_evaluation_score": 0.75,
        "bleu": {...},
        "rouge": {...},
        "groundedness": {...}
      }
    }
  ]
}
```

---

## Next Steps

1. **Load curriculum**: `python load_curriculum.py`
2. **Run quick test**: `python scripts/show_metrics.py`
3. **Run comprehensive test**: `python scripts/test_rag_quality.py`
4. **Review JSON results**: `cat quality_test_results.json`
5. **Adjust thresholds** if needed based on your SLA
6. **Integrate into CI/CD** for continuous validation

---

## Success Criteria for Production

| Metric | Threshold | Status |
|--------|-----------|--------|
| System Success Rate | 100% | ✅ 100% |
| Overall Score | ≥ 0.7 | ⚠️ 1.0 (demo) |
| BLEU Score | ≥ 0.5 | ⚠️ 1.0 (demo) |
| Groundedness | ≥ 0.6 | ⚠️ 1.0 (demo) |
| Context Utilization | ≥ 0.5 | ⚠️ 1.0 (demo) |
| Document Generation | < 2 min | ✅ ~60s avg |

**Next action**: Load curriculum data and rerun tests for realistic metrics.
