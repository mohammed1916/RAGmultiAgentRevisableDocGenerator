# LangSmith Setup Guide

LangSmith provides observability and monitoring for LLM applications. This guide explains how to enable tracing for the SpecBot RAG application.

## What is LangSmith?

LangSmith is LangChain's tracing and observability platform that helps you:
- **Monitor** agent and chain executions in real-time
- **Debug** issues by viewing complete execution traces
- **Evaluate** quality metrics across runs
- **Compare** different versions and experiments
- **Optimize** prompts and chains with feedback

## Setup Steps

### 1. Get API Key from LangSmith

1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up or log in with your account
3. Navigate to **Settings** → **API Keys**
4. Create a new API key and copy it

### 2. Set Environment Variables

Add to your `.env` file:

```env
LANGSMITH_ENABLED=true
LANGSMITH_API_KEY=ls_xxxxxxxxxxxxxxxxxxxxx
LANGSMITH_PROJECT=specbot-rag
```

Or set as system environment variables:

**Windows (PowerShell):**
```powershell
$env:LANGSMITH_ENABLED = "true"
$env:LANGSMITH_API_KEY = "ls_xxxxxxxxxxxxxxxxxxxxx"
$env:LANGSMITH_PROJECT = "specbot-rag"
```

**Windows (Command Prompt):**
```cmd
set LANGSMITH_ENABLED=true
set LANGSMITH_API_KEY=ls_xxxxxxxxxxxxxxxxxxxxx
set LANGSMITH_PROJECT=specbot-rag
```

**Linux/Mac:**
```bash
export LANGSMITH_ENABLED=true
export LANGSMITH_API_KEY="ls_xxxxxxxxxxxxxxxxxxxxx"
export LANGSMITH_PROJECT="specbot-rag"
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Setup

Run the verification script:

```bash
python scripts/verify_langsmith.py
```

Expected output:
```
[OK] LangSmith Configuration
  Enabled: true
  API Key: ls_...xxxxx (masked)
  Project: specbot-rag
  Endpoint: https://api.smith.langchain.com
  Tracing: READY
```

### 5. Run Application with Tracing

Start the document generation to trace:

```bash
# Single test run
python scripts/show_metrics.py

# Or test via API
python run_server.py
# Then: curl -X POST http://localhost:8000/api/generate \
#   -H "Content-Type: application/json" \
#   -d '{"request": "Create a physics study plan"}'
```

## Viewing Traces in LangSmith

1. Go to [LangSmith Dashboard](https://smith.langchain.com/)
2. Select your project (e.g., `specbot-rag`)
3. View traces in real-time as operations execute
4. Click on a trace to see:
   - Full execution flow (plan → write → review → refine → generate)
   - Agent inputs and outputs
   - Token usage and timing
   - LLM model and parameters
   - Error details if any

## Tracing Architecture

The application traces at multiple levels:

```
Document Generation (root trace)
├─ [PLAN] Planner Agent
│  └─ LLM Call: qwen3:8b
├─ [WRITE] Writer Agent
│  └─ LLM Call: qwen3:8b
├─ [REVIEW] Reviewer Agent
│  └─ LLM Call: qwen3:8b
├─ [REFINE] Refinement Loop (if needed)
│  └─ Writer Agent (revision)
│     └─ LLM Call: qwen3:8b
└─ [GENERATE] DOCX Generation
   └─ File: output/documents/document_*.docx
```

## Configuration Details

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGSMITH_ENABLED` | `false` | Enable/disable tracing |
| `LANGSMITH_API_KEY` | `` | Your LangSmith API key |
| `LANGSMITH_PROJECT` | `specbot-rag` | Project name in LangSmith |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API endpoint |

### Python Configuration

In code, use the config:

```python
from server.config.settings import config
from server.tools.utils.langsmith_tracer import enable_langsmith_tracing

# Check status
status = config.langsmith
print(f"Enabled: {status.enabled}")
print(f"Project: {status.project}")

# Enable/disable at runtime
enable_langsmith_tracing("custom-project")
```

## Best Practices

### 1. Project Organization

Create separate projects for different purposes:
- `specbot-rag-dev` - Development and debugging
- `specbot-rag-test` - Testing and evaluation
- `specbot-rag-prod` - Production runs

### 2. Monitoring

Regular check LangSmith dashboard for:
- **Token usage trends** - Optimize to reduce costs
- **Latency** - Monitor performance degradation
- **Error rates** - Catch issues early
- **Quality metrics** - Track generation quality over time

### 3. Debugging Issues

If document generation fails:
1. Check the trace in LangSmith
2. Look at the exact LLM input/output
3. See which agent step failed
4. Review logs alongside traces

### 4. Performance Optimization

Use traces to:
- Identify bottlenecks (which agent takes longest?)
- Reduce unnecessary LLM calls
- Cache frequently-used prompts
- Batch similar requests

## Disabling Tracing

### Temporarily Disable

In Python:
```python
from server.tools.utils.langsmith_tracer import disable_langsmith_tracing
disable_langsmith_tracing()
```

### Permanently Disable

Set environment variable:
```env
LANGSMITH_ENABLED=false
```

## Troubleshooting

### Tracing Not Appearing

1. Verify API key is correct:
   ```bash
   echo %LANGSMITH_API_KEY%  # Windows
   echo $LANGSMITH_API_KEY   # Linux/Mac
   ```

2. Check that `LANGSMITH_ENABLED=true`

3. Verify network connection to LangSmith endpoint

4. Check logs for errors:
   ```bash
   python scripts/show_metrics.py 2>&1 | grep -i langsmith
   ```

### High Token Usage

- Check if you're running multiple test runs
- Review trace payloads - are they too large?
- Consider batching requests
- Use a filtering/sampling strategy for high-volume apps

### API Key Issues

If you see "Unauthorized" errors:
1. Regenerate your API key in LangSmith settings
2. Update `.env` file
3. Restart the application

## API Reference

### Enable Tracing

```python
from server.tools.utils.langsmith_tracer import enable_langsmith_tracing

# Enable with default project name
enable_langsmith_tracing()

# Enable with custom project name
enable_langsmith_tracing("my-custom-project")
```

### Get Status

```python
from server.tools.utils.langsmith_tracer import get_langsmith_status

status = get_langsmith_status()
# {
#   'enabled': True,
#   'has_api_key': True,
#   'project': 'specbot-rag',
#   'endpoint': 'https://api.smith.langchain.com',
#   'tracing_active': True
# }
```

### Disable Tracing

```python
from server.tools.utils.langsmith_tracer import disable_langsmith_tracing

disable_langsmith_tracing()
```

## Next Steps

1. ✅ Set up API key and environment variables
2. ✅ Run a test with `python scripts/show_metrics.py`
3. ✅ View traces in LangSmith dashboard
4. ✅ Explore the execution flow and metrics
5. ✅ Set up monitoring and alerts for production

---

**Last Updated:** 2026-07-13
**Document Version:** 1.0
