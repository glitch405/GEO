"""
Probe Bright Data's MCP server: launch it via npx, list available tools,
print anything that looks like an AI-answer scraper.
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


async def main() -> int:
    token = os.environ.get("BRIGHTDATA_API_TOKEN")
    if not token:
        print("BRIGHTDATA_API_TOKEN not set", file=sys.stderr)
        return 2

    params = StdioServerParameters(
        command="npx",
        args=["-y", "@brightdata/mcp"],
        env={
            "API_TOKEN": token,
            "PRO_MODE": "true",
            "PATH": os.environ.get("PATH", ""),
        },
    )

    print("Launching Bright Data MCP server via npx…")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Session initialized.\n")

            tools_resp = await session.list_tools()
            print(f"Total tools exposed: {len(tools_resp.tools)}\n")

            keywords = ("chatgpt", "perplexity", "google", "grok", "ai_insights", "ai mode")
            print("Tools matching AI-answer keywords:")
            for t in tools_resp.tools:
                name = t.name.lower()
                if any(k in name for k in keywords):
                    print(f"  • {t.name}")
                    if t.description:
                        desc = (t.description[:150] + "…") if len(t.description) > 150 else t.description
                        print(f"      {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
