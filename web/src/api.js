const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function searchEpisodes(query, maxResults = 20) {
  return request(`/episodes/search?q=${encodeURIComponent(query)}&max_results=${maxResults}`);
}

export async function getRandomEpisodes(maxResults = 10, category = null) {
  let url = `/episodes/random?max_results=${maxResults}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;
  return request(url);
}

export async function getEpisode(id) {
  return request(`/episodes/${id}`);
}

export async function getFeedEpisodes(feedId, maxResults = 20) {
  return request(`/episodes/feed/${feedId}?max_results=${maxResults}`);
}

export async function searchByPerson(person, maxResults = 10) {
  return request(`/episodes/person/${encodeURIComponent(person)}?max_results=${maxResults}`);
}

export async function getProfile() {
  return request("/profile");
}

export async function updateProfile(profile) {
  return request("/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export async function logFeedback(itemId, title, rating, notes = null) {
  return request("/feedback", {
    method: "POST",
    body: JSON.stringify({ item_id: itemId, title, rating, notes }),
  });
}

export async function getHistory(limit = 20) {
  return request(`/history?limit=${limit}`);
}

export async function getFavorites() {
  return request("/favorites");
}

export async function addFavorite(feedId, feedTitle) {
  return request("/favorites", {
    method: "POST",
    body: JSON.stringify({ feed_id: feedId, feed_title: feedTitle }),
  });
}

export async function removeFavorite(feedId) {
  return request(`/favorites/${feedId}`, { method: "DELETE" });
}

export async function getRecommendations(userRequest = "") {
  return request("/recommend", {
    method: "POST",
    body: JSON.stringify({ request: userRequest }),
  });
}
