const API_BASE = (import.meta.env.VITE_SSK_API_BASE || "").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const lawApi = {
  getCategories() {
    return request("/api/categories");
  },
  getHomePicks() {
    return request("/api/home/picks");
  },
  getBills(params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/api/bills${query ? `?${query}` : ""}`);
  },
  getBill(id) {
    return request(`/api/bills/${id}`);
  },
  searchBills(query) {
    return request(`/api/search?q=${encodeURIComponent(query)}`);
  },
  sendChat(message, sessionId) {
    return request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId }),
    });
  },
};
