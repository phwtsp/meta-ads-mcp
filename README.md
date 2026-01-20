# 🚀 Meta Ads MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Ready](https://img.shields.io/badge/MCP-Ready-green)](https://modelcontextprotocol.io)
[![Meta Marketing API](https://img.shields.io/badge/Meta-Marketing%20API-blue)](https://developers.facebook.com/docs/marketing-apis)

> **AI-Powered Facebook Ads Integration for Claude, Cursor, and MCP Clients.**

## 📖 Overview

The **Meta Ads MCP Server** is a robust Python implementation of the **Model Context Protocol (MCP)**, designed to bridge valid **AI Agents** and LLMs directly with the **Meta (Facebook) Marketing API**.

This tool enables AI assistants (like **Claude Desktop**, **Cursor AI**, and **Windsurf**) to autonomously:
*   📊 **Retrieve real-time analytics** (Spend, ROAS, CTR, CPA).
*   🏗️ **Analyze campaign structures** (Campaigns, Ad Sets, Ads).
*   🎨 **Inspect ad creatives** (Images, Copy, Calls to Action).
*   📉 **Visualize performance trends** with ASCII charts.
*   � **Audit audience demographics** and platform placement.

Perfect for **Marketing Automation**, **Ad Ops**, and **Data Analysis** workflows directly within your AI chat interface.

---

## 📑 Table of Contents

*   [Features](#-features)
*   [Installation](#-installation)
*   [Configuration](#-configuration)
*   [Usage with MCP Clients](#-usage-with-mcp-clients)
*   [Tools Available](#-tools-available)
*   [Troubleshooting](#-troubleshooting)
*   [License](#-license)

---

## 🚀 Features

Empower your workflow with a comprehensive suite of ad management tools:

*   **Multi-Client Support**: Seamlessly switch between multiple ad accounts (`meta_list_clients`).
*   **Deep Drill-Down**: Navigate from account level down to specific ads (`meta_get_structure`).
*   **Advanced Analytics**: customized reports with daily breakdowns, specific metrics, and image previews (`meta_get_analytics`).
*   **Creative Intelligence**: Extract and analyze ad copy, headlines, and visual assets (`meta_get_ad_creative_details`).
*   **Financial Health**: Monitor account balances, spend caps, and payment statuses (`meta_get_account_balance`).
*   **Performance Comparison**: Side-by-side metric comparison for A/B testing analysis (`meta_compare_performance`).
*   **Trend Visualization**: Generate instant ASCII charts for metrics like ROAS and Spend (`meta_get_trend_chart`).

## 🛠️ Installation

### Prerequisites

*   **Python 3.10** or higher.
*   **Meta System User Token** or Developer Token with `ads_read` and `read_insights` permissions.
*   **Git** installed.

### Step-by-Step Guide

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/phwtsp/mcp-meta-ads.git
    cd mcp-meta-ads
    ```

2.  **Set Up Virtual Environment**
    It is best practice to use a virtual environment to manage dependencies.
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

### 1. Environment Variables (.env)
Create a `.env` file in the root directory to store your sensitive **Meta Access Token**.

```bash
# .env file
META_ACCESS_TOKEN=your_secret_access_token_here_eaaxxx
```

### 2. Client Mapping (clients.json)
Create a `clients.json` file to map easy-to-remember names to your Ad Account IDs. This allows you to ask "How is *Client A* doing?" instead of memorizing IDs.

```json
{
    "My Brand": "act_123456789",
    "Agency Client X": "act_987654321"
}
```

## 🔌 Usage with MCP Clients

Integrate this server with any MCP-compliant application.

### Claude Desktop / Cursor Configuration

Add the following to your `mcp.json` or MCP settings file.

**Important:** Use **absolute paths** for both the Python executable (inside your venv) and the `server.py` script.

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "/Users/username/path/to/mcp-meta-ads/venv/bin/python",
      "args": [
        "/Users/username/path/to/mcp-meta-ads/server.py"
      ],
      "env": {
        "META_ACCESS_TOKEN": "your_actual_token_here_if_not_using_dotenv"
      }
    }
  }
}
```

## 🧰 Tools Available

Here is a quick reference of the tools this server provides to the AI:

| Tool Name | Description | Key Arguments |
| :--- | :--- | :--- |
| `meta_list_clients` | List all configured accounts. | None |
| `meta_get_structure` | View Campaigns, AdSets, or Ads tree. | `account_identifier`, `campaign_id` |
| `meta_get_analytics` | Get detailed performance metrics. | `object_id`, `date_preset`, `level` |
| `meta_get_ad_creative` | Fetch ad copy, headline & image. | `ad_id` |
| `meta_get_demographics` | Age, Gender & Platform breakdown. | `object_id` |
| `meta_compare_performance`| Compare multiple items side-by-side.| `ids_str` |
| `meta_get_trend_chart` | ASCII line chart for metrics. | `object_id`, `metric` |

## ❓ Troubleshooting

**Q: "Error: Account not found"**
*   **A**: Ensure the account ID in `clients.json` starts with `act_` and that your Access Token has permissions for that specific ad account.

**Q: No data returned for insights**
*   **A**: Check the `date_preset`. New accounts might not have data for "last_7d". Try setting `date_preset="maximum"`.

**Q: Connection Refused / 500 Error**
*   **A**: Verify your internet connection and that the Meta API is not down. Check if your Access Token has expired.

## 🛡️ Security Note

*   **Never commit** your `.env` or `clients.json` files to GitHub.
*   The included `.gitignore` is pre-configured to prevent accidental leaks of these files.

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

*Built with ❤️ for the AI Agentic Era.*
