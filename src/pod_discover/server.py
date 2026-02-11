#!/usr/bin/env python3
"""Pod-Discover MCP Server: Episode-level podcast discovery."""

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .db import Database
from .models import ConsumptionEntry, TasteProfile
from .podcast_index import PodcastIndexClient

# Initialize global instances
db = Database()
podcast_client = PodcastIndexClient()

# Create MCP server
app = Server("pod-discover")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="search_episodes",
            description="Search podcast episodes by keyword or topic using full-text search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (keywords or topics)"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_episode",
            description="Get full details for a specific episode by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "episode_id": {"type": "integer", "description": "The episode ID"},
                },
                "required": ["episode_id"],
            },
        ),
        Tool(
            name="get_podcast_episodes",
            description="List recent episodes from a specific podcast feed",
            inputSchema={
                "type": "object",
                "properties": {
                    "feed_id": {"type": "integer", "description": "The podcast feed ID"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of episodes to return",
                        "default": 20,
                    },
                },
                "required": ["feed_id"],
            },
        ),
        Tool(
            name="search_by_person",
            description="Find episodes featuring a specific person (host, guest, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "person": {"type": "string", "description": "Name of the person to search for"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["person"],
            },
        ),
        Tool(
            name="discover_random",
            description="Get random episodes for discovery, optionally filtered by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of episodes to return",
                        "default": 5,
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g., 'Technology', 'History')",
                    },
                },
            },
        ),
        Tool(
            name="get_taste_profile",
            description="Get the current user taste profile including preferences and interests",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="update_taste_profile",
            description="Update the user taste profile with new preferences",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_json": {
                        "type": "string",
                        "description": "JSON string of TasteProfile fields to update",
                    },
                },
                "required": ["profile_json"],
            },
        ),
        Tool(
            name="log_feedback",
            description="Log user feedback for a consumed item (rating + notes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "ID of the item (episode ID as string)"},
                    "title": {"type": "string", "description": "Title of the item"},
                    "rating": {
                        "type": "integer",
                        "description": "Rating from 1-5",
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "notes": {"type": "string", "description": "Optional notes about the item"},
                },
                "required": ["item_id", "title", "rating"],
            },
        ),
        Tool(
            name="get_history",
            description="Get recent consumption history",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entries to return",
                        "default": 20,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_episodes":
            query = arguments["query"]
            max_results = arguments.get("max_results", 10)
            episodes = await podcast_client.search_episodes_by_term(query, max_results)
            result = [ep.model_dump() for ep in episodes]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_episode":
            episode_id = arguments["episode_id"]
            episode = await podcast_client.get_episode_by_id(episode_id)
            result = episode.model_dump() if episode else {"error": "Episode not found"}
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_podcast_episodes":
            feed_id = arguments["feed_id"]
            max_results = arguments.get("max_results", 20)
            episodes = await podcast_client.get_episodes_by_feed(feed_id, max_results)
            result = [ep.model_dump() for ep in episodes]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "search_by_person":
            person = arguments["person"]
            max_results = arguments.get("max_results", 10)
            episodes = await podcast_client.search_episodes_by_person(person, max_results)
            result = [ep.model_dump() for ep in episodes]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "discover_random":
            max_results = arguments.get("max_results", 5)
            category = arguments.get("category")
            episodes = await podcast_client.get_random_episodes(max_results, category)
            result = [ep.model_dump() for ep in episodes]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_taste_profile":
            profile = db.get_taste_profile()
            return [TextContent(type="text", text=profile.model_dump_json(indent=2))]

        elif name == "update_taste_profile":
            profile_json = arguments["profile_json"]
            profile_data = json.loads(profile_json)
            # Merge with existing profile
            current = db.get_taste_profile()
            updated_data = current.model_dump()
            updated_data.update(profile_data)
            updated_profile = TasteProfile(**updated_data)
            db.update_taste_profile(updated_profile)
            return [TextContent(type="text", text=json.dumps({"status": "success", "profile": updated_data}))]

        elif name == "log_feedback":
            entry = ConsumptionEntry(
                item_id=arguments["item_id"],
                title=arguments["title"],
                rating=arguments["rating"],
                notes=arguments.get("notes"),
            )
            entry_id = db.log_consumption(entry)
            return [
                TextContent(
                    type="text", text=json.dumps({"status": "success", "entry_id": entry_id, "rating": entry.rating})
                )
            ]

        elif name == "get_history":
            limit = arguments.get("limit", 20)
            history = db.get_consumption_history(limit)
            result = [entry.model_dump() for entry in history]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
