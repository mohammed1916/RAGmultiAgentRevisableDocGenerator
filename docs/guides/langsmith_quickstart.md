# LangSmith Quick Start (5 minutes)

Get observability and monitoring up and running in 5 minutes.

## TL;DR - Setup in 3 Steps

### Step 1: Get API Key (2 min)
1. Go to https://smith.langchain.com/
2. Sign up or log in
3. Copy your API key from Settings → API Keys

### Step 2: Set Environment Variable (1 min)

**Windows (PowerShell):**
```powershell
$env:LANGSMITH_API_KEY = "ls_your_key_here"
$env:LANGSMITH_ENABLED = "true"
```

**Linux/Mac:**
```bash
export LANGSMITH_API_KEY="ls_your_key_here"
export LANGSMITH_ENABLED="true"
```

### Step 3: Run a Test (2 min)
```bash
# Verify setup
python scripts/verify_langsmith.py

# Run with tracing
python scripts/show_metrics.py

# View traces at: https://smith.langchain.com/
```

## What You'll See

### In Terminal:
```
[LANGSMITH] Enabled tracing
  Project: document-generation
  Endpoint: https://api.smith.langchain.com
```

### In LangSmith Dashboard:
- Real-time execution traces
- Document generation pipeline (plan → write → review → refine → generate)
- Agent inputs/outputs
- LLM calls with token counts
- Execution timing and errors

## Example: Complete Trace View

When you run `python scripts/show_metrics.py` with LangSmith enabled:

```
Document Generation Trace
├─ Session: "document-generation"
├─ Timestamp: 2026-07-13T14:30:00
├─ Run ID: abc123...
│
├─ [PLAN] Planner Agent
│  ├─ Input: "Create a 2-day study plan for Electrostatics..."
│  ├─ LLM Call: qwen3:8b
│  ├─ Tokens: 1289 completion, 1636 prompt
│  ├─ Latency: 14.2s
│  └─ Output: ExecutionPlan with 11 tasks
│
├─ [WRITE] Writer Agent
│  ├─ Input: ExecutionPlan
│  ├─ LLM Call: qwen3:8b
│  ├─ Tokens: 630 completion
│  ├─ Latency: 8.2s
│  └─ Output: Document sections
│
├─ [REVIEW] Reviewer Agent
│  ├─ Input: Generated sections
│  ├─ LLM Call: qwen3:8b
│  ├─ Latency: 20.1s
│  └─ Output: Feedback + issues found
│
├─ [REFINE] Refinement (Iteration 1)
│  ├─ Input: Feedback from reviewer
│  ├─ Writer Agent: Revise sections
│  ├─ Latency: 8.2s
│  └─ Output: Revised sections
│
└─ [GENERATE] DOCX Generation
   ├─ Input: Final sections
   ├─ Latency: 0.5s
   └─ Output: document_20260713_143000.docx
```

## Common Tasks

### Monitor Real-Time Execution

```bash
# Run generation with live tracing
python scripts/show_metrics.py

# LangSmith dashboard updates instantly - no refresh needed!
```

### Compare Different Runs

1. Run the app multiple times
2. In LangSmith, click "Compare" on the runs
3. See differences in:
   - Latency
   - Token usage
   - Agent outputs
   - Issues and feedback

### Create a Custom Project

```bash
# In Python:
from server.tools.utils.langsmith_tracer import enable_langsmith_tracing

# Create project for specific experiment
enable_langsmith_tracing("my-custom-experiment")
```

Or set environment variable:
```bash
export LANGSMITH_PROJECT="my-custom-experiment"
```

### Disable Tracing (Keep Running)

```python
from server.tools.utils.langsmith_tracer import disable_langsmith_tracing
disable_langsmith_tracing()
```

### Check Status Programmatically

```python
from server.tools.utils.langsmith_tracer import get_langsmith_status

status = get_langsmith_status()
if status['tracing_active']:
    print("Tracing is active!")
    print(f"Project: {status['project']}")
```

## Debugging Guide

### Trace Not Appearing?

1. **Check if enabled:**
   ```bash
   python scripts/verify_langsmith.py
   ```
   Should show `[OK] Connected to LangSmith API`

2. **Verify API key:**
   ```bash
   # Windows
   echo %LANGSMITH_API_KEY%
   
   # Linux/Mac
   echo $LANGSMITH_API_KEY
   ```

3. **Check logs:**
   ```bash
   python scripts/show_metrics.py 2>&1 | grep -i langsmith
   ```

### Want to See Intermediate Steps?

LangSmith shows all LLM calls and agent steps. Just click on any span in the trace to expand it.

### Comparing Performance?

Use the "Compare" feature in LangSmith to see:
- Which run was faster?
- Which used fewer tokens?
- Where did quality degrade?

## Costs & Pricing

- **First 100 traces:** Free
- **Overage:** See https://smith.langchain.com/pricing
- **Tip:** Use a project name like `specbot-rag-test` for development, keep production separate

## Next Steps

✅ **Just got started?**
- Run: `python scripts/verify_langsmith.py`
- Run: `python scripts/show_metrics.py`
- Open: https://smith.langchain.com/

📊 **Want to optimize?**
- Read full guide: [LangSmith Setup Guide](langsmith_setup.md)
- Check token usage in traces
- Compare runs to find performance bottlenecks

🔍 **Need help?**
- See [Troubleshooting](langsmith_setup.md#troubleshooting) section
- Check [API Reference](langsmith_setup.md#api-reference)

---

**Document:** LangSmith Quick Start  
**Last Updated:** 2026-07-13  
**Time to Complete:** 5 minutes
