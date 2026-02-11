import { useState, useEffect, useCallback } from "react";
import SearchBar from "./components/SearchBar";
import EpisodeCard from "./components/EpisodeCard";
import * as api from "./api";

const TABS = [
  { id: "discover", label: "Discover" },
  { id: "history", label: "History" },
  { id: "profile", label: "Profile" },
];

function RecommendationCard({ episode, onViewFeed, favoriteFeeds }) {
  const [isFav, setIsFav] = useState(favoriteFeeds.has(episode.feed_id));
  const description = (() => {
    const div = document.createElement("div");
    div.innerHTML = episode.description || "";
    return div.textContent || "";
  })();

  async function toggleFavorite() {
    try {
      if (isFav) {
        await api.removeFavorite(episode.feed_id);
        setIsFav(false);
      } else {
        await api.addFavorite(episode.feed_id, episode.feed_title);
        setIsFav(true);
      }
    } catch (e) {
      console.error("Failed to toggle favorite:", e);
    }
  }

  const duration = episode.duration_seconds
    ? episode.duration_seconds >= 3600
      ? `${Math.floor(episode.duration_seconds / 3600)}h ${Math.floor((episode.duration_seconds % 3600) / 60)}m`
      : `${Math.floor(episode.duration_seconds / 60)}m`
    : null;

  return (
    <div className="group bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden hover:border-indigo-700/50 transition-all">
      <div className="p-4">
        <div className="flex gap-3">
          {episode.image && (
            <img
              src={episode.image}
              alt=""
              className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
              onError={(e) => (e.target.style.display = "none")}
            />
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-zinc-100 leading-snug line-clamp-2">
              {episode.url ? (
                <a
                  href={episode.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-indigo-400 transition-colors"
                >
                  {episode.title}
                </a>
              ) : (
                episode.title
              )}
            </h3>
            <div className="flex items-center gap-2 mt-1 text-xs text-zinc-500">
              {episode.feed_title && (
                <button
                  onClick={() => onViewFeed && onViewFeed(episode.feed_id, episode.feed_title)}
                  className="hover:text-indigo-400 cursor-pointer transition-colors truncate"
                >
                  {episode.feed_title}
                </button>
              )}
              {episode.feed_id && (
                <button
                  onClick={toggleFavorite}
                  title={isFav ? "Remove from favorites" : "Add podcast to favorites"}
                  className={`cursor-pointer transition-colors text-base leading-none ${
                    isFav ? "text-red-400" : "text-zinc-600 hover:text-red-300"
                  }`}
                >
                  {isFav ? "♥" : "♡"}
                </button>
              )}
              {duration && (
                <>
                  <span className="text-zinc-700">·</span>
                  <span>{duration}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {episode.match_reason && (
          <div className="mt-3 flex items-start gap-2 px-3 py-2 bg-indigo-950/30 border border-indigo-900/30 rounded-lg">
            <span className="text-indigo-400 flex-shrink-0 text-xs font-bold mt-px">
              {episode.match_score}/10
            </span>
            <p className="text-xs text-indigo-300/90 leading-relaxed">{episode.match_reason}</p>
          </div>
        )}

        <p className="mt-2 text-xs text-zinc-500 leading-relaxed line-clamp-2">{description}</p>
      </div>
    </div>
  );
}

function DiscoverView() {
  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(true);
  const [recError, setRecError] = useState(null);

  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchMode, setSearchMode] = useState(null);
  const [feedInfo, setFeedInfo] = useState(null);
  const [error, setError] = useState(null);
  const [queriesUsed, setQueriesUsed] = useState(null);
  const [recRequest, setRecRequest] = useState("");
  const [showRecInput, setShowRecInput] = useState(false);
  const [favoriteFeeds, setFavoriteFeeds] = useState(new Set());
  const [usage, setUsage] = useState(null);

  // Auto-load recommendations and favorites on mount
  useEffect(() => {
    api.getFavorites().then((data) => {
      setFavoriteFeeds(new Set((data.favorites || []).map((f) => f.feed_id)));
    });

    setRecLoading(true);
    api.getRecommendations("")
      .then((data) => {
        setRecommendations((data.episodes || []).slice(0, 6));
        if (data.usage) setUsage(data.usage);
        setRecError(null);
      })
      .catch((e) => {
        setRecError(e.message);
      })
      .finally(() => {
        setRecLoading(false);
      });
  }, []);

  async function refreshRecommendations() {
    setRecLoading(true);
    setRecError(null);
    try {
      const data = await api.getRecommendations("");
      setRecommendations((data.episodes || []).slice(0, 6));
      if (data.usage) setUsage(data.usage);
    } catch (e) {
      setRecError(e.message);
    } finally {
      setRecLoading(false);
    }
  }

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

  function clearSearch() {
    setEpisodes([]);
    setSearchMode(null);
    setFeedInfo(null);
    setQueriesUsed(null);
    setError(null);
  }

  return (
    <div className="space-y-8">
      {/* Hero Recommendations Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-zinc-100">Picked for You</h2>
            <p className="text-sm text-zinc-500 mt-0.5">Based on your taste profile</p>
          </div>
          <button
            onClick={refreshRecommendations}
            disabled={recLoading}
            className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            {recLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {recLoading && (
          <div className="py-12 text-center">
            <div className="inline-flex items-center gap-2 text-sm text-indigo-400 animate-pulse">
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing your taste profile and finding episodes...
            </div>
          </div>
        )}

        {recError && !recLoading && (
          <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl text-center">
            <p className="text-sm text-zinc-400">Could not load recommendations.</p>
            <p className="text-xs text-zinc-600 mt-1">{recError}</p>
            <button
              onClick={refreshRecommendations}
              className="mt-3 px-4 py-1.5 text-xs bg-indigo-700 hover:bg-indigo-600 text-white rounded-lg transition-colors cursor-pointer"
            >
              Try Again
            </button>
          </div>
        )}

        {!recLoading && !recError && recommendations.length === 0 && (
          <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-xl text-center">
            <p className="text-sm text-zinc-400">
              Set up your taste profile to get personalized recommendations.
            </p>
          </div>
        )}

        {!recLoading && recommendations.length > 0 && (
          <div className="grid gap-3">
            {recommendations.map((ep) => (
              <RecommendationCard
                key={ep.id}
                episode={ep}
                onViewFeed={handleViewFeed}
                favoriteFeeds={favoriteFeeds}
              />
            ))}
          </div>
        )}

        {usage && !recLoading && (
          <div className="flex items-center gap-3 mt-3 text-xs text-zinc-600">
            <span>Tokens: {(usage.input_tokens + usage.output_tokens).toLocaleString()} ({usage.input_tokens.toLocaleString()} in / {usage.output_tokens.toLocaleString()} out)</span>
            <span>·</span>
            <span>Cost: ${((usage.input_tokens / 1_000_000) * 1 + (usage.output_tokens / 1_000_000) * 5).toFixed(4)}</span>
            <span className="text-zinc-700">Haiku 4.5</span>
          </div>
        )}
      </section>

      {/* Divider */}
      <div className="border-t border-zinc-800" />

      {/* Explore Section */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-4">Explore</h2>

        <SearchBar onSearch={handleSearch} loading={loading} />

        <div className="flex items-center gap-3 flex-wrap mt-3">
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
            {loading && searchMode === "recommend" ? "Finding..." : "Custom Recommendations"}
          </button>
          {feedInfo && (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <span>Browsing:</span>
              <span className="text-indigo-400 font-medium">{feedInfo.title}</span>
              <button
                onClick={clearSearch}
                className="text-zinc-500 hover:text-zinc-300 cursor-pointer"
              >
                ✕
              </button>
            </div>
          )}
          {searchMode && !feedInfo && (
            <button
              onClick={clearSearch}
              className="text-xs text-zinc-500 hover:text-zinc-300 cursor-pointer"
            >
              Clear results
            </button>
          )}
        </div>

        {showRecInput && (
          <form onSubmit={handleRecommend} className="flex gap-2 mt-3">
            <input
              type="text"
              value={recRequest}
              onChange={(e) => setRecRequest(e.target.value)}
              placeholder="What are you in the mood for?"
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
          <div className="mt-3 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300">
            {error}
          </div>
        )}

        {queriesUsed && (
          <div className="flex items-center gap-2 flex-wrap text-xs text-zinc-500 mt-3">
            <span>AI searched for:</span>
            {queriesUsed.map((q, i) => (
              <span key={i} className="px-2 py-0.5 bg-zinc-800 rounded-full text-zinc-400">
                {q}
              </span>
            ))}
          </div>
        )}

        {loading && (
          <div className="text-center py-8 text-zinc-500">
            <p className="text-sm animate-pulse">
              {searchMode === "recommend"
                ? "AI is finding episodes for you..."
                : "Loading..."}
            </p>
          </div>
        )}

        {episodes.length > 0 && (
          <div className="grid gap-4 mt-4">
            {episodes.map((ep) => (
              <EpisodeCard
                key={ep.id}
                episode={ep}
                onViewFeed={handleViewFeed}
                favoriteFeeds={favoriteFeeds}
              />
            ))}
          </div>
        )}
      </section>
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
  const [favSearch, setFavSearch] = useState("");
  const [favResults, setFavResults] = useState([]);
  const [favSearching, setFavSearching] = useState(false);

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

  async function handleFavSearch(e) {
    if (e) e.preventDefault();
    if (!favSearch.trim()) return;
    setFavSearching(true);
    try {
      const data = await api.searchEpisodes(favSearch, 30);
      const seen = new Set(favorites.map((f) => f.feed_id));
      const feeds = [];
      for (const ep of data.episodes || []) {
        if (ep.feed_id && !seen.has(ep.feed_id)) {
          feeds.push({ feed_id: ep.feed_id, feed_title: ep.feed_title });
          seen.add(ep.feed_id);
        }
      }
      setFavResults(feeds);
    } catch (e) {
      console.error("Favorite search failed:", e);
    } finally {
      setFavSearching(false);
    }
  }

  async function handleAddFavorite(feedId, feedTitle) {
    await api.addFavorite(feedId, feedTitle);
    setFavorites([...favorites, { feed_id: feedId, feed_title: feedTitle }]);
    setFavResults(favResults.filter((f) => f.feed_id !== feedId));
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
            {favorites.length > 0 && (
              <div className="grid gap-2 mb-3">
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
            )}
            <form onSubmit={handleFavSearch} className="flex gap-2">
              <input
                type="text"
                value={favSearch}
                onChange={(e) => setFavSearch(e.target.value)}
                placeholder="Search podcasts to add..."
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                type="submit"
                disabled={favSearching}
                className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors cursor-pointer disabled:opacity-50"
              >
                {favSearching ? "Searching..." : "Search"}
              </button>
            </form>
            {favResults.length > 0 && (
              <div className="grid gap-2 mt-3">
                {favResults.map((feed) => (
                  <div
                    key={feed.feed_id}
                    className="flex items-center justify-between p-2 bg-zinc-900 border border-zinc-800 rounded-lg"
                  >
                    <span className="text-sm text-zinc-300">{feed.feed_title}</span>
                    <button
                      onClick={() => handleAddFavorite(feed.feed_id, feed.feed_title)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 cursor-pointer px-2"
                    >
                      + Add
                    </button>
                  </div>
                ))}
              </div>
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
