import { useState, useEffect, useCallback } from "react";
import SearchBar from "./components/SearchBar";
import EpisodeCard from "./components/EpisodeCard";
import * as api from "./api";

const TABS = [
  { id: "discover", label: "Discover" },
  { id: "history", label: "History" },
  { id: "profile", label: "Profile" },
];

function DiscoverView() {
  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchMode, setSearchMode] = useState(null);
  const [feedInfo, setFeedInfo] = useState(null);
  const [error, setError] = useState(null);
  const [queriesUsed, setQueriesUsed] = useState(null);
  const [recRequest, setRecRequest] = useState("");
  const [showRecInput, setShowRecInput] = useState(false);
  const [favoriteFeeds, setFavoriteFeeds] = useState(new Set());

  useEffect(() => {
    api.getFavorites().then((data) => {
      setFavoriteFeeds(new Set((data.favorites || []).map((f) => f.feed_id)));
    });
  }, []);

  async function handleSearch(query) {
    setLoading(true);
    setError(null);
    setFeedInfo(null);
    setQueriesUsed(null);
    try {
      const data = await api.searchEpisodes(query);
      setEpisodes(data.episodes || []);
      setSearchMode("search");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRandom() {
    setLoading(true);
    setError(null);
    setFeedInfo(null);
    setQueriesUsed(null);
    try {
      const data = await api.getRandomEpisodes(10);
      setEpisodes(data.episodes || []);
      setSearchMode("random");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecommend(e) {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setFeedInfo(null);
    setQueriesUsed(null);
    setShowRecInput(false);
    try {
      const data = await api.getRecommendations(recRequest);
      setEpisodes(data.episodes || []);
      setQueriesUsed(data.queries_used || null);
      setSearchMode("recommend");
      setRecRequest("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleViewFeed(feedId, feedTitle) {
    if (!feedId) return;
    setLoading(true);
    setError(null);
    setQueriesUsed(null);
    try {
      const data = await api.getFeedEpisodes(feedId);
      setEpisodes(data.episodes || []);
      setSearchMode("feed");
      setFeedInfo({ id: feedId, title: feedTitle });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <SearchBar onSearch={handleSearch} loading={loading} />

      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={handleRandom}
          disabled={loading}
          className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
        >
          Surprise Me
        </button>
        <button
          onClick={() => showRecInput ? handleRecommend() : setShowRecInput(true)}
          disabled={loading}
          className="px-4 py-2 text-sm bg-indigo-700 hover:bg-indigo-600 text-white rounded-lg transition-colors cursor-pointer disabled:opacity-50"
        >
          {loading && searchMode === "recommend" ? "Finding recommendations..." : "Recommend for Me"}
        </button>
        {feedInfo && (
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <span>Browsing:</span>
            <span className="text-indigo-400 font-medium">{feedInfo.title}</span>
            <button
              onClick={() => { setFeedInfo(null); setEpisodes([]); setSearchMode(null); }}
              className="text-zinc-500 hover:text-zinc-300 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {showRecInput && (
        <form onSubmit={handleRecommend} className="flex gap-2">
          <input
            type="text"
            value={recRequest}
            onChange={(e) => setRecRequest(e.target.value)}
            placeholder="Optional: tell it what you're in the mood for... (or leave blank for profile-based recs)"
            autoFocus
            className="flex-1 bg-zinc-900 border border-indigo-700/50 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            Go
          </button>
        </form>
      )}

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300">
          {error}
        </div>
      )}

      {queriesUsed && (
        <div className="flex items-center gap-2 flex-wrap text-xs text-zinc-500">
          <span>AI searched for:</span>
          {queriesUsed.map((q, i) => (
            <span key={i} className="px-2 py-0.5 bg-zinc-800 rounded-full text-zinc-400">
              {q}
            </span>
          ))}
        </div>
      )}

      {episodes.length === 0 && !loading && !error && (
        <div className="text-center py-20 text-zinc-500">
          <p className="text-lg">Search for episodes or hit "Recommend for Me" to get started</p>
        </div>
      )}

      {loading && (
        <div className="text-center py-12 text-zinc-500">
          <p className="text-sm animate-pulse">
            {searchMode === "recommend"
              ? "AI is analyzing your taste profile and finding episodes..."
              : "Loading..."}
          </p>
        </div>
      )}

      <div className="grid gap-4">
        {episodes.map((ep) => (
          <EpisodeCard
            key={ep.id}
            episode={ep}
            onViewFeed={handleViewFeed}
            favoriteFeeds={favoriteFeeds}
          />
        ))}
      </div>
    </div>
  );
}

function HistoryView() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getHistory(50).then((data) => {
      setEntries(data.entries || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <p className="text-zinc-500">Loading history...</p>;

  if (entries.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
        <p className="text-lg">No ratings yet</p>
        <p className="text-sm mt-1">Rate episodes in the Discover tab to build your history</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold text-zinc-200">Your Listening History</h2>
      <div className="grid gap-2">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded-lg"
          >
            <div className="min-w-0">
              <p className="text-sm text-zinc-200 truncate">{entry.title}</p>
              {entry.notes && (
                <p className="text-xs text-zinc-500 mt-0.5">{entry.notes}</p>
              )}
              <p className="text-xs text-zinc-600 mt-0.5">{entry.timestamp}</p>
            </div>
            <div className="flex-shrink-0 ml-4 text-yellow-400 text-sm">
              {"★".repeat(entry.rating)}
              {"☆".repeat(5 - entry.rating)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProfileView() {
  const [profile, setProfile] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [newTopic, setNewTopic] = useState("");
  const [newWeight, setNewWeight] = useState(0.5);
  const [favorites, setFavorites] = useState([]);

  useEffect(() => {
    api.getProfile().then((data) => {
      setProfile(data);
      setDraft(data);
    });
    api.getFavorites().then((data) => setFavorites(data.favorites || []));
  }, []);

  async function handleRemoveFavorite(feedId) {
    await api.removeFavorite(feedId);
    setFavorites(favorites.filter((f) => f.feed_id !== feedId));
  }

  async function handleSave() {
    setSaving(true);
    try {
      const updated = await api.updateProfile(draft);
      setProfile(updated);
      setEditing(false);
    } catch (e) {
      console.error("Failed to save profile:", e);
    } finally {
      setSaving(false);
    }
  }

  function addTopic() {
    if (!newTopic.trim()) return;
    setDraft({
      ...draft,
      topic_interests: {
        ...draft.topic_interests,
        [newTopic.trim().toLowerCase()]: newWeight,
      },
    });
    setNewTopic("");
    setNewWeight(0.5);
  }

  function removeTopic(topic) {
    const updated = { ...draft.topic_interests };
    delete updated[topic];
    setDraft({ ...draft, topic_interests: updated });
  }

  if (!profile) return <p className="text-zinc-500">Loading profile...</p>;

  if (!editing) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-200">Taste Profile</h2>
          <button
            onClick={() => { setEditing(true); setDraft(profile); }}
            className="px-4 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors cursor-pointer"
          >
            Edit
          </button>
        </div>

        <div className="grid gap-4">
          <ProfileField label="Depth" value={profile.preferred_depth} />
          <ProfileField
            label="Formats"
            value={
              profile.format_preferences.length > 0
                ? profile.format_preferences.join(", ")
                : "No preference"
            }
          />
          <ProfileField
            label="Duration"
            value={
              profile.preferred_duration_min || profile.preferred_duration_max
                ? `${profile.preferred_duration_min || "any"} – ${profile.preferred_duration_max || "any"} min`
                : "No preference"
            }
          />
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wide mb-2">Topics</p>
            {Object.keys(profile.topic_interests).length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {Object.entries(profile.topic_interests)
                  .sort(([, a], [, b]) => b - a)
                  .map(([topic, weight]) => (
                    <span
                      key={topic}
                      className="px-2.5 py-1 bg-indigo-900/40 border border-indigo-800/50 rounded-full text-xs text-indigo-300"
                    >
                      {topic}{" "}
                      <span className="text-indigo-500">
                        {Math.round(weight * 100)}%
                      </span>
                    </span>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No topics set</p>
            )}
          </div>
          {profile.notes && <ProfileField label="Notes" value={profile.notes} />}

          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wide mb-2">Favorite Podcasts</p>
            {favorites.length > 0 ? (
              <div className="grid gap-2">
                {favorites.map((fav) => (
                  <div
                    key={fav.feed_id}
                    className="flex items-center justify-between p-2 bg-zinc-800/50 rounded-lg"
                  >
                    <span className="text-sm text-zinc-200">{fav.feed_title}</span>
                    <button
                      onClick={() => handleRemoveFavorite(fav.feed_id)}
                      className="text-xs text-zinc-500 hover:text-red-400 cursor-pointer px-2"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">
                No favorites yet — click the heart next to a podcast name in Discover
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Edit mode
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-200">Edit Taste Profile</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setEditing(false)}
            className="px-4 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <div className="grid gap-5">
        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wide">Preferred Depth</label>
          <div className="flex gap-2 mt-2">
            {["casual", "moderate", "deep-dive"].map((d) => (
              <button
                key={d}
                onClick={() => setDraft({ ...draft, preferred_depth: d })}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors cursor-pointer ${
                  draft.preferred_depth === d
                    ? "bg-indigo-600 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wide">
            Format Preferences
          </label>
          <div className="flex gap-2 mt-2 flex-wrap">
            {["narrative", "interview", "roundtable", "solo"].map((f) => (
              <button
                key={f}
                onClick={() => {
                  const prefs = draft.format_preferences || [];
                  setDraft({
                    ...draft,
                    format_preferences: prefs.includes(f)
                      ? prefs.filter((p) => p !== f)
                      : [...prefs, f],
                  });
                }}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors cursor-pointer ${
                  (draft.format_preferences || []).includes(f)
                    ? "bg-indigo-600 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wide">Duration (minutes)</label>
          <div className="flex items-center gap-3 mt-2">
            <input
              type="number"
              placeholder="Min"
              value={draft.preferred_duration_min || ""}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  preferred_duration_min: e.target.value ? parseInt(e.target.value) : null,
                })
              }
              className="w-24 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-zinc-600">to</span>
            <input
              type="number"
              placeholder="Max"
              value={draft.preferred_duration_max || ""}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  preferred_duration_max: e.target.value ? parseInt(e.target.value) : null,
                })
              }
              className="w-24 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wide">Topics</label>
          <div className="flex flex-wrap gap-2 mt-2">
            {Object.entries(draft.topic_interests || {}).map(([topic, weight]) => (
              <span
                key={topic}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-indigo-900/40 border border-indigo-800/50 rounded-full text-xs text-indigo-300"
              >
                {topic} {Math.round(weight * 100)}%
                <button
                  onClick={() => removeTopic(topic)}
                  className="text-indigo-500 hover:text-red-400 cursor-pointer ml-0.5"
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
          <div className="flex items-center gap-2 mt-3">
            <input
              type="text"
              placeholder="Add topic..."
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTopic())}
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-indigo-500"
            />
            <input
              type="range"
              min="0.1"
              max="1"
              step="0.1"
              value={newWeight}
              onChange={(e) => setNewWeight(parseFloat(e.target.value))}
              className="w-20"
            />
            <span className="text-xs text-zinc-500 w-10">{Math.round(newWeight * 100)}%</span>
            <button
              onClick={addTopic}
              className="px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors cursor-pointer"
            >
              Add
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wide">Notes</label>
          <textarea
            value={draft.notes || ""}
            onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
            placeholder="Anything else about your taste..."
            rows={3}
            className="w-full mt-2 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-indigo-500 resize-none"
          />
        </div>
      </div>
    </div>
  );
}

function ProfileField({ label, value }) {
  return (
    <div>
      <p className="text-xs text-zinc-500 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-zinc-200 mt-0.5">{value}</p>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("discover");

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-bold tracking-tight">
            Pod Discover
          </h1>
          <nav className="flex gap-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors cursor-pointer ${
                  tab === t.id
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6">
        {tab === "discover" && <DiscoverView />}
        {tab === "history" && <HistoryView />}
        {tab === "profile" && <ProfileView />}
      </main>
    </div>
  );
}
