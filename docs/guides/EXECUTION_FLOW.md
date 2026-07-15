# Execution Flow: Client & Server with Code Snippets

## Overview: From User Input to Generated Document

```
User Input → Chat Flow → Information Collection → Document Generation → DOCX Output
  (Client)    (Client+Server)    (LLM Loop)          (Multi-Agent)      (File)
```

---

## 1. CHAT INITIALIZATION: User Sends Initial Request

### Client Side: `client/app.js`

**User types in chat input and hits Send:**

```javascript
// client/app.js - Line 74-87
async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message || isWaiting) return;

    if (!currentChatContext) {
        // Initial message - start chat
        await startChat(message);
    } else {
        // Answer to a question
        await answerQuestion(message);
    }

    chatInput.value = '';
}
```

**Calls startChat() which sends POST request:**

```javascript
// client/app.js - Line 92-130
async function startChat(initialRequest) {
    isWaiting = true;
    try {
        addChatMessage('user', initialRequest);
        showTyping();

        const response = await fetch(`${api.baseURL}/chat/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request: initialRequest })
        });

        if (!response.ok) throw new Error('Failed to start chat');
        const data = await response.json();

        removeTyping();
        addChatMessage('assistant', data.message);

        currentChatContext = data.context;
        currentSessionId = data.session_id;

        // Calculate progress from conversation length
        const progress = calculateProgress(data.context);
        updateProgress(progress);  // Updates progress bar
        progressSection.style.display = 'block';

        // If LLM has more questions, display them
        if (data.questions && data.questions.length > 0) {
            displayChatQuestions(data.questions);
        }

        // If LLM says [READY], show generate button
        if (data.is_ready_to_generate) {
            showGenerateButton();
        }
    } finally {
        isWaiting = false;
    }
}
```

---

### Server Side: `server/api.py` → `/chat/start` endpoint

**Receives user's initial request:**

```python
# server/api.py - Line 236-261
@app.post("/chat/start")
async def start_chat(request: DocumentRequest) -> ChatResponse:
    """Start a new chat conversation for document generation."""
    logger.info(f"Starting chat: {request.request[:100]}...")

    try:
        # Create ChatOrchestrator and send initial request
        response = chat_orchestrator.start_conversation(request.request)

        # Generate unique session ID
        import uuid
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = response.context

        # Add session_id to response
        response.session_id = session_id
        return response
    except Exception as e:
        logger.error(f"Chat start failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Delegates to ChatOrchestrator:**

```python
# server/chat_orchestrator.py - Line 61-97
def start_conversation(self, request: str) -> ChatResponse:
    """Start conversation - LLM responds to initial request."""
    logger.info(f"Starting conversation: {request[:100]}...")

    context = ChatContext(initial_request=request)
    context.conversation.append(ChatMessage(role="user", content=request))

    # LLM generates the first response
    response_text = self._llm_respond(context)
    context.conversation.append(ChatMessage(role="assistant", content=response_text))

    # Check if LLM determined we're ready
    is_ready = self._check_if_ready(context)

    # Update context.is_ready_to_generate so it's included in response
    context.is_ready_to_generate = is_ready

    return ChatResponse(
        message=response_text,
        session_id=None,  # Set by API
        questions=None if is_ready else [ClarifyingQuestion(
            question="Your response:",
            key="user_input",
            options=None,
            required=True,
        )],
        context=context,
        is_ready_to_generate=is_ready,
        next_action="ready_to_generate" if is_ready else "ask_more",
    )
```

### LLM Call Inside ChatOrchestrator

```python
# server/chat_orchestrator.py - Line 153-196
def _llm_respond(self, context: ChatContext) -> str:
    """LLM generates the next response - includes decision making."""
  
    # Build messages for chat API with system prompt
    messages = [
        {"role": "system", "content": self.SYSTEM_PROMPT},
    ]

    # Add conversation history
    messages.extend([
        {"role": msg.role, "content": msg.content}
        for msg in context.conversation[-10:]  # Last 10 messages
    ])

    # Add context reminder
    context_msg = f"""Current learned context:
- Subject: {context.answers.get('subject', 'Not yet mentioned')}
- Topics: {context.answers.get('topics', 'Not yet mentioned')}
- Deadline: {context.answers.get('deadline', 'Not yet mentioned')}

Generate the NEXT assistant response now."""

    messages.append({"role": "user", "content": context_msg})

    try:
        # Call Cloud Ollama
        result = self.llm_client.chat(messages)
        response_text = result.get("message", {}).get("content", "").strip()

        if not response_text:
            logger.error("Empty response from LLM")
            return "I had trouble processing that..."

        logger.info(f"LLM generated response: {response_text[:100]}...")
        return response_text
    except Exception as e:
        logger.error(f"LLM response failed: {e}")
        return f"I had trouble processing that..."
```

### System Prompt (LLM Instructions)

```python
# server/chat_orchestrator.py - Line 26-53
SYSTEM_PROMPT = """You are an intelligent study scheduling agent. 
Your role is to conduct a natural conversation to help students prepare for exams.

CONVERSATION FLOW (LLM decides all transitions):
1. Initial: Understand what student is studying (subject/exam)
2. Information Gathering: Learn about their topics and deadline
3. Planning: Create a personalized study schedule
4. Confirmation: Let student review and proceed

KEY RULES:
- Generate ALL assistant messages yourself - never ask user directly
- Analyze what user knows vs doesn't know
- If user is vague/uncertain, you decide to fetch curriculum details and recommend
- If user is clear, proceed with their answer
- Use natural language - make it a real conversation
- Track: subject, topics, deadline (store in context as you learn them)
- When you have subject + topics + deadline, you're ready to generate schedule

STATE INDICATORS (in your message):
- [GATHERING] - collecting information
- [RECOMMENDING] - suggesting topics from curriculum
- [READY] - have all info, ready to generate schedule
"""
```

---

## 2. CONVERSATION LOOP: User Answers Questions

### Client Side: Answer Question

```javascript
// client/app.js - Line 135-167
async function answerQuestion(answer) {
    isWaiting = true;
    try {
        addChatMessage('user', answer);
        showTyping();

        // Send answer to server
        const response = await fetch(
            `${api.baseURL}/chat/answer?session_id=${currentSessionId}&question_key=${currentQuestionKey}&answer=${encodeURIComponent(answer)}`,
            { method: 'POST' }
        );

        if (!response.ok) throw new Error('Failed to answer question');
        const data = await response.json();

        removeTyping();
        addChatMessage('assistant', data.message);

        currentChatContext = data.context;
      
        // Update progress bar: 20% per message
        const progress = calculateProgress(data.context);
        updateProgress(progress);

        // Check if ready to generate
        if (data.is_ready_to_generate) {
            updateProgress(1.0); // 100% when ready
            showGenerateButton();
        } else if (data.questions && data.questions.length > 0) {
            displayChatQuestions(data.questions);
        }
    } finally {
        isWaiting = false;
    }
}

// Calculate progress: 20% per user message (max 100%)
function calculateProgress(context) {
    if (!context || !context.conversation) return 0;
    const messageCount = context.conversation.filter(msg => msg.role === 'user').length;
    const progress = Math.min(1.0, messageCount * 0.2);
    return progress;
}
```

### Server Side: `/chat/answer` endpoint

```python
# server/api.py - Line 264-293
@app.post("/chat/answer")
async def answer_question(
    session_id: str,
    question_key: str,
    answer: str,
) -> ChatResponse:
    """Answer a clarifying question in the chat."""
    logger.info(f"Processing chat answer: {question_key}={answer[:50]}")

    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    try:
        context = chat_sessions[session_id]
        response = chat_orchestrator.add_answer(context, question_key, answer)
        chat_sessions[session_id] = response.context  # Update session
        response.session_id = session_id
        return response
    except Exception as e:
        logger.error(f"Chat answer failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**ChatOrchestrator processes the answer:**

```python
# server/chat_orchestrator.py - Line 99-151
def add_answer(self, context: ChatContext, question_key: str, answer: str) -> ChatResponse:
    """Process user's answer - LLM decides everything."""
    logger.info(f"User answered: {answer[:100]}...")

    # Add user message to conversation
    context.conversation.append(ChatMessage(role="user", content=answer))

    # LLM generates the ENTIRE next response
    # LLM will decide: what to ask, whether to fetch RAG, what to recommend
    response_text = self._llm_respond(context)
    context.conversation.append(ChatMessage(role="assistant", content=response_text))

    # Extract context from LLM response
    self._extract_context_from_response(response_text, context)

    # Check if LLM indicated it's ready
    is_ready = self._check_if_ready(context)

    # Update context.is_ready_to_generate
    context.is_ready_to_generate = is_ready

    if is_ready:
        return ChatResponse(
            message=response_text,
            session_id=None,
            questions=None,
            context=context,
            is_ready_to_generate=True,
            next_action="ready_to_generate",
        )
    else:
        return ChatResponse(
            message=response_text,
            session_id=None,
            questions=[ClarifyingQuestion(
                question="Continue:",
                key="user_input",
                options=None,
                required=True,
            )],
            context=context,
            is_ready_to_generate=False,
            next_action="ask_more",
        )

def _check_if_ready(self, context: ChatContext) -> bool:
    """Check if LLM indicated we have everything needed."""
    if context.conversation:
        last_response = context.conversation[-1].content
        return "[READY]" in last_response  # LLM marks with [READY] tag
```

---

## 3. DOCUMENT GENERATION: User Clicks Generate Button

### Client Side: Send to Document Generation

```javascript
// client/app.js - Line 219-260
async function generateDocument() {
    isWaiting = true;
    try {
        addChatMessage('assistant', ' Generating your document...');
        showTyping();

        // Send chat context to backend for document generation
        const response = await fetch(`${api.baseURL}/chat/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                context: currentChatContext  // Pass the whole conversation context
            })
        });

        if (!response.ok) throw new Error('Failed to generate document');
        const data = await response.json();

        removeTyping();
        addChatMessage('assistant',
            `✓ Document created!\n\n📄 ${data.document_filename}\n\nQuality: ${data.quality_scores.overall}/5`
        );

        // Show download + refine buttons
        chatQuestionsArea.innerHTML = `
            <div style="display: flex; gap: 12px;">
                <a href="${api.baseURL}/download/${data.document_filename}"
                   class="btn btn-success"
                   style="flex: 1; text-align: center; text-decoration: none; padding: 12px; display: block;">
                     Download
                </a>
                <button class="btn btn-secondary" style="flex: 1; padding: 12px;" onclick="startRefinement()">
                     Refine
                </button>
            </div>
        `;

        // Refresh documents list
        await loadDocuments();
    } finally {
        isWaiting = false;
    }
}
```

### Server Side: `/chat/generate` endpoint

```python
# server/api.py - Line 302-351
@app.post("/chat/generate")
async def generate_from_chat(req: GenerateFromChatRequest) -> DocumentResponse:
    """Generate document from completed chat context using multi-agent orchestration."""
    logger.info(f"Generating document from chat: {req.session_id}")
    logger.info(f"Context ready: {req.context.is_ready_to_generate}")

    if not req.context.is_ready_to_generate and len(req.context.conversation) == 0:
        raise HTTPException(
            status_code=400,
            detail="Chat context not ready for generation. Have a conversation first."
        )

    try:
        # Build comprehensive prompt from chat context
        prompt = chat_orchestrator.get_generation_prompt(req.context)

        # Create document request
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": req.session_id,
                "chat_history": len(req.context.conversation),
                "source": "chat_orchestrator",
            }
        )

        logger.info(f"Calling multi-agent orchestrator for document generation...")

        # Generate document using multi-agent pipeline
        response = orchestrator.generate_document(doc_request)

        logger.info(f"Document generated successfully: {response.document_filename}")
        return response

    except Exception as e:
        logger.error(f"Document generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")
```

---

## 3.5 REFINEMENT: User Refines Generated Document

### Client Side: Refinement Flow

**User clicks "Refine" button after generation:**

```javascript
// client/app.js - startRefinement()
function startRefinement() {
    // Collapse chat history
    chatMessages.style.display = 'none';
    progressSection.style.display = 'none';

    // Create toggle button
    const collapseBtn = document.createElement('button');
    collapseBtn.id = 'toggleChatBtn';
    collapseBtn.textContent = ' Show Previous Conversation';
    collapseBtn.onclick = toggleChatHistory;
    chatMessages.parentNode.insertBefore(collapseBtn, chatMessages);

    // Show refinement input
    chatQuestionsArea.innerHTML = `
        <div style="padding: 16px; background: #f9f9f9; border-radius: 6px;">
            <label style="display: block; margin-bottom: 8px; font-weight: 600;">How would you like to refine this document?</label>
            <div style="display: flex; gap: 8px;">
                <textarea
                    id="refinementInput"
                    placeholder="e.g., 'Add more examples' or 'Make it shorter'"
                    rows="3"
                    style="flex: 1; padding: 10px; border: 2px solid #dee2e6; border-radius: 6px;"
                ></textarea>
                <button class="btn btn-primary" onclick="submitRefinement()">Submit</button>
            </div>
        </div>
    `;

    document.getElementById('refinementInput').focus();
}

// Toggle previous chat visibility
function toggleChatHistory() {
    const isHidden = chatMessages.style.display === 'none';
    if (isHidden) {
        chatMessages.style.display = 'block';
        progressSection.style.display = 'block';
        document.getElementById('toggleChatBtn').textContent = ' Hide Previous Conversation';
    } else {
        chatMessages.style.display = 'none';
        progressSection.style.display = 'none';
        document.getElementById('toggleChatBtn').textContent = ' Show Previous Conversation';
    }
}

// Submit refinement request
async function submitRefinement() {
    const refinement = document.getElementById('refinementInput').value.trim();
    if (!refinement || isWaiting) return;

    isWaiting = true;
    try {
        addChatMessage('user', refinement);
        showTyping();

        // Send refinement to backend
        const response = await fetch(`${api.baseURL}/chat/refine`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                refinement_request: refinement,
                context: currentChatContext
            })
        });

        if (!response.ok) throw new Error('Failed to refine document');
        const data = await response.json();

        removeTyping();
        addChatMessage('assistant', data.message || '✓ Document refined and regenerated.');
        currentChatContext = data.context;

        // Show refinement option again or download
        if (data.is_ready_to_generate) {
            showRefinementOption();
        }
    } catch (error) {
        console.error('Error:', error);
        removeTyping();
        addChatMessage('assistant', '[ERROR] ' + error.message);
    } finally {
        isWaiting = false;
    }
}
```

### Server Side: `/chat/refine` endpoint

**NEW endpoint for document refinement:**

```python
# server/api.py - Line 354-404
@app.post("/chat/refine")
async def refine_document(req: GenerateFromChatRequest) -> DocumentResponse:
    """Refine an already-generated document based on user feedback.

    Takes a refinement request and re-generates the document with the updated requirements.

    Args:
        req: Request with session ID, context, and refinement request

    Returns:
        Updated DocumentResponse with refined document
    """
    logger.info(f"Refining document from chat: {req.session_id}")

    if req.session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    try:
        context = chat_sessions[req.session_id]

        # Add refinement request to conversation context
        if not hasattr(context, 'refinement_requests'):
            context.refinement_requests = []
        context.refinement_requests.append(req.refinement_request)

        # Build refined prompt from chat context + refinement request
        prompt = chat_orchestrator.get_generation_prompt(context)
        prompt += f"\n\n[REFINEMENT REQUEST]: {req.refinement_request}"

        # Create document request with context
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": req.session_id,
                "chat_history": len(context.conversation),
                "refinement_request": req.refinement_request,
                "source": "chat_refinement",
            }
        )

        logger.info(f"Calling orchestrator for document refinement...")

        # Generate refined document using multi-agent pipeline
        response = orchestrator.generate_document(doc_request)

        logger.info(f"Document refined successfully: {response.document_filename}")

        # Update session context
        chat_sessions[req.session_id] = context

        # Return response with refinement message
        return DocumentResponse(
            success=True,
            document_filename=response.document_filename,
            request=prompt,
            message=f"✓ Document refined based on: {req.refinement_request}"
        )

    except Exception as e:
        logger.error(f"Document refinement failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document refinement failed: {str(e)}")
```

---

## 4. MULTI-AGENT PIPELINE: Document Generation

### Server Side: Orchestrator Main Flow

```python
# server/orchestrator.py - Line 43-161
def generate_document(self, doc_request: DocumentRequest) -> DocumentResponse:
    """Generate a complete document from a request."""
    logger.info(f"Starting document generation: {doc_request.request[:100]}...")
    self.metrics.start_pipeline()

    try:
        # PHASE 1: Planning
        logger.info("=" * 50)
        logger.info("PHASE 1: Planning")
        logger.info("=" * 50)
        plan_start = time.time()
        plan = self.planner.plan(doc_request.request)
        plan_latency = (time.time() - plan_start) * 1000
        self.metrics.record_planner_execution(plan_latency, len(plan.tasks))

        # PHASE 2: Writing
        logger.info("=" * 50)
        logger.info("PHASE 2: Writing Document")
        logger.info("=" * 50)
        write_start = time.time()
        sections = self.writer.write_all_sections(doc_request.request, plan)
        write_latency = (time.time() - write_start) * 1000
        self.metrics.record_writer_execution(write_latency)

        # PHASE 3: Review (skip for todo lists)
        review_iterations = 0
        if plan.document_type.lower() == "todo list":
            logger.info("Skipping review for todo list - simple format doesn't need iteration")
        else:
            logger.info("=" * 50)
            logger.info("PHASE 3: Review & Iterative Refinement")
            logger.info("=" * 50)
            review_start = time.time()

            for iteration in range(1, config.max_review_iterations + 1):
                logger.info(f"Review iteration {iteration}")
                feedback = self.reviewer.review_document(plan.document_type, sections)

                if not feedback.has_issues:
                    logger.info("Review passed - no issues found ✓")
                    break
                else:
                    logger.warning(f"Issues found - refining document...")
                    review_iterations = iteration

                    if iteration < config.max_review_iterations:
                        logger.info(f"Fixing {len(feedback.section_feedback)} sections with issues...")
                        sections = self._refine_sections(
                            doc_request.request, plan, sections, feedback
                        )

            review_latency = (time.time() - review_start) * 1000
            self.metrics.record_reviewer_execution(review_latency, review_iterations)

        # PHASE 4: DOCX Generation
        logger.info("=" * 50)
        logger.info("PHASE 4: DOCX Generation")
        logger.info("=" * 50)
        docx_start = time.time()

        structure = DocumentStructure(
            title=plan.document_type,
            sections=sections,
        )

        self.docx_generator.from_structure(structure)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"document_{timestamp}.docx"
        filepath = os.path.join(config.document_output_dir, filename)

        document_path = self.docx_generator.save(filepath)
        docx_latency = (time.time() - docx_start) * 1000

        # Build response
        response = DocumentResponse(
            success=True,
            document_filename=filename,
            execution_plan=plan,
            assumptions=plan.assumptions,
            metrics=pipeline_metrics,
            quality_scores=quality_scores,
            message="Document generated successfully",
        )

        logger.info("=" * 50)
        logger.info("DOCUMENT GENERATION COMPLETE")
        logger.info("=" * 50)
        return response
```

### PHASE 1: Planner Agent

```python
# server/agents/planner.py - Line 26-101
def plan(self, request: str) -> ExecutionPlan:
    """Generate an execution plan for the request."""
    logger.info(f"Planning document generation for request: {request[:100]}...")

    prompt = self._build_planning_prompt(request)

    try:
        response = self.client.structured_generate(
            prompt,
            schema={
                "type": "object",
                "properties": {
                    "document_type": {"type": "string"},
                    "assumptions": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "description": {"type": "string"},
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                            },
                        },
                    },
                    "outline": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["document_type", "assumptions", "tasks", "outline"],
            },
        )

        parsed = response.get("parsed_response", {})

        # Convert tasks to Task objects
        tasks = [
            Task(
                id=t["id"],
                description=t["description"],
                dependencies=t.get("dependencies", []),
            )
            for t in parsed.get("tasks", [])
        ]

        plan = ExecutionPlan(
            document_type=parsed.get("document_type", "Professional Document"),
            assumptions=parsed.get("assumptions", {}),
            tasks=tasks,
            outline=parsed.get("outline", []),
        )

        logger.info(
            f"Planning complete. Generated {len(plan.tasks)} tasks. "
            f"Document type: {plan.document_type}"
        )
        return plan
```

**Planner Prompt (for Todo Lists):**

```python
def _build_planning_prompt(self, request: str) -> str:
    return f"""You are a todo list planning agent. Analyze this request and create a prioritized todo list.

Request: {request}

Generate a todo plan that includes:
1. Document type: "Todo List"
2. Assumptions: Any reasonable assumptions about deadlines/context
3. Tasks: Individual todo items with priorities
4. Outline: Section names for the final document

For the tasks, provide:
- Unique task IDs (starting from 1)
- Description (the actual todo item)
- Dependencies (task IDs this depends on, if any)

Each task should be:
- Specific and actionable
- Have an implied priority (High/Medium/Low based on urgency)
- Realistic deadline

Return the plan as JSON with these exact fields."""
```

### PHASE 2: Writer Agent

```python
# server/agents/writer.py - Line 95-175
def write_all_sections(self, request: str, plan: ExecutionPlan) -> List[DocumentSection]:
    """Write all sections of the document in order."""
  
    # SMART ROUTING: If it's a todo list, generate a simple table
    if plan.document_type.lower() == "todo list":
        return self._generate_todo_section(request, plan)

    sections = []

    for i, section_title in enumerate(plan.outline):
        section = self.write_section(
            request, plan, i, previous_sections=sections
        )
        sections.append(section)

    logger.info(f"All {len(sections)} sections written")
    return sections

def _generate_todo_section(self, request: str, plan: ExecutionPlan) -> List[DocumentSection]:
    """Generate a simple todo table from plan tasks."""
    logger.info("Generating todo list from plan tasks")

    # Build markdown table
    markdown = "| # | Task | Priority | Deadline | Hours |\n"
    markdown += "|---|------|----------|----------|-------|\n"

    for task in plan.tasks:
        task_id = task.id
        description = task.description.replace("|", "\\|")[:50]
        priority = self._infer_priority(task.description)
        deadline = plan.assumptions.get("deadline", "1 week")
        hours = self._estimate_hours(task.description)

        markdown += f"| {task_id} | {description} | {priority} | {deadline} | {hours} |\n"

    section = DocumentSection(
        title="Priority Todo List",
        content=markdown,
        heading_level=1
    )

    logger.info(f"Todo section generated with {len(plan.tasks)} items")
    return [section]

@staticmethod
def _infer_priority(description: str) -> str:
    """Infer priority from task description."""
    desc_lower = description.lower()
    if any(word in desc_lower for word in ["critical", "urgent", "asap", "immediately", "high"]):
        return "High"
    elif any(word in desc_lower for word in ["low", "optional", "later", "secondary"]):
        return "Low"
    return "Medium"
```

### PHASE 3: Reviewer Agent (Skipped for Todos)

```python
# server/agents/reviewer.py
def review_document(self, document_type: str, sections: List[DocumentSection]) -> ReviewFeedback:
    """Review document and provide feedback."""
    logger.info("Starting document review...")

    prompt = f"""You are an expert document reviewer. Assess this document for quality.

Document Type: {document_type}

Sections:
{chr(10).join([f"- {s.title}: {s.content[:200]}..." for s in sections])}

Assess for:
- Relevance to request
- Completeness
- Coherence
- Structure

Return JSON with issues found."""

    # Call LLM
    result = self.client.structured_generate(prompt, schema=REVIEW_SCHEMA)
  
    # Return feedback
    return ReviewFeedback(has_issues=..., section_feedback=[...])
```

### PHASE 4: DOCX Generation with Markdown Parsing

```python
# server/tools/docx_generator.py - Line 190-203
def from_structure(self, structure: DocumentStructure) -> None:
    """Build document from structured data."""
    self.create_document(structure.title)

    for section in structure.sections:
        if section.heading_level > 0:
            self.add_heading(section.title, section.heading_level)
        # Use markdown section parser to properly handle headers, tables, lists
        self.add_markdown_section(section.content)

    logger.info(f"Document built from structure with {len(structure.sections)} sections")

def add_markdown_section(self, markdown_text: str) -> None:
    """Add markdown content as properly formatted DOCX elements."""
    if not self.doc:
        raise DOCXGenerationException("Document not initialized.")

    blocks = MarkdownFormatter.parse_blocks(markdown_text)

    for block in blocks:
        block_type = block.get('type')

        if block_type == 'heading':
            self.add_heading(block['text'], level=min(block['level'], 3))

        elif block_type == 'table':
            rows = block['rows']
            if rows:
                cols = max(len(row) for row in rows) if rows else 1
                self.add_table(len(rows), cols, rows)

        elif block_type == 'bullet_list':
            self.add_bullet_list(block['items'])

        elif block_type == 'numbered_list':
            self.add_numbered_list(block['items'])

        elif block_type == 'paragraph':
            self.add_paragraph(block['text'])

    logger.debug(f"Added markdown section with {len(blocks)} blocks")
```

**Markdown Block Parser:**

```python
# server/tools/markdown_formatter.py - Line 11-74
@staticmethod
def parse_blocks(text: str) -> List[Dict[str, Any]]:
    """Parse markdown into block-level elements."""
    blocks = []
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Check for headers: ## Section
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            text_content = header_match.group(2).strip()
            blocks.append({'type': 'heading', 'level': level, 'text': text_content})
            i += 1
            continue

        # Check for tables: | col1 | col2 |
        if line.strip().startswith('|'):
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row_text = lines[i].strip()
                cells = [cell.strip() for cell in row_text.split('|')[1:-1]]
                # Skip separator rows
                if not all(c.replace('-', '').replace(' ', '') == '' for c in cells):
                    table_rows.append(cells)
                i += 1

            if table_rows:
                blocks.append({'type': 'table', 'rows': table_rows})
            continue

        # Check for bullet lists: - item
        bullet_match = re.match(r'^[-*]\s+(.+)$', line)
        if bullet_match:
            items = []
            while i < len(lines) and re.match(r'^[-*]\s+(.+)$', lines[i]):
                match = re.match(r'^[-*]\s+(.+)$', lines[i])
                items.append(match.group(1))
                i += 1
            blocks.append({'type': 'bullet_list', 'items': items})
            continue

        # Default: paragraph
        blocks.append({'type': 'paragraph', 'text': line.strip()})
        i += 1

    return blocks
```

---

## 5. RETURN TO CLIENT: Download Document

### Server sends back DocumentResponse

```python
{
    "success": true,
    "document_filename": "document_20260709_162132.docx",
    "request": "Create a todo list for studying",
    "execution_plan": {
        "document_type": "Todo List",
        "tasks": [...],
        "outline": ["Priority Todo List"],
        "assumptions": {...}
    },
    "quality_scores": {
        "relevance": 5,
        "completeness": 4,
        "coherence": 5,
        "structure": 5,
        "overall": 4
    },
    "metrics": {
        "total_execution_time_ms": 45000,
        "planner_latency_ms": 12000,
        "writer_latency_ms": 8000,
        "reviewer_latency_ms": 0,  // Skipped for todo
        "docx_generation_latency_ms": 500
    },
    "message": "Document generated successfully"
}
```

### Client displays result and enables download

```javascript
// client/app.js - generates download link
chatQuestionsArea.innerHTML = `
    <a href="${api.baseURL}/download/${data.document_filename}"
       class="btn btn-success"
       style="display: block; text-align: center; text-decoration: none; padding: 12px;">
         Download: ${data.document_filename}
    </a>
`;
```

### Server `/download` endpoint serves file

```python
# server/api.py - Line 206-233
@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated document."""
    # Security: prevent directory traversal
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = Path("output") / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    if not filepath.suffix == ".docx":
        raise HTTPException(status_code=400, detail="Only .docx files can be downloaded")

    logger.info(f"Downloading file: {filename}")
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
```

---

## Summary: Complete Flow

```
1. CLIENT: User types "Create todo list for studying" → sendChatMessage()
2. API: POST /chat/start → calls chat_orchestrator.start_conversation()
3. LLM: Generates response with questions via OllamaClient
4. CLIENT: Shows response, user answers questions
5. API: POST /chat/answer → processes each answer
6. LLM: Continues conversation, eventually returns [READY]
7. CLIENT: Shows "Generate Document" button
8. CLIENT: User clicks Generate → POST /chat/generate
9. API: Calls orchestrator.generate_document()
10. PHASE 1 (Planner): LLM generates 7 todo tasks with priorities
11. PHASE 2 (Writer): Creates markdown table from tasks
12. PHASE 3 (Reviewer): SKIPPED (todo list doesn't need review)
13. PHASE 4 (DOCX Gen): Parses markdown → creates DOCX file
14. SERVER: Saves to output/document_TIMESTAMP.docx
15. CLIENT: Shows Download + Refine buttons
16. CLIENT (OPTIONAL): User clicks Refine → startRefinement()
17. CLIENT: Hides chat history, shows refinement input
18. CLIENT: User enters refinement (e.g., "Add more details") → submitRefinement()
19. API: POST /chat/refine → re-runs orchestrator with refinement added to prompt
20. SERVER: Regenerates document with refinement applied
21. CLIENT: User downloads refined document OR refines again
```

---

## Key Points

 **100% LLM-Driven**: All decisions made by LLM, no hardcoded logic
 **Stateful Chat**: Context preserved across requests via session_id
 **Multi-Agent**: Planner → Writer → Reviewer pipeline
 **Smart Routing**: Todo lists skip review phase (faster)
 **Markdown → DOCX**: Block-level parsing converts to proper Word formatting
 **Progress Tracking**: Client updates progress bar (20% per message, 100% when ready)
 **Refinement Loop**: Users can refine documents iteratively without restarting conversation
 **Cloud Ollama**: Uses gpt-oss:120b with 3000s timeout

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat/start` | POST | Start new conversation |
| `/chat/answer` | POST | Answer clarifying question |
| `/chat/generate` | POST | Generate document from chat context |
| `/chat/refine` | POST | Refine existing document with feedback |
| `/chat/answer` | POST | Answer clarifying question |
| `/download/{filename}` | GET | Download generated DOCX |
