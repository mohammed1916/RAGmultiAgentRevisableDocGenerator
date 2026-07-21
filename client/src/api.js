const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const userId = 'demo-user'

async function request(path, options = {}) {
  const isForm = options.body instanceof FormData
  // Let the browser set the multipart Content-Type (with boundary) for FormData.
  const headers = isForm ? { ...options.headers } : { 'Content-Type': 'application/json', ...options.headers }
  const response = await fetch(`${baseUrl}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  userId,
  bootstrap: () => request(`/learning/demo?user_id=${userId}`),
  listProfiles: () => request(`/learning/profiles?user_id=${userId}`),
  createProfile: (profile) => request('/learning/profiles', { method: 'POST', body: JSON.stringify({ user_id: userId, ...profile }) }),
  updateProfile: (profileId, changes) => request(`/learning/profiles/${profileId}?user_id=${userId}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteProfile: (profileId) => request(`/learning/profiles/${profileId}?user_id=${userId}`, { method: 'DELETE' }),
  dashboard: (profileId) => request(`/learning/profiles/${profileId}/dashboard?user_id=${userId}`),
  refreshGraph: (profileId) => request(`/learning/profiles/${profileId}/graph/refresh?user_id=${userId}`, { method: 'POST' }),
  saveGraph: (profileId, graph) => request(`/learning/profiles/${profileId}/graph?user_id=${userId}`, { method: 'PUT', body: JSON.stringify(graph) }),
  generatePlan: (profileId) => request(`/learning/profiles/${profileId}/generate/plan?user_id=${userId}`, { method: 'POST' }),
  generateFlashcards: (profileId) => request(`/learning/profiles/${profileId}/generate/flashcards?user_id=${userId}`, { method: 'POST' }),
  generateSubjects: (profileId) => request(`/learning/profiles/${profileId}/generate/subjects?user_id=${userId}`, { method: 'POST' }),
  search: (profileId, query) => request(`/learning/profiles/${profileId}/search?user_id=${userId}&q=${encodeURIComponent(query)}`),
  // Collections (workspaces) and documents
  createWorkspace: (profileId, name, description = '') => request('/learning/workspaces', { method: 'POST', body: JSON.stringify({ user_id: userId, profile_id: profileId, name, description }) }),
  listDocuments: (profileId) => request(`/learning/profiles/${profileId}/documents?user_id=${userId}`),
  createDocument: (doc) => request('/learning/documents', { method: 'POST', body: JSON.stringify({ user_id: userId, ...doc }) }),
  deleteDocument: (documentId) => request(`/learning/documents/${documentId}?user_id=${userId}`, { method: 'DELETE' }),
  saveDocument: (documentId, content) => request(`/learning/documents/${documentId}/content?user_id=${userId}&content=${encodeURIComponent(content)}`, { method: 'PATCH' }),
  updateTask: (profileId, taskId, status) => request(`/learning/profiles/${profileId}/tasks/${taskId}?user_id=${userId}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  review: (profileId, cardId, rating) => request(`/learning/profiles/${profileId}/flashcards/${cardId}/review?user_id=${userId}`, { method: 'POST', body: JSON.stringify({ rating }) }),
  tutor: (profileId, question) => request(`/learning/profiles/${profileId}/tutor?user_id=${userId}`, { method: 'POST', body: JSON.stringify({ question }) }),
  // Knowledge-base ingestion + retrieval
  ingestText: (profileId, fields) => {
    const form = new FormData()
    Object.entries(fields).forEach(([key, value]) => { if (value != null) form.append(key, value) })
    return request(`/learning/profiles/${profileId}/ingest/text?user_id=${userId}`, { method: 'POST', body: form, headers: {} })
  },
  ingestPdf: (profileId, file, fields = {}) => {
    const form = new FormData()
    form.append('file', file)
    Object.entries(fields).forEach(([key, value]) => { if (value != null) form.append(key, value) })
    return request(`/learning/profiles/${profileId}/ingest?user_id=${userId}`, { method: 'POST', body: form, headers: {} })
  },
  retrieve: (profileId, query, topK = 5) => request(`/learning/profiles/${profileId}/retrieve?user_id=${userId}&q=${encodeURIComponent(query)}&top_k=${topK}`),
  infrastructure: () => request('/learning/infrastructure'),
  // Model selector
  listModels: () => request('/models'),
  setModel: (mode, model) => request('/settings/model', { method: 'PUT', body: JSON.stringify({ mode, model }) }),
  // Per-item CRUD
  addTask: (profileId, task) => request(`/learning/profiles/${profileId}/tasks?user_id=${userId}`, { method: 'POST', body: JSON.stringify(task) }),
  editTask: (profileId, taskId, changes) => request(`/learning/profiles/${profileId}/tasks/${taskId}/edit?user_id=${userId}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteTask: (profileId, taskId) => request(`/learning/profiles/${profileId}/tasks/${taskId}?user_id=${userId}`, { method: 'DELETE' }),
  addCard: (profileId, card) => request(`/learning/profiles/${profileId}/flashcards?user_id=${userId}`, { method: 'POST', body: JSON.stringify(card) }),
  editCard: (profileId, cardId, changes) => request(`/learning/profiles/${profileId}/flashcards/${cardId}?user_id=${userId}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteCard: (profileId, cardId) => request(`/learning/profiles/${profileId}/flashcards/${cardId}?user_id=${userId}`, { method: 'DELETE' }),
  addSubject: (profileId, subject) => request(`/learning/profiles/${profileId}/subjects?user_id=${userId}`, { method: 'POST', body: JSON.stringify(subject) }),
  editSubject: (profileId, name, changes) => request(`/learning/profiles/${profileId}/subjects/${encodeURIComponent(name)}?user_id=${userId}`, { method: 'PATCH', body: JSON.stringify(changes) }),
  deleteSubject: (profileId, name) => request(`/learning/profiles/${profileId}/subjects/${encodeURIComponent(name)}?user_id=${userId}`, { method: 'DELETE' }),
}
