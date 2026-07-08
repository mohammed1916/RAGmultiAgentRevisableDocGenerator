/**
 * Main Application Logic
 * Handles UI interactions and document generation flow
 */

// DOM Elements
const documentForm = document.getElementById('documentForm');
const requestInput = document.getElementById('request');
const submitBtn = document.getElementById('submitBtn');
const loadingModal = document.getElementById('loadingModal');
const resultsSection = document.getElementById('resultsSection');
const serverStatusText = document.getElementById('statusText');
const statusIndicator = document.getElementById('statusIndicator');
const successAlert = document.getElementById('successAlert');
const errorAlert = document.getElementById('errorAlert');

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await checkServerStatus();
    setupEventListeners();
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
            submitBtn.disabled = false;
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
    submitBtn.disabled = true;
    submitBtn.title = 'Server is not running. Start it with: python main.py';
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    documentForm.addEventListener('submit', handleFormSubmit);
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    const request = requestInput.value.trim();
    if (!request) {
        showError('Please enter a document request');
        return;
    }

    try {
        // Show loading modal
        showLoadingModal();
        clearResults();

        // Generate document
        const response = await api.generateDocument(request);

        // Display results
        displayResults(response);
        showSuccessAlert('Document generated successfully!');
    } catch (error) {
        console.error('Error generating document:', error);
        showError(`Error: ${error.message}`);
    } finally {
        hideLoadingModal();
    }
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
 * Check server status periodically
 */
setInterval(checkServerStatus, 30000); // Check every 30 seconds
