# Muckaway.AI MCP Server

> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

UK waste logistics AI. Estimate waste volumes, get skip hire pricing, classify waste types, calculate haulage costs, find licensed disposal facilities, and generate legally compliant Waste Transfer Notes.

[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/muckaway-ai)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

## Tools

| Tool | Description |
|------|-------------|
| `estimate_waste_volume` | Estimate waste volume and recommend skip size |
| `get_skip_pricing` | Skip hire pricing by size with permit costs |
| `check_waste_type` | Classify waste type and return disposal requirements |
| `calculate_transport` | Calculate haulage cost for waste transport |
| `find_nearest_tip` | Find nearest licensed waste disposal facilities |
| `generate_waste_transfer_note` | Generate a legally compliant Waste Transfer Note |

## Quick Start

```bash
pip install mcp
git clone https://github.com/CSOAI-ORG/muckaway-ai-mcp.git
cd muckaway-ai-mcp
python server.py
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "muckaway-ai": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/muckaway-ai-mcp"
    }
  }
}
```

## Pricing

| Plan | Price | Requests |
|------|-------|----------|
| Free | $0/mo | 50 requests/month |
| Pro | $19/mo | 5,000 requests/month |

[Get on MCPize](https://mcpize.com/mcp/muckaway-ai)

## Part of MEOK AI Labs

This is one of 255+ MCP servers by MEOK AI Labs. Browse all at [meok.ai](https://meok.ai) or [GitHub](https://github.com/CSOAI-ORG).

---
**MEOK AI Labs** | [meok.ai](https://meok.ai) | nicholas@meok.ai | United Kingdom
