# src/pod_discover/reddit_parser.py
"""Reddit RSS parser for podcast mentions"""

import re
from collections import defaultdict

import feedparser


class RedditParser:
    """Parse Reddit RSS feeds to extract podcast mentions"""

    def __init__(self):
        self.base_url = "https://www.reddit.com"

    def parse_subreddit(self, subreddit: str, sort: str = "hot") -> dict[str, int]:
        """
        Parse a single subreddit RSS feed.
        Returns dict of {podcast_name: mention_count}
        """
        url = f"{self.base_url}/r/{subreddit}/{sort}.rss"

        try:
            feed = feedparser.parse(url)
            mentions = defaultdict(int)

            for entry in feed.entries:
                # Combine title and summary for analysis
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '')
                text = f"{title} {summary}"

                # Extract podcast names
                names = self._extract_podcast_names(text)
                for name in names:
                    mentions[name] += 1

            return dict(mentions)

        except Exception as e:
            # Log error but don't crash - Reddit parsing is best-effort
            print(f"Error parsing r/{subreddit}: {e}")
            return {}

    def _extract_podcast_names(self, text: str) -> list[str]:
        """
        Extract potential podcast names from text.
        Looks for:
        - Text in quotes: "Podcast Name"
        - Common podcast keywords followed by name
        """
        names = []

        # Find quoted strings (likely podcast names) - both single and double quotes
        quoted_double = re.findall(r'"([^"]+)"', text)
        quoted_single = re.findall(r"'([^']+)'", text)
        quoted = quoted_double + quoted_single
        names.extend([q.lower().strip() for q in quoted if len(q) > 2])

        # Find patterns like "podcast NAME" or "listening to NAME"
        # Stop at common words that end podcast names
        patterns = [
            r'podcast[:\s]+([A-Z][A-Za-z\s]{2,30}?)(?:\s+(?:is|was|these|those|days|today|now|here|there)|[.,!?]|$)',
            r'listening to\s+([A-Z][A-Za-z\s]{2,30}?)(?:\s+(?:is|was|these|those|days|today|now|here|there)|[.,!?]|$)',
            r'check out\s+([A-Z][A-Za-z\s]{2,30}?)(?:\s+(?:is|was|these|those|days|today|now|here|there)|[.,!?]|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            names.extend([m.lower().strip() for m in matches if len(m.strip()) > 2])

        # Deduplicate while preserving order
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)

        return unique_names

    def _aggregate_mentions(self, mentions_list: list[dict[str, int]]) -> dict[str, int]:
        """Aggregate mention counts from multiple sources"""
        result = defaultdict(int)

        for mentions in mentions_list:
            for name, count in mentions.items():
                result[name] += count

        return dict(result)

    def parse_subreddits(self, subreddits: list[str], sort: str = "hot") -> dict[str, int]:
        """
        Parse multiple subreddits and aggregate mentions.
        Returns dict of {podcast_name: total_mention_count}
        """
        all_mentions = []

        for subreddit in subreddits:
            mentions = self.parse_subreddit(subreddit, sort=sort)
            all_mentions.append(mentions)

        return self._aggregate_mentions(all_mentions)
