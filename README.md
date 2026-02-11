# Pod-Discover

Episode-level podcast discovery MCP server that provides Claude with tools to search podcast episodes, manage a taste profile, and log feedback.

## Features

- **Search & Discovery**: Search episodes by keyword, person, or discover random episodes
- **Taste Profile**: Track preferences (depth, format, topics, duration) that Claude can reference
- **Consumption Log**: Rate and annotate episodes to build your listening history
- **Rich Metadata**: Access episode descriptions, duration, images, and transcript URLs

## Getting Podcast Index API Credentials

1. Sign up at [Podcast Index](https://api.podcastindex.org/)
   - **Note**: Currently requires a non-free email domain (no Gmail, Outlook, etc.)
   - Consider using a custom domain email or work email
2. After signup, get your API Key and Secret from the dashboard

## Setup

1. Install dependencies:
```bash
cd pod-discover
uv sync
```

2. Configure Claude Desktop:

The configuration has been created at `~/Library/Application Support/Claude/claude_desktop_config.json`.

Edit this file and replace the placeholders with your actual credentials:
```json
{
  "mcpServers": {
    "pod-discover": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/bhannan/code/pod-discover", "src/pod_discover/server.py"],
      "env": {
        "PODCAST_INDEX_KEY": "your_actual_key_here",
        "PODCAST_INDEX_SECRET": "your_actual_secret_here"
      }
    }
  }
}
```

3. Restart Claude Desktop to load the MCP server

## Testing

Run the test suite:
```bash
uv run pytest
```

Test the MCP server with MCP Inspector:
```bash
uv run mcp dev src/pod_discover/server.py
```

## Available Tools

### Search & Discovery
- `search_episodes` - Search by keyword/topic
- `get_episode` - Get details for a specific episode ID
- `get_podcast_episodes` - List recent episodes from a podcast
- `search_by_person` - Find episodes featuring a specific person
- `discover_random` - Get random episodes for serendipitous discovery

### Taste Profile
- `get_taste_profile` - View your current preferences
- `update_taste_profile` - Update preferences (depth, format, topics, duration)
- `log_feedback` - Rate an episode (1-5) with notes
- `get_history` - View your listening history

## Example Usage with Claude

Once configured, you can have conversations like:

```
You: "Search for episodes about the history of cryptography"
Claude: [Uses search_episodes tool]

You: "I really liked that episode about Enigma, rate it 5 stars"
Claude: [Uses log_feedback tool]

You: "What's my taste profile?"
Claude: [Uses get_taste_profile tool]

You: "Based on what I like, find me something new about WWII history"
Claude: [Uses search_episodes and cross-references with your profile]
```

## Database

Profile and consumption data is stored in `~/.pod-discover/pod_discover.db`

## Future Enhancements (v1)

- Book search integration (Google Books API)
- Movie search integration (TMDB API)
- Queue/library management
- Transcript fetching and semantic search
