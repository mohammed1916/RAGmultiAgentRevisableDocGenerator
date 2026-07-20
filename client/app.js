/**
 * Main Application Logic
 * Handles UI interactions and document generation flow
 */

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');
const chatQuestionsArea = document.getElementById('chatQuestionsArea');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const resultsSection = document.getElementById('resultsSection');
const serverStatusText = document.getElementById('statusText');
const statusIndicator = document.getElementById('statusIndicator');
const successAlert = document.getElementById('successAlert');
const errorAlert = document.getElementById('errorAlert');

// Chat state
let currentChatContext = null;
let currentSessionId = null;
let isWaiting = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await checkServerStatus();
    setupEventListeners();
    await loadDocuments();
    // Auto-refresh documents list every 5 seconds
    setInterval(loadDocuments, 5000);
});

/**
 * Check server status on page load
 */
async function checkServerStatus() {
    try {
        const isHealthy = await api.healthCheck();
        if (isHealthy) {
            statusIndicator.classList.add('connected');
            statusIndicator.classList.remove('disconnected');
            serverStatusText.textContent = 'Connected';
        } else {
            setServerDisconnected();
        }
    } catch (error) {
        setServerDisconnected();
    }
}

function setServerDisconnected() {
    statusIndicator.classList.remove('connected');
    statusIndicator.classList.add('disconnected');
    serverStatusText.textContent = 'Disconnected';
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    chatSendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

/**
 * Send initial chat message or answer
 */
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

/**
 * Start new chat conversation
 */
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
        currentSessionId = data.session_id;  // Use session_id from server

        // Calculate progress based on conversation length
        const progress = calculateProgress(data.context);
        updateProgress(progress);
        progressSection.style.display = 'block';

        if (data.questions && data.questions.length > 0) {
            displayChatQuestions(data.questions);
        }

        if (data.is_ready_to_generate) {
            showGenerateButton();
        }
    } catch (error) {
        console.error('Error:', error);
        removeTyping();
        addChatMessage('assistant', '[ERROR] ' + error.message);
    } finally {
        isWaiting = false;
    }
}

/**
 * Answer a clarifying question
 */
async function answerQuestion(answer) {
    isWaiting = true;
    try {
        addChatMessage('user', answer);
        showTyping();

        const response = await fetch(
            `${api.baseURL}/chat/answer?session_id=${currentSessionId}&question_key=${currentQuestionKey}&answer=${encodeURIComponent(answer)}`,
            { method: 'POST' }
        );

        if (!response.ok) throw new Error('Failed to answer question');
        const data = await response.json();

        removeTyping();
        addChatMessage('assistant', data.message);

        currentChatContext = data.context;
        const progress = calculateProgress(data.context);
        updateProgress(progress);

        if (data.is_ready_to_generate) {
            updateProgress(1.0); // 100% when ready
            showGenerateButton();
        } else if (data.questions && data.questions.length > 0) {
            displayChatQuestions(data.questions);
        }
    } catch (error) {
        console.error('Error:', error);
        removeTyping();
        addChatMessage('assistant', '[ERROR] ' + error.message);
    } finally {
        isWaiting = false;
    }
}

/**
 * Display clarifying questions
 */
let currentQuestionKey = '';
function displayChatQuestions(questions) {
    if (!questions || questions.length === 0) return;

    const q = questions[0];
    currentQuestionKey = q.key;

    const html = `<div><strong>${q.question}</strong></div>`;

    if (q.options && q.options.length > 0) {
        let optionsHtml = '<div class="question-options" style="margin-top: 8px;">';
        q.options.forEach(opt => {
            optionsHtml += `<button class="option-button" onclick="answerQuestion('${opt}')">${opt}</button>`;
        });
        optionsHtml += '</div>';
        chatQuestionsArea.innerHTML = html + optionsHtml;
    } else {
        chatQuestionsArea.innerHTML = html + `
            <div style="display: flex; gap: 8px; margin-top: 8px;">
                <textarea id="answerInput" placeholder="Type your answer..." rows="2" style="flex: 1; padding: 8px; border: 2px solid #dee2e6; border-radius: 6px;"></textarea>
                <button class="btn btn-primary" style="align-self: flex-end;" onclick="answerQuestion(document.getElementById('answerInput').value)">Submit</button>
            </div>
        `;
        document.getElementById('answerInput').focus();
    }
}

/**
 * Show generate button when ready
 */
function showGenerateButton() {
    chatQuestionsArea.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <p style="margin-bottom: 12px; font-weight: 600; color: #28a745;">✓ I have all the information I need!</p>
            <p style="margin-bottom: 16px; color: #666; font-size: 14px;">I'll now create your document...</p>
            <button class="btn btn-success" style="width: 100%; padding: 12px;" onclick="generateDocument()">Generate Document</button>
        </div>
    `;
}

/**
 * Show refinement option after generation
 */
function showRefinementOption() {
    chatQuestionsArea.innerHTML = `
        <div style="padding: 20px; background: #f0f7ff; border-radius: 6px; border-left: 4px solid #0066cc;">
            <p style="margin: 0 0 16px 0; font-weight: 600; color: #0066cc;">✓ Document Generated!</p>
            <p style="margin: 0 0 16px 0; color: #555; font-size: 14px;">Would you like to refine this document further?</p>
            <div style="display: flex; gap: 8px;">
                <button class="btn btn-primary" style="flex: 1;" onclick="startRefinement()">Refine Document</button>
                <button class="btn btn-secondary" style="flex: 1;" onclick="clearRefinement()">Done</button>
            </div>
        </div>
    `;
}

/**
 * Start refinement mode - hide chat history and show refinement input
 */
function startRefinement() {
    // Collapse chat history
    const chatSection = document.querySelector('.chat-section');
    const collapseBtn = document.createElement('button');
    collapseBtn.className = 'btn btn-sm';
    collapseBtn.style.cssText = 'margin-top: 12px; padding: 6px 12px; font-size: 12px; width: 100%;';
    collapseBtn.textContent = '▼ Show Previous Conversation';
    collapseBtn.onclick = toggleChatHistory;

    chatMessages.style.display = 'none';
    progressSection.style.display = 'none';

    if (!document.getElementById('toggleChatBtn')) {
        collapseBtn.id = 'toggleChatBtn';
        chatMessages.parentNode.insertBefore(collapseBtn, chatMessages);
    }

    // Show refinement input
    chatQuestionsArea.innerHTML = `
        <div style="padding: 16px; background: #f9f9f9; border-radius: 6px; border: 1px solid #ddd;">
            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #333;">How would you like to refine this document?</label>
            <div style="display: flex; gap: 8px;">
                <textarea
                    id="refinementInput"
                    placeholder="e.g., 'Add more examples to section 2' or 'Make it more concise'"
                    rows="3"
                    style="flex: 1; padding: 10px; border: 2px solid #dee2e6; border-radius: 6px; font-family: inherit;"
                ></textarea>
                <button class="btn btn-primary" style="align-self: flex-end; height: fit-content;" onclick="submitRefinement()">Submit</button>
            </div>
        </div>
    `;

    document.getElementById('refinementInput').focus();
}

/**
 * Toggle chat history visibility
 */
function toggleChatHistory() {
    const toggleBtn = document.getElementById('toggleChatBtn');
    const isHidden = chatMessages.style.display === 'none';

    if (isHidden) {
        chatMessages.style.display = 'block';
        progressSection.style.display = 'block';
        toggleBtn.textContent = '▲ Hide Previous Conversation';
    } else {
        chatMessages.style.display = 'none';
        progressSection.style.display = 'none';
        toggleBtn.textContent = '▼ Show Previous Conversation';
    }
}

/**
 * Submit refinement request
 */
async function submitRefinement() {
    const refinement = document.getElementById('refinementInput').value.trim();
    if (!refinement || isWaiting) return;

    isWaiting = true;
    try {
        addChatMessage('user', refinement);
        showTyping();

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

        // Show refinement option again or download option
        if (data.is_ready_to_generate) {
            showRefinementOption();
        } else if (data.questions && data.questions.length > 0) {
            displayChatQuestions(data.questions);
        }
    } catch (error) {
        console.error('Error:', error);
        removeTyping();
        addChatMessage('assistant', '[ERROR] ' + error.message);
    } finally {
        isWaiting = false;
    }
}

/**
 * Clear refinement mode - restore normal view
 */
function clearRefinement() {
    const toggleBtn = document.getElementById('toggleChatBtn');
    if (toggleBtn) toggleBtn.remove();
    chatMessages.style.display = 'block';
    progressSection.style.display = 'block';
    chatQuestionsArea.innerHTML = `
        <div style="text-align: center; padding: 20px; color: #666;">
            <p>✓ Document ready for download</p>
        </div>
    `;
}

/**
 * Generate document from chat context
 */
async function generateDocument() {
    isWaiting = true;
    try {
        addChatMessage('assistant', '⏳ Generating your document...');
        showTyping();

        const response = await fetch(`${api.baseURL}/chat/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                context: currentChatContext
            })
        });

        if (!response.ok) throw new Error('Failed to generate document');
        const data = await response.json();

        removeTyping();
        addChatMessage('assistant',
            `✓ Document created!\n\n📄 ${data.document_filename}\n\nQuality: ${data.quality_scores.overall}/5`
        );

        // Show download + refinement options
        chatQuestionsArea.innerHTML = `
            <div style="display: flex; gap: 12px;">
                <a href="${api.baseURL}/download/${data.document_filename}"
                   class="btn btn-success"
                   style="flex: 1; text-align: center; text-decoration: none; padding: 12px; display: block;">
                    ⬇️ Download
                </a>
                <button class="btn btn-secondary" style="flex: 1; padding: 12px;" onclick="startRefinement()">
                    ✏️ Refine
                </button>
            </div>
        `;

        // Refresh documents list
        await loadDocuments();
    } catch (error) {
        console.error('Error:', error);
        removeTyping();
        addChatMessage('assistant', '[ERROR] ' + error.message);
    } finally {
        isWaiting = false;
    }
}

/**
 * Add message to chat
 */
function addChatMessage(role, content) {
    const msg = document.createElement('div');
    msg.className = `chat-message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;

    msg.appendChild(bubble);
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Show typing indicator
 */
function showTyping() {
    const msg = document.createElement('div');
    msg.className = 'chat-message assistant';
    msg.id = 'typingIndicator';

    const typing = document.createElement('div');
    typing.className = 'typing-dots';
    typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    msg.appendChild(typing);
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Remove typing indicator
 */
function removeTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

/**
 * Calculate progress based on conversation length
 */
function calculateProgress(context) {
    if (!context || !context.conversation) return 0;

    // Progress based on number of exchanges
    // Each user message = 20% up to 100%
    const messageCount = context.conversation.filter(msg => msg.role === 'user').length;
    const progress = Math.min(1.0, messageCount * 0.2);

    return progress;
}

/**
 * Update progress bar
 */
function updateProgress(confidence) {
    const percent = Math.round(confidence * 100);
    progressBar.style.width = percent + '%';
    progressPercent.textContent = percent + '%';
}

/**
 * Display generation results
 */
function displayResults(response) {
    // Show results section
    resultsSection.style.display = 'block';

    // Document info
    document.getElementById('docType').textContent = response.execution_plan.document_type;
    document.getElementById('docFile').textContent = response.document_filename;
    document.getElementById('docStatus').textContent = response.success ? '✓ Generated' : '✗ Failed';

    // Execution plan
    document.getElementById('tasksCount').textContent = response.metrics.num_generated_tasks;
    document.getElementById('sectionsCount').textContent = response.execution_plan.outline.length;

    // Assumptions
    displayAssumptions(response.assumptions);

    // Outline
    displayOutline(response.execution_plan.outline);

    // Quality scores
    displayScores(response.quality_scores);

    // Metrics
    displayMetrics(response.metrics);

    // Download button
    setupDownloadButton(response.document_filename);

    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

/**
 * Display assumptions in a list
 */
function displayAssumptions(assumptions) {
    const list = document.getElementById('assumptionsList');
    list.innerHTML = '';

    if (!assumptions || Object.keys(assumptions).length === 0) {
        list.innerHTML = '<li style="padding: 12px; text-align: center; color: #6c757d;">No assumptions recorded</li>';
        return;
    }

    Object.entries(assumptions).forEach(([key, value]) => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${escapeHtml(key)}:</strong> ${escapeHtml(value)}`;
        list.appendChild(li);
    });
}

/**
 * Display document outline
 */
function displayOutline(outline) {
    const list = document.getElementById('outlineList');
    list.innerHTML = '';

    if (!outline || outline.length === 0) {
        list.innerHTML = '<li style="padding: 12px; text-align: center; color: #6c757d;">No outline available</li>';
        return;
    }

    outline.forEach(section => {
        const li = document.createElement('li');
        li.textContent = section;
        list.appendChild(li);
    });
}

/**
 * Display quality scores
 */
function displayScores(scores) {
    if (!scores) return;

    const scoreFields = [
        { id: 'relevance', value: scores.relevance },
        { id: 'completeness', value: scores.completeness },
        { id: 'coherence', value: scores.coherence },
        { id: 'structure', value: scores.structure },
        { id: 'overall', value: scores.overall },
    ];

    scoreFields.forEach(field => {
        const percentage = (field.value / 5) * 100;
        const scoreElement = document.getElementById(field.id + 'Score');
        const valueElement = document.getElementById(field.id + 'Value');

        scoreElement.style.width = percentage + '%';
        valueElement.textContent = field.value + '/5';
    });
}

/**
 * Display performance metrics
 */
function displayMetrics(metrics) {
    if (!metrics) return;

    document.getElementById('totalTime').textContent = formatTime(metrics.total_execution_time_ms);
    document.getElementById('plannerTime').textContent = formatTime(metrics.planner_latency_ms);
    document.getElementById('writerTime').textContent = formatTime(metrics.writer_latency_ms);
    document.getElementById('reviewerTime').textContent = formatTime(metrics.reviewer_latency_ms);
    document.getElementById('docxTime').textContent = formatTime(metrics.docx_generation_latency_ms);
    document.getElementById('reviewIterations').textContent = metrics.review_iterations + ' iteration(s)';
}

/**
 * Setup download button
 */
function setupDownloadButton(filename) {
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = `./generated_documents/${filename}`;
    downloadBtn.download = filename;
    downloadBtn.target = '_blank';
}

/**
 * Fill example text into form
 */
function fillExample(element) {
    const text = element.querySelector('p').textContent;
    requestInput.value = text;
    requestInput.focus();
    requestInput.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Show loading modal with animation
 */
function showLoadingModal() {
    loadingModal.style.display = 'flex';
    animateLoadingPhases();
}

/**
 * Animate loading phases
 */
function animateLoadingPhases() {
    const phases = [
        'Planning document structure...',
        'Writing content sections...',
        'Reviewing and quality checking...',
        'Generating Word document...',
    ];

    let currentPhase = 0;
    const phaseElement = document.getElementById('loadingPhase');

    const interval = setInterval(() => {
        if (!loadingModal.style.display || loadingModal.style.display === 'none') {
            clearInterval(interval);
            return;
        }

        phaseElement.textContent = 'Phase: ' + phases[currentPhase % phases.length];
        currentPhase++;
    }, 3000);
}

/**
 * Hide loading modal
 */
function hideLoadingModal() {
    loadingModal.style.display = 'none';
}

/**
 * Show success alert
 */
function showSuccessAlert(message) {
    successAlert.textContent = message;
    successAlert.style.display = 'block';
    errorAlert.style.display = 'none';
}

/**
 * Show error alert
 */
function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
    successAlert.style.display = 'none';
}

/**
 * Clear results
 */
function clearResults() {
    successAlert.style.display = 'none';
    errorAlert.style.display = 'none';
}

/**
 * Format time in milliseconds to readable format
 */
function formatTime(ms) {
    if (!ms) return '-';

    if (ms < 1000) {
        return Math.round(ms) + 'ms';
    } else if (ms < 60000) {
        return (ms / 1000).toFixed(2) + 's';
    } else {
        return (ms / 60000).toFixed(2) + 'm';
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load and display generated documents
 */
async function loadDocuments() {
    try {
        const response = await fetch(`${api.baseURL}/files`);
        const data = await response.json();
        const docsList = document.getElementById('docsList');

        if (!docsList) return; // Element not found, skip

        // Update stats
        document.getElementById('totalDocs').textContent = data.total || 0;
        const totalSizeMB = (data.files || []).reduce((sum, f) => sum + (f.size_mb || 0), 0);
        document.getElementById('totalSize').textContent = totalSizeMB.toFixed(2) + ' MB';

        const files = data.files || [];

        if (files.length === 0) {
            docsList.innerHTML = '<div class="docs-empty">No documents generated yet. Create one above!</div>';
            return;
        }

        // Build file list HTML
        let html = '';
        files.forEach(file => {
            const created = new Date(file.created).toLocaleString();
            html += `
                <div class="doc-item">
                    <div class="doc-info">
                        <div class="doc-name">${escapeHtml(file.filename)}</div>
                        <div class="doc-meta">
                            Size: <strong>${file.size_mb}</strong> MB | Created: <strong>${created}</strong>
                        </div>
                    </div>
                    <div class="doc-actions">
                        <a href="${api.baseURL}/download/${encodeURIComponent(file.filename)}"
                           class="btn-download-small" download>
                            [Download]
                        </a>
                    </div>
                </div>
            `;
        });

        docsList.innerHTML = html;
    } catch (error) {
        console.error('Error loading documents:', error);
        const docsList = document.getElementById('docsList');
        if (docsList) {
            docsList.innerHTML = '<div class="docs-empty">[Error loading documents]</div>';
        }
    }
}

/**
 * Check server status periodically
 */
setInterval(checkServerStatus, 30000); // Check every 30 seconds
