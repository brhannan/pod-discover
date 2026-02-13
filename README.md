# Pod-Discover

Episode-level podcast discovery with AI-powered recommendations. Includes a web app for browsing and curating, plus an MCP server for conversational discovery with Claude.

## Features

- **Search & Discovery**: Search episodes by keyword, person, or discover random episodes
- **AI Recommendations**: Claude analyzes your taste profile, favorite podcasts, and rating history to find episodes you'll love — with explanations for each match
- **Favorite Podcasts**: Heart podcasts you love; the recommender uses them as signals
- **Taste Profile**: Track preferences (depth, format, topics, duration)
- **Consumption Log**: Rate episodes (1-5 stars) to build your listening history
- **Two Interfaces**: Web app for browsing/curating, MCP server for conversational discovery in Claude Desktop

## Architecture

```
┌─────────────────┐     ┌──────────────┐
│   Web Frontend  │     │ Claude       │
│   (React/Vite)  │     │ Desktop      │
└────────┬────────┘     └──────┬───────┘
         │                     │
    ┌────▼─────┐        ┌──────▼──────┐
    │ FastAPI  │        │ MCP Server  │
    │ Backend  │        │ (stdio)     │
    └────┬─────┘        └──────┬──────┘
         │                     │
         └──────────┬──────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
    Podcast    Claude API   SQLite
    Index API  (Haiku)     (shared DB)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Podcast Index API credentials](https://api.podcastindex.org/)
- [Anthropic API key](https://console.anthropic.com/) (for AI recommendations)

## Setup

### 1. Install dependencies

```bash
cd pod-discover
uv sync
cd web && npm install
```

### 2. Set environment variables

```bash
export PODCAST_INDEX_KEY="your_key"
export PODCAST_INDEX_SECRET="your_secret"
export ANTHROPIC_API_KEY="your_key"       # for AI recommendations
```

### 3. Run the web app

Start both the backend and frontend:

```bash
# Terminal 1: Backend API
uv run uvicorn pod_discover.api:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd web && npm run dev
```

Open http://localhost:5173

### 4. (Optional) Configure Claude Desktop MCP

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pod-discover": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pod-discover", "src/pod_discover/server.py"],
      "env": {
        "PODCAST_INDEX_KEY": "your_key",
        "PODCAST_INDEX_SECRET": "your_secret"
      }
    }
  }
}
```

## Web App

### Discover Tab
- **Search**: Find episodes by keyword
- **Surprise Me**: Random episode discovery
- **Recommend for Me**: AI-powered recommendations based on your profile, favorites, and history
- **Heart button**: Favorite a podcast to improve future recommendations
- **Star ratings**: Rate episodes 1-5 stars

### History Tab
- View all rated episodes with timestamps

### Profile Tab
- Set preferred depth (casual / moderate / deep-dive)
- Choose format preferences (narrative, interview, roundtable, solo)
- Set duration range
- Manage topic interests with weighted tags
- View and manage favorite podcasts

## MCP Server Tools

### Search & Discovery
- `search_episodes` - Search by keyword/topic
- `get_episode` - Get details for a specific episode
- `get_podcast_episodes` - List episodes from a podcast
- `search_by_person` - Find episodes featuring a specific person
- `discover_random` - Random episodes for serendipitous discovery

### Taste Profile
- `get_taste_profile` / `update_taste_profile` - Manage preferences
- `log_feedback` - Rate an episode (1-5) with notes
- `get_history` - View listening history

## Recommendation Algorithm

Pod Discover uses a **hybrid recommendation system** that combines:
- **70% Personalization**: AI analysis of your taste profile, favorites, and listening history
- **30% Discovery**: Trending content and social proof from the community

### How It Works

1. **Multi-Source Candidate Gathering**
   - AI generates search queries based on your profile
   - Fetches trending episodes from Podcast Index
   - Pulls from Reddit-mentioned podcasts

2. **Composite Scoring**
   Each episode gets scored on 6 dimensions:
   - 🎯 **AI Match** (50%): How well it fits your taste profile
   - 📈 **Trending** (15%): Current popularity on Podcast Index
   - 💬 **Social Buzz** (10%): Reddit community mentions
   - ⭐ **Popularity** (10%): Established show quality
   - 🕐 **Recency** (10%): Preference for fresh content
   - ⏱️ **Duration** (5%): Fits your preferred episode length

3. **Final Ranking**
   Episodes are ranked by composite score, deduplicated by podcast feed, and top results returned.

### Tuning Recommendations

Want to adjust how recommendations work? Edit `src/pod_discover/config.py`:

```python
class RecommendationWeights:
    AI_MATCH = 0.50      # Increase for more personalization
    TRENDING = 0.15      # Increase for more discovery
    SOCIAL_BUZZ = 0.10   # Increase for community favorites
    # ...
```

Weights must sum to 1.0. Restart the server after changes.

### Caching

- **Recommendations**: Cached for 1 hour (invalidates when you update profile/favorites)
- **Trending data**: Refreshed every 4 hours
- **Reddit mentions**: Refreshed every 6 hours

## Testing

```bash
uv run pytest -v
```

## Data Storage

All data is stored locally in `~/.pod-discover/pod_discover.db` (SQLite). This database is shared between the web app and MCP server, so your ratings, favorites, and profile stay in sync across both interfaces.

## Future Enhancements

- Book/movie cross-medium recommendations
- Queue/library management
- Transcript fetching and semantic search
