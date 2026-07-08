/**
 * API Service for Document Generation
 * Handles all communication with the backend server
 */

class DocumentGenerationAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL.replace(/\/$/, ''); // Remove trailing slash
        this.timeout = 5 * 60 * 1000; // 5 minutes
    }

    /**
     * Check if the server is healthy
     * @returns {Promise<boolean>}
     */
    async healthCheck() {
        try {
            const response = await this.request('/health', 'GET');
            return response.status === 'healthy';
        } catch (error) {
            console.warn('Health check failed:', error);
            return false;
        }
    }

    /**
     * Generate a document
     * @param {string} request - The document request
     * @param {object} metadata - Optional metadata
     * @returns {Promise<object>} - The response with generated document
     */
    async generateDocument(request, metadata = null) {
        if (!request || !request.trim()) {
            throw new Error('Request cannot be empty');
        }

        const payload = {
            request: request.trim(),
        };

        if (metadata) {
            payload.metadata = metadata;
        }

        return await this.request('/agent', 'POST', payload);
    }

    /**
     * Get server metrics
     * @returns {Promise<object>}
     */
    async getMetrics() {
        return await this.request('/metrics', 'GET');
    }

    /**
     * Download a document file
     * @param {string} filename - The document filename
     */
    downloadDocument(filename) {
        // In a real application, this would fetch the document from the server
        // For now, we'll construct a download link
        const downloadUrl = `${this.baseURL}/download/${filename}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * Internal method to make HTTP requests
     * @private
     */
    async request(endpoint, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);

            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json();
                const errorMessage = errorData.detail || response.statusText;
                throw new Error(`${response.status}: ${errorMessage}`);
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout - server took too long to respond');
            }
            throw error;
        }
    }
}

// Create global API instance
const api = new DocumentGenerationAPI();
