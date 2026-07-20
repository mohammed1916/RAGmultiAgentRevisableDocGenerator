# AI Learning Operating System
## 06 - AI Engine, Agent Architecture & Context Planning

---

# Overview

Large Language Models are not the system.

They are one component inside a much larger AI architecture.

Instead of asking the LLM every question directly, the platform first determines

- who the user is
- what profile is active
- what they are currently studying
- what documents are relevant
- what memories should be recalled
- what planner information matters
- which tools are required

Only then is the final context constructed.

The AI engine acts as an intelligent operating system for multiple AI models and specialized agents.

---

# AI Request Lifecycle

```
User Query

↓

Profile Detection

↓

Intent Detection

↓

Context Planner

↓

Tool Selection

↓

Agent Selection

↓

Memory Retrieval

↓

Hybrid Retrieval

↓

Knowledge Graph

↓

Planner Context

↓

Prompt Builder

↓

LLM

↓

Post Processing

↓

Memory Update

↓

Planner Update

↓

Analytics
```

The LLM is never called directly.

---

# AI Gateway

The AI Gateway is the central entry point for every AI request.

Responsibilities

- authentication
- model routing
- prompt generation
- tool execution
- streaming
- structured outputs
- retries
- logging
- token accounting

Everything passes through the gateway.

---

# Context Planner

The Context Planner determines what information is required before calling the model.

Instead of blindly retrieving every document, it asks

```
Does this need notes?

Does this need PDFs?

Does this need memory?

Does this need planner?

Does this need internet?

Does this need previous conversation?

Does this need knowledge graph?

Does this need analytics?
```

The planner then constructs the minimum useful context.

---

# Context Sources

The planner can retrieve context from

```
Documents

↓

Notes

↓

Conversations

↓

Planner

↓

Memory

↓

Knowledge Graph

↓

Analytics

↓

Calendar

↓

Internet (optional)
```

Each source contributes independently.

---

# Prompt Construction Pipeline

```
User Question

↓

Intent

↓

Retrieved Context

↓

Memory

↓

Planner

↓

System Instructions

↓

Tools

↓

Conversation History

↓

Prompt Assembly

↓

LLM
```

Prompt construction should remain deterministic and inspectable.

---

# Intent Detection

Every request is classified before execution.

Example intents

- Question Answering
- Summarization
- Note Generation
- Flashcard Generation
- Quiz Creation
- Revision Planning
- Document Editing
- Interview Preparation
- Code Explanation
- Code Generation
- Research
- Comparison
- Translation

Intent determines which agents and tools are activated.

---

# Model Routing

Different tasks require different models.

Examples

| Task                | Preferred Model                 |
| ------------------- | ------------------------------- |
| Reasoning           | GPT-5.5                         |
| Fast Q&A            | GPT-5.5 Mini                    |
| Embeddings          | text-embedding-3-large / BGE-M3 |
| OCR                 | PaddleOCR                       |
| Speech              | Whisper                         |
| Image Understanding | GPT Vision                      |

The router should remain configurable.

---

# Agent Architecture

Rather than one monolithic assistant, the system uses specialized agents.

```
User

↓

Router

↓

Planner Agent

Retriever Agent

Memory Agent

Writing Agent

Quiz Agent

Revision Agent

Research Agent

Analytics Agent

↓

Coordinator

↓

Final Response
```

Agents communicate through structured messages.

---

# Planner Agent

Responsibilities

- build study plans
- estimate workload
- prioritize tasks
- reschedule missed work
- predict completion

Inputs

- progress
- exam date
- available hours
- memory
- confidence

Outputs

- daily plan
- weekly plan
- reminders

---

# Retriever Agent

Responsible for

- metadata filtering
- hybrid retrieval
- reranking
- citations
- context compression

It never generates answers.

Its only responsibility is retrieving evidence.

---

# Memory Agent

Responsibilities

- retrieve memories
- summarize conversations
- update preferences
- identify weak concepts
- forget obsolete memories
- merge duplicates

Memory should evolve continuously.

---

# Writing Agent

Responsibilities

- generate notes
- rewrite notes
- simplify content
- improve grammar
- create summaries
- generate reports

---

# Quiz Agent

Responsibilities

Generate

- MCQs
- coding questions
- short answers
- essay questions
- interview questions
- flashcards

Questions should align with the user's current mastery.

---

# Revision Agent

Responsibilities

- determine review schedule
- integrate FSRS
- detect forgotten concepts
- schedule practice
- estimate retention

---

# Research Agent

Responsibilities

- compare sources
- summarize research papers
- identify contradictions
- generate literature reviews
- recommend additional reading

---

# Analytics Agent

Responsibilities

Analyze

- learning velocity
- consistency
- confidence trends
- planner effectiveness
- retrieval quality
- AI usage

Generate recommendations automatically.

---

# Agent Communication

Agents communicate using structured messages.

Example

```
Retriever

↓

Context

↓

Memory

↓

Planner

↓

Writer

↓

LLM
```

Agents should never share internal state directly.

---

# Tool Calling

Agents can invoke tools.

Examples

- document search
- internet search
- calculator
- code execution
- planner
- filesystem
- OCR
- PDF parsing
- markdown parser

Tool outputs become additional context.

---

# Structured Outputs

Every agent returns structured objects.

Example

```json
{
  "intent": "quiz_generation",
  "confidence": 0.98,
  "retrieval_needed": true,
  "memory_needed": false,
  "planner_needed": true,
  "tools": [
    "retriever",
    "planner"
  ]
}
```

Structured outputs reduce hallucinations.

---

# Conversation State

Each conversation maintains state.

```
Conversation

↓

Messages

↓

Retrieved Context

↓

Memory

↓

Planner State

↓

Agent Outputs
```

State enables long-running workflows.

---

# Token Budget Management

The Context Planner should manage token usage.

Priority order

1. System Prompt
2. User Query
3. Retrieved Context
4. Memory
5. Planner
6. Conversation History
7. Analytics

If the token limit is exceeded

- compress context
- summarize history
- remove redundant chunks

Never truncate the user's question.

---

# Context Compression

Compression pipeline

```
Retrieved Chunks

↓

Remove Duplicates

↓

Merge Similar Sections

↓

Summarize

↓

Preserve Citations

↓

Prompt
```

Compression should preserve factual content.

---

# Memory Update Pipeline

After every response

```
Conversation

↓

Summarization

↓

Extract Preferences

↓

Detect Weak Topics

↓

Update Memory

↓

Update Planner

↓

Update Knowledge Graph
```

The AI learns continuously.

---

# Personalization

The AI should adapt to

- learning style
- preferred explanation depth
- language
- difficulty
- pace
- exam type
- coding proficiency

Responses should become increasingly personalized over time.

---

# Hallucination Prevention

Before answering

```
Evidence Available?

↓

Yes

↓

Answer with citations

↓

No

↓

Request clarification or state uncertainty
```

The model should never invent educational facts.

---

# Response Pipeline

```
LLM Output

↓

Validate Structure

↓

Verify Citations

↓

Apply Formatting

↓

Generate References

↓

Store Conversation

↓

Update Memory

↓

Return Response
```

---

# Multi-Agent Workflow Example

```
User

↓

"I forgot Electrostatics."

↓

Planner Agent

↓

Find current syllabus

↓

Retriever Agent

↓

Retrieve notes

↓

Memory Agent

↓

Identify forgotten concepts

↓

Revision Agent

↓

Schedule review

↓

Writing Agent

↓

Generate summary

↓

Quiz Agent

↓

Create practice questions

↓

Final Response
```

The user receives not only an explanation, but also a personalized revision plan and quiz.

---

# Long-Running Tasks

Some workflows execute asynchronously.

Examples

- generate 500 flashcards
- summarize an entire book
- build a knowledge graph
- generate interview preparation
- process large document collections

These tasks should execute through background workers.

---

# AI Design Principles

The AI subsystem should satisfy

✓ Retrieval-first

✓ Memory-aware

✓ Planner-aware

✓ Tool-augmented

✓ Multi-agent

✓ Event-driven

✓ Profile-aware

✓ Token-efficient

✓ Citation-based

✓ Extensible

The objective is not simply to answer questions, but to behave as an intelligent learning companion that continuously reasons about the user's goals, remembers their progress, plans future work, and coordinates specialized agents to provide the most useful assistance.