# Meta Ads MCP Server

This project implements a **Model Context Protocol (MCP)** server for integrating with the Meta Marketing API (Facebook Ads). It enables AI assistants and other MCP-compatible tools to interact directly with ad accounts to retrieve reports, campaign structures, creatives, and detailed metrics.

## 🚀 Features

The server exposes several powerful tools for ad analysis and management:

*   **`meta_list_clients`**: Lists configured clients and their account IDs.
*   **`meta_get_structure`**: Hierarchical navigation (Drill-down). Lists Campaigns for an account, or Ad Sets and Ads for a specific Campaign.
*   **`meta_get_analytics`**: Complete analytical reports (Spend, ROAS, CPA, CTR, etc.) with support for daily breakdowns and different levels (Campaign, AdSet, Ad). Includes image preview links for ads.
*   **`meta_get_ad_creative_details`**: Creative details (Image, Title, Body/Copy, CTA) for a specific ad.
*   **`meta_get_account_balance`**: Checks account balance, total spend, spend cap, and account status.
*   **`meta_get_demographics`**: Demographic analysis (Age and Gender) and Platform breakdown (Instagram vs Facebook).
*   **`meta_compare_performance`**: Side-by-side performance comparison of multiple IDs (Campaigns, AdSets, etc.).
*   **`meta_get_trend_chart`**: Generates ASCII charts to visualize metric trends (e.g., Spend, ROAS) over time.

## 🛠️ Installation and Configuration

### Prerequisites

*   Python 3.10+
*   Meta API Access Token (Business Manager System User or Developer Token)

### Step-by-Step Guide

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/phwtsp/mcp-meta-ads.git
    cd mcp-meta-ads
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root (or configure in your environment) with your access token:
    ```env
    META_ACCESS_TOKEN=your_token_here_eaaxxx...
    ```

5.  **Configure Clients:**
    Create a `clients.json` file in the project root to map friendly names to ad account IDs (`act_XXXXXXXX`):
    ```json
    {
        "Client Name 1": "act_1234567890",
        "Client Name 2": "act_0987654321"
    }
    ```

## 🔌 Using with MCP Clients

To use this server with MCP clients (like Claude Desktop or Cursor), add the configuration to your MCP settings file.

Example configuration (`mcp.json` or similar):

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "/absolute/path/to/project/venv/bin/python",
      "args": [
        "/absolute/path/to/project/server.py"
      ],
      "env": {
        "META_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

> **Note:** Ensure you use the **absolute path** for the `python` executable inside the virtual environment (`venv`) and for the `server.py` script.

## 📦 Project Structure

*   `server.py`: Main MCP server source code.
*   `.env`: (Not versioned) Stores sensitive credentials.
*   `clients.json`: (Not versioned) Configuration file for client ad accounts.
*   `requirements.txt`: Python dependency list.

## 🛡️ Security

This project handles sensitive access tokens.
*   Never commit the `.env` or `clients.json` files containing real data.
*   The `.gitignore` file is already configured to exclude these files.

## 📄 License

This project is licensed under the MIT License.
