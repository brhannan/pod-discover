# Testing Pod-Discover

## Unit Tests

Run the complete test suite:
```bash
uv run pytest -v
```

Run specific tests:
```bash
uv run pytest tests/test_db.py -v
uv run pytest tests/test_podcast_index.py -v
```

## Manual Testing with MCP Inspector

Once you have Podcast Index API credentials:

1. Set environment variables:
```bash
export PODCAST_INDEX_KEY="your_key"
export PODCAST_INDEX_SECRET="your_secret"
```

2. Run the MCP inspector:
```bash
uv run mcp dev src/pod_discover/server.py
```

3. Test each tool:
   - Try `search_episodes` with query: "history of computing"
   - Try `discover_random` with max_results: 3
   - Try `get_taste_profile` (should return default profile)
   - Try `update_taste_profile` with JSON like: `{"preferred_depth": "deep-dive", "topic_interests": {"technology": 0.9}}`
   - Try `log_feedback` with item_id: "12345", title: "Test Episode", rating: 5
   - Try `get_history` to see your logged feedback

## Testing with Claude Desktop

1. Ensure credentials are set in `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Restart Claude Desktop completely (Cmd+Q and relaunch)
3. Start a conversation and try commands like:
   - "Search for podcast episodes about artificial intelligence"
   - "Show me my taste profile"
   - "I liked that episode, rate it 5 stars with note 'Great explanation of neural networks'"

## Troubleshooting

### "PODCAST_INDEX_KEY and PODCAST_INDEX_SECRET must be set"
- Make sure credentials are properly set in the Claude Desktop config
- For command line testing, export the environment variables

### "No module named 'pod_discover'"
- Run from the project root directory
- Or use `uv run python -m pod_discover.server` instead

### Server not showing up in Claude Desktop
- Check that the config file is in the correct location
- Verify JSON syntax is valid (no trailing commas)
- Fully restart Claude Desktop (not just reload)
- Check Claude Desktop logs for errors
