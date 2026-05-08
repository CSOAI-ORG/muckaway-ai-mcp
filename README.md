[![muckaway-ai-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/muckaway-ai-mcp/badges/score.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/muckaway-ai-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-Published-green)](https://registry.modelcontextprotocol.io)
[![PyPI](https://img.shields.io/pypi/v/muckaway-ai-mcp)](https://pypi.org/project/muckaway-ai-mcp/)

[![muckaway-ai-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/muckaway-ai-mcp/badges/card.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/muckaway-ai-mcp)

<div align="center">

# Muckaway Ai MCP

**Muckaway.AI MCP Server - Waste Logistics AI**

[![PyPI](https://img.shields.io/pypi/v/meok-muckaway-ai-mcp)](https://pypi.org/project/meok-muckaway-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Muckaway.AI MCP Server - Waste Logistics AI
Built by MEOK AI Labs | https://muckaway.ai

UK waste removal, skip hire, haulage costing, waste classification,
disposal facility lookup, and Waste Transfer Note generation.
Covers Environmental Protection Act 1990 and Duty of Care regulations.

## Tools

| Tool | Description |
|------|-------------|
| `estimate_waste_volume` | Estimate waste volume from dimensions and recommend skip size. |
| `get_skip_pricing` | Return skip hire pricing by size with permit costs. |
| `check_waste_type` | Classify waste type and return disposal requirements. |
| `calculate_transport` | Calculate haulage cost for waste transport. |
| `find_nearest_tip` | Find nearest licensed waste disposal facilities by waste type and postcode. |
| `generate_waste_transfer_note` | Generate a Waste Transfer Note with all legally mandatory fields. |

## Installation

```bash
pip install meok-muckaway-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "muckaway-ai": {
      "command": "python",
      "args": ["-m", "meok_muckaway_ai_mcp.server"]
    }
  }
}
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
<!-- mcp-name: io.github.CSOAI-ORG/muckaway-ai-mcp -->
