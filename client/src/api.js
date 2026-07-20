const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const userId = 'demo-user'

async function request(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

export const api = {
  userId,
  bootstrap: () => request(`/learning/demo?user_id=${userId}`),
  dashboard: (profileId) => request(`/learning/profiles/${profileId}/dashboard?user_id=${userId}`),
  search: (profileId, query) => request(`/learning/profiles/${profileId}/search?user_id=${userId}&q=${encodeURIComponent(query)}`),
  saveDocument: (documentId, content) => request(`/learning/documents/${documentId}/content?user_id=${userId}&content=${encodeURIComponent(content)}`, { method: 'PATCH' }),
  updateTask: (profileId, taskId, status) => request(`/learning/profiles/${profileId}/tasks/${taskId}?user_id=${userId}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  review: (profileId, cardId, rating) => request(`/learning/profiles/${profileId}/flashcards/${cardId}/review?user_id=${userId}`, { method: 'POST', body: JSON.stringify({ rating }) }),
  tutor: (profileId, question) => request(`/learning/profiles/${profileId}/tutor?user_id=${userId}`, { method: 'POST', body: JSON.stringify({ question }) }),
  infrastructure: () => request('/learning/infrastructure'),
}
