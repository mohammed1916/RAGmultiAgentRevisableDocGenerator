# Documentation Guides

Consolidated documentation for the RAG system, organized by topic.

## Quick Links by Purpose

### Getting Started
- [GETTING_STARTED.md](GETTING_STARTED.md) - New to the project? Start here
- [RAG_OPERATIONS.md](RAG_OPERATIONS.md) - Setup and operations (includes Milvus setup, chunk viewer, and analysis)

### Understanding the System
- [EXECUTION_FLOW.md](EXECUTION_FLOW.md) - Complete flow from chat to document generation with code examples
- [API.md](API.md) - REST API reference and examples

### Testing & Quality
- [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md) - Quality metrics and testing strategy

### Observability
- [langsmith_setup.md](langsmith_setup.md) - LangSmith configuration for tracing and monitoring

## Recommended Reading Order

### For New Users (First Time)
1. **GETTING_STARTED.md** (15 min)
   - Installation
   - First run
   - Basic concepts

2. **RAG_OPERATIONS.md** (15 min)
   - Database setup
   - Data loading
   - Verification

3. **EXECUTION_FLOW.md** (20 min)
   - System architecture
   - Component interaction
   - Complete pipeline flow

### For Testing & Production
- **PRODUCTION_TESTING_GUIDE.md** (15 min)
  - Quality metrics
  - Testing strategy
  - Acceptance criteria

### For Development
- **EXECUTION_FLOW.md** (Technical reference)
- **API.md** (Integration reference)
- **RAG_OPERATIONS.md** (Debugging and analysis)

### For Operations & Monitoring
- **RAG_OPERATIONS.md** (Database operations)
- **langsmith_setup.md** (Trace visualization)

## Document Overview

| Guide | Purpose | Audience |
|-------|---------|----------|
| GETTING_STARTED.md | Onboarding and setup | New users |
| RAG_OPERATIONS.md | Database and RAG operations (consolidated) | DevOps, Developers |
| EXECUTION_FLOW.md | Technical architecture and flow | Developers, Architects |
| API.md | REST API reference | Backend engineers, Integrators |
| PRODUCTION_TESTING_GUIDE.md | Quality assurance and metrics | QA, DevOps |
| langsmith_setup.md | Observability configuration | DevOps, SRE |

## Key Concepts

### BLEU Score
- Measures n-gram precision
- Range: 0.0 (no overlap) to 1.0 (perfect)
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#quality-metrics)

### ROUGE Score
- Measures recall of n-grams
- Range: 0.0 to 1.0
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#quality-metrics)

### Groundedness
- Percentage of generated content grounded in context
- Detects hallucinations
- See: [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md#quality-metrics)

## Common Questions

### "How do I set up Milvus and load data?"
See [RAG_OPERATIONS.md](RAG_OPERATIONS.md#milvus-setup-docker)

### "How do I search for chunks?"
See [RAG_OPERATIONS.md](RAG_OPERATIONS.md#chunk-viewer-commands)

### "What's the API?"
See [API.md](API.md)

### "How does the system work?"
See [EXECUTION_FLOW.md](EXECUTION_FLOW.md)

### "How do I debug issues?"
See [RAG_OPERATIONS.md](RAG_OPERATIONS.md#chunk-analysis--debugging)

### "How do I run quality tests?"
See [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md)

### "How do I enable observability?"
See [langsmith_setup.md](langsmith_setup.md)

## Tips for Using This Documentation

- All guides are self-contained and can be read independently
- Use [Quick Links](#quick-links-by-purpose) to find what you need
- Code examples are provided where relevant
- Commands are highlighted with syntax highlighting
- Search functionality available in terminal: `grep -r "keyword" docs/guides/`

## Consolidated Guides

The following guides have been consolidated into single documents for easier maintenance:

- **RAG_OPERATIONS.md** consolidates:
  - Milvus database setup
  - Chunk viewer guide
  - Milvus analyzer tools
  - Data loading procedures

- **EXECUTION_FLOW.md** now includes:
  - Chat initialization
  - Conversation flow
  - Document generation pipeline
  - Document refinement feature

## External Resources

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Milvus Documentation: https://milvus.io/docs
- LangChain Documentation: https://python.langchain.com/docs
- BLEU Score Reference: https://en.wikipedia.org/wiki/BLEU
- ROUGE Score Reference: https://en.wikipedia.org/wiki/ROUGE_(metric)

---

**Total Documentation**: 7 comprehensive guides
**Last Updated**: 2026-07-15
