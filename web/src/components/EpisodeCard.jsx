import { useState } from "react";
import { logFeedback, addFavorite, removeFavorite, addToMyList } from "../api";

function StarRating({ rating, onRate }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          onClick={() => onRate(star)}
          className={`text-lg cursor-pointer transition-colors ${
            star <= rating
              ? "text-yellow-400"
              : "text-zinc-600 hover:text-yellow-300"
          }`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function formatDuration(seconds) {
  if (!seconds) return null;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function stripHtml(html) {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent || "";
}

export default function EpisodeCard({ episode, onViewFeed, onRate, favoriteFeeds = new Set(), myListIds = new Set() }) {
  const [userRating, setUserRating] = useState(0);
  const [rated, setRated] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [isFav, setIsFav] = useState(favoriteFeeds.has(episode.feed_id));
  const [inList, setInList] = useState(myListIds.has(episode.id));

  const description = stripHtml(episode.description || "");
  const duration = formatDuration(episode.duration_seconds);

  async function handleRate(stars) {
    setUserRating(stars);
    try {
      await logFeedback(String(episode.id), episode.title, stars);
      setRated(true);
      if (onRate) onRate(episode, stars);
    } catch (e) {
      console.error("Failed to log rating:", e);
    }
  }

  async function toggleFavorite() {
    try {
      if (isFav) {
        await removeFavorite(episode.feed_id);
        setIsFav(false);
      } else {
        await addFavorite(episode.feed_id, episode.feed_title);
        setIsFav(true);
      }
    } catch (e) {
      console.error("Failed to toggle favorite:", e);
    }
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden hover:border-zinc-600 transition-colors">
      <div className="flex gap-4 p-4">
        {episode.image && (
          <img
            src={episode.image}
            alt=""
            className="w-20 h-20 rounded-md object-cover flex-shrink-0"
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

          <div className="flex items-center gap-2 mt-1 text-xs text-zinc-400">
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
            <button
              onClick={async () => {
                if (inList) return;
                try {
                  await addToMyList(
                    episode.id, episode.title, episode.feed_id, episode.feed_title, episode.image, episode.url
                  );
                  setInList(true);
                } catch (e) {
                  console.error("Failed to add to list:", e);
                }
              }}
              title={inList ? "In your list" : "Add to My List"}
              className={`cursor-pointer transition-colors text-xs leading-none px-1.5 py-0.5 rounded ${
                inList
                  ? "bg-emerald-900/40 text-emerald-400"
                  : "bg-zinc-800 text-zinc-500 hover:text-indigo-300 hover:bg-zinc-700"
              }`}
            >
              {inList ? "Listed" : "+ List"}
            </button>
            {duration && (
              <>
                <span className="text-zinc-600">·</span>
                <span>{duration}</span>
              </>
            )}
          </div>

          <p
            className={`mt-2 text-xs text-zinc-400 leading-relaxed ${
              expanded ? "" : "line-clamp-2"
            }`}
          >
            {description}
          </p>
          {description.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-indigo-400 mt-1 cursor-pointer hover:text-indigo-300"
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
        </div>
      </div>

      {episode.match_reason && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-indigo-900/30 bg-indigo-950/20">
          <span className="text-xs font-medium text-indigo-400 flex-shrink-0">
            {episode.match_score}/10
          </span>
          <span className="text-xs text-indigo-300/80">{episode.match_reason}</span>
        </div>
      )}

      <div className="flex items-center justify-between px-4 py-2 border-t border-zinc-800 bg-zinc-950/50">
        <StarRating rating={userRating} onRate={handleRate} />
        {rated && (
          <span className="text-xs text-emerald-400">Rated!</span>
        )}
      </div>
    </div>
  );
}
