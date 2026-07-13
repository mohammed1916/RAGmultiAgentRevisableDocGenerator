# Guides

Complete documentation for the RAG system. 9 comprehensive guides organized by topic.

## Quick Links by Purpose

### Getting Started
- [GETTING_STARTED.md](GETTING_STARTED.md) - New to the project? Start here
- [MILVUS_SETUP.md](MILVUS_SETUP.md) - Setting up the database

### Understanding the System
- [EXECUTION_FLOW.md](EXECUTION_FLOW.md) - Deep dive into how everything works
- [API.md](API.md) - REST API reference and examples

### Testing & Production
- [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md) - Quality metrics and testing strategy
- [TESTING_SUMMARY.md](TESTING_SUMMARY.md) - Quick test results overview

### Data & Debugging
- [CHUNK_VIEWER_GUIDE.md](CHUNK_VIEWER_GUIDE.md) - Complete guide to viewing/searching chunks
- [VIEW_CHUNKS_SUMMARY.md](VIEW_CHUNKS_SUMMARY.md) - Quick reference for chunk viewer

## Reading Order

### For New Users
1. **GETTING_STARTED.md** (15 min)
   - Installation
   - First run
   - Basic concepts

2. **MILVUS_SETUP.md** (10 min)
   - Database setup
   - Configuration
   - Verification

3. **EXECUTION_FLOW.md** (20 min)
   - System architecture
   - Component interaction
   - Pipeline flow

### For Testing & Production
1. **PRODUCTION_TESTING_GUIDE.md** (15 min)
   - Quality metrics
   - Testing strategy
   - Thresholds

2. **TESTING_SUMMARY.md** (5 min)
   - Recent results
   - Interpretation

### For Debugging
1. **CHUNK_VIEWER_GUIDE.md** (15 min)
   - All available commands
   - Workflows
   - Troubleshooting

2. **VIEW_CHUNKS_SUMMARY.md** (5 min)
   - Quick reference
   - Common searches

### For Integration
- **API.md** (10 min)
  - Endpoints
  - Request/response formats
  - Examples

## Document Summary

| Guide | Purpose | Time | For Whom |
|-------|---------|------|----------|
| GETTING_STARTED.md | Quick onboarding | 15 min | New users |
| MILVUS_SETUP.md | Database setup | 10 min | DevOps / Setup |
| EXECUTION_FLOW.md | Technical deep dive | 20 min | Developers |
| API.md | API reference | 10 min | Integration / Backend |
| PRODUCTION_TESTING_GUIDE.md | Quality assurance | 15 min | QA / DevOps |
| TESTING_SUMMARY.md | Test results | 5 min | Everyone |
| CHUNK_VIEWER_GUIDE.md | Data inspection | 15 min | Debugging / Analysis |
| VIEW_CHUNKS_SUMMARY.md | Chunk viewer cheatsheet | 5 min | Power users |

## Key Concepts Explained

### BLEU Score
- Measures n-gram precision
- Range: 0.0 (no overlap) to 1.0 (perfect)
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#bleu)

### ROUGE Score
- Measures recall of n-grams
- Range: 0.0 to 1.0
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#rouge)

### Groundedness
- % of generated content grounded in context
- Detects hallucinations
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#groundedness)

### Context Utilization
- How much retrieved context is used
- Indicates RAG efficiency
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#context-utilization)

## Common Tasks

### "How do I run tests?"
→ See [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md)

### "How do I search for chunks?"
→ See [CHUNK_VIEWER_GUIDE.md](CHUNK_VIEWER_GUIDE.md#search-chunks)

### "What's the API?"
→ See [API.md](API.md)

### "How does the system work?"
→ See [EXECUTION_FLOW.md](EXECUTION_FLOW.md)

### "I'm stuck, how do I debug?"
→ See [CHUNK_VIEWER_GUIDE.md](CHUNK_VIEWER_GUIDE.md#troubleshooting)

## Tips for Reading

- Each guide is **self-contained** - can read in any order
- Use **[Quick Links](#quick-links-by-purpose)** to find what you need
- **Code examples** are provided where relevant
- **Related guides** are linked at the bottom of each document
- **Commands** are highlighted with syntax highlighting

## Updating Documentation

When you update code:
1. Check which guides reference the code
2. Update the relevant guide
3. Update [../INDEX.md](../INDEX.md) if adding new guides
4. Add a note in the changelog

## External Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Milvus Documentation](https://milvus.io/docs)
- [Langchain Documentation](https://python.langchain.com/docs)
- [BLEU Score Explanation](https://en.wikipedia.org/wiki/BLEU)
- [ROUGE Score Explanation](https://en.wikipedia.org/wiki/ROUGE_(metric))

---

**Total Documentation:** ~150 KB across 9 guides
**Last Updated:** 2026-07-13
