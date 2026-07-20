# Adaptive Learning Agent - Future Implementation Plan (not now)

## Current State Analysis

### What Already Exists ✅
1. **Data Models** (in `server/base/models.py`):
   - `StudentState` — tracks learned topics, exam deadlines, available hours/day
   - `StudyPlan` — structured plan with topics, daily load, feasibility flags
   - `ProgressClaim` / `ProgressUpdate` — for parsing user progress statements
   - `TopicProgress` — tracks confidence per topic

2. **Agents** (in `server/agents/`):
   - `StateAwarePlanner` — generates plans respecting student progress
   - `WriterAgent` — already integrated with RetrievalOrchestrator
   - `ReviewerAgent` — reviews generated content
   - `ProgressExtractor` (in tools) — parses progress from user input

3. **Retrieval Layer** (just integrated):
   - `RetrievalOrchestrator` — intelligent collection routing, metadata filtering
   - Configuration-driven collection registry (no hardcoded names)
   - `CollectionMetadata` with logical↔physical name mapping

4. **Chat Layer**:
   - Chat API and ChatOrchestrator for conversation management
   - ChatContext model for tracking conversation state

### What's Missing ❌

1. **Learning Memory Persistence**:
   - StudentState exists in memory but not persisted
   - No student profile storage
   - No learning history database
   - No weak area tracking per student

2. **Plan Refinement Mechanism**:
   - No ability to update existing plans
   - No feedback acceptance from users
   - No plan version history
   - No "refine" endpoint in API

3. **Learning Evaluation Agent**:
   - No progress evaluation after practice
   - No weak area identification
   - No feedback loop to update StudentState

4. **Integration**:
   - StateAwarePlanner not connected to main orchestrator
   - No learning memory lifecycle (create → store → retrieve → update)
   - Chat layer doesn't track StudentState between conversations

---

## Proposed Architecture

```
User Input (Goal + Context)
    ↓
[Chat Layer] - Clarify & Contextualize
    ↓
[Learning Memory Service] - Retrieve StudentState (or create new)
    ↓
[Learning Planner Agent] - Generate StudyPlan (state-aware)
    ↓
[Plan Repository] - Persist & version plans
    ↓
[Presentation] - Show plan to user
    ↓
[Refinement Loop] ← User feedback
    ↓ (update & re-plan)
[Plan Repository] - Version updated plan
    ↓
[Retrieval Agent] - Fetch study materials per topic
    ↓
[Learning Evaluation Agent] - Track progress
    ↓
[Memory Update] - Update StudentState with learned topics
    ↓
[Future Plans] - Next planning uses updated state
```

---

## Implementation Plan (Phase 1-3)

### Phase 1: Learning Memory (Storage Layer)
**Goal:** Persist student state and learning history

**Files to Create:**
- `server/storage/learning_memory.py` — StudentState CRUD operations
- `server/storage/plan_repository.py` — StudyPlan versioning & retrieval
- `server/storage/models.py` — Database models (SQLAlchemy or similar)
- `server/storage/__init__.py` — Public API

**Files to Modify:**
- `server/base/models.py` — Add LearningMemoryEntry, PlanVersion models

**Tasks:**
1. Choose persistence layer (SQLite, PostgreSQL, or file-based JSON)
2. Implement StudentState CRUD
3. Implement StudyPlan versioning (keep history)
4. Add query methods:
   - `get_student_state(student_id)` → StudentState
   - `save_study_plan(student_id, plan)` → PlanVersion
   - `get_latest_plan(student_id)` → StudyPlan
   - `update_learned_topics(student_id, topics)` → None

**Acceptance Criteria:**
- StudentState persists across sessions
- Plans are versioned (can view/revert to previous plans)
- Unit tests for CRUD operations

---

### Phase 2: Plan Refinement Loop
**Goal:** Accept user feedback and update existing plans

**Files to Create:**
- `server/agents/plan_refiner.py` — Refines existing plans based on feedback
- `server/api/refinement_routes.py` — API endpoints for refinement

**Files to Modify:**
- `server/api/routes.py` — Add refinement endpoint
- `server/core/orchestrators/learning.py` — New orchestrator for learning flow
- `server/base/models.py` — Add RefinementRequest, RefinementFeedback models

**Tasks:**
1. Create `RefinementRequest` model:
   ```python
   - student_id: str
   - current_plan_id: str
   - feedback: str  # "Reduce theory", "Add practice", "Only 1h/day"
   - context: Optional[Dict]
   ```

2. Implement `PlanRefiner` agent:
   - Takes: current plan + feedback
   - Parses feedback intent
   - Updates plan attributes (daily_load, theory_ratio, practice_ratio)
   - Regenerates topic sequence if needed
   - Returns: updated StudyPlan

3. Add API endpoint: `POST /refinement`
   - Accepts RefinementRequest
   - Calls PlanRefiner
   - Saves new version via LearningMemory
   - Returns updated plan

4. Update chat flow:
   - After plan generation, accept refinement queries
   - Don't start a completely new plan; refine existing one

**Acceptance Criteria:**
- User can ask: "Reduce theory sections" → plan updates
- User can ask: "I only have 1h/day" → daily_load adjusts
- Previous plans remain in history
- Refined plan reuses structure (just adjusts proportions)

---

### Phase 3: Learning Evaluation & Feedback Loop
**Goal:** Track progress and update student state

**Files to Create:**
- `server/agents/learning_evaluator.py` — Evaluates student progress after practice
- `server/agents/weak_area_detector.py` — Identifies topics needing more work
- `server/storage/progress_tracker.py` — Records completion + scores

**Files to Modify:**
- `server/api/routes.py` — Add progress tracking endpoint
- `server/base/models.py` — Add CompletionRecord, EvaluationResult models

**Tasks:**
1. Create progress tracking workflow:
   - Student completes a topic/section
   - System evaluates: quiz score, time spent, quality of answer
   - Updates StudentState.learned_topics[topic].confidence
   - Flags weak areas if confidence < threshold

2. Implement `LearningEvaluator`:
   - Takes: student_id, topic, completion_evidence (score, time, etc.)
   - Validates completion
   - Updates StudentState via LearningMemory
   - Returns: ProgressUpdate

3. Weak area detection:
   - After evaluation, check for topics with confidence < 0.6
   - Add to StudentState.weak_areas
   - Next plan should emphasize these topics

**Acceptance Criteria:**
- Progress tracking records persist
- StudentState automatically updates after completion
- Weak areas automatically flagged
- Next plan generation uses updated weak_areas

---

## File Structure Summary

```
server/
├── storage/ [NEW]
│   ├── __init__.py
│   ├── learning_memory.py      (StudentState CRUD)
│   ├── plan_repository.py       (StudyPlan versioning)
│   ├── progress_tracker.py      (Completion records)
│   └── models.py                (DB models)
│
├── agents/
│   ├── state_aware_planner.py   [MODIFY] Connect to LearningMemory
│   ├── plan_refiner.py          [NEW]
│   ├── learning_evaluator.py    [NEW]
│   └── weak_area_detector.py    [NEW]
│
├── core/orchestrators/
│   ├── learning.py              [NEW] Orchestrate learning flow
│   └── base.py                  [MODIFY] Add learning orchestrator
│
├── api/
│   ├── routes.py                [MODIFY] Add refinement + progress endpoints
│   └── refinement_routes.py      [NEW]
│
└── base/
    └── models.py                [MODIFY] Add new models
```

---

## Key Design Decisions

### 1. Separation of Concerns
- **LearningMemory**: Only persistence (CRUD)
- **StateAwarePlanner**: Only planning (uses memory, not updates it)
- **PlanRefiner**: Only updates (doesn't re-plan from scratch)
- **LearningEvaluator**: Only evaluation (doesn't plan or persist directly)

### 2. Dependency Injection
```python
# Instead of:
planner = StateAwarePlanner()  # Hardcoded dependency on Ollama

# Do this:
planner = StateAwarePlanner(
    ollama_client=llm_client,
    memory=learning_memory,
    retrieval_orchestrator=retriever
)
```

### 3. Immutable Plans
- StudyPlan should be frozen after creation
- Refinement creates a new version, not modifies existing
- Plan history is queryable

### 4. No Hardcoded Collection Names
- Already done via RetrievalOrchestrator + CollectionRegistry
- Refinement agent uses same registry

---

## Success Metrics

**Phase 1 Complete When:**
- [ ] StudentState persists across 5+ sessions
- [ ] Plans are versioned with timestamps
- [ ] Can retrieve student history

**Phase 2 Complete When:**
- [ ] User feedback updates plans without regeneration
- [ ] Refinement takes <5 seconds
- [ ] Plan versions align with feedback

**Phase 3 Complete When:**
- [ ] Progress tracking records 100+ completions
- [ ] Weak areas auto-detect after 3 evaluations
- [ ] Next plan emphasizes weak areas

---

## Risk Mitigation

| Risk               | Mitigation                                           |
| ------------------ | ---------------------------------------------------- |
| Data loss          | Regular backups, use persistent DB (not memory)      |
| Over-fragmentation | Version limit (keep last 10 plans per student)       |
| Evaluation gaming  | Score validation, time-vs-score anomaly detection    |
| Tight coupling     | All agents use interfaces (LLMClient, StorageClient) |

---

## Next Steps

1. **Approve** this plan (or request changes)
2. **Phase 1**: Implement learning memory persistence
3. **Phase 2**: Implement plan refinement
4. **Phase 3**: Implement evaluation & feedback loop
5. **Integration**: Connect to chat layer
6. **Testing**: Unit tests + E2E flow

**Estimated Timeline:**
- Phase 1: 2-3 hours (storage + CRUD)
- Phase 2: 2-3 hours (refinement agent + endpoints)
- Phase 3: 3-4 hours (evaluation + feedback)
- Integration: 2 hours
- **Total: ~9-12 hours**

---

