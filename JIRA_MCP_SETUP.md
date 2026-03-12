# JIRA MCP Setup Guide

This project includes JIRA integration via MCP (Model Context Protocol).

## Quick Start

### 1. Install Prerequisites

```bash
# Install Node.js if not already installed
# Download from https://nodejs.org

# Install JIRA MCP server
npm install -g @modelcontextprotocol/server-jira
```

### 2. Get JIRA Credentials

1. **Email**: Your JIRA email (you're already logged in)
2. **API Token**: 
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the token

### 3. Configure Environment

```bash
# Copy the example env file
copy .env.example .env

# Edit .env and fill in your credentials:
# JIRA_EMAIL=your-email@example.com
# JIRA_API_TOKEN=your-api-token
```

### 4. Configure Your AI Tool

#### For Cursor:
Edit `%USERPROFILE%\.cursor\mcp.json`:
```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-jira"],
      "env": {
        "JIRA_EMAIL": "your-email@example.com",
        "JIRA_API_TOKEN": "your-api-token",
        "JIRA_DOMAIN": "nicholasburton2.atlassian.net"
      }
    }
  }
}
```

#### For Windsurf:
Edit `%USERPROFILE%\.windsurf\mcp.json` with the same configuration.

#### For Claude Desktop:
Edit `%APPDATA%\Claude\mcp_servers.json`:
```json
{
  "jira": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-jira"],
    "env": {
      "JIRA_EMAIL": "your-email@example.com",
      "JIRA_API_TOKEN": "your-api-token",
      "JIRA_DOMAIN": "nicholasburton2.atlassian.net"
    }
  }
}
```

### 5. Restart Your AI Tool

After configuring, restart your AI tool. You should now be able to:
- Query JIRA issues
- Create new issues
- Update existing issues
- Search by project, status, assignee, etc.

## Available Commands

Once connected, you can ask questions like:
- "Show me the backlog issues in DEV project"
- "What's the status of issue DEV-123?"
- "Create a new issue for fixing the login bug"
- "List all issues assigned to me"

## Troubleshooting

### "MCP server not found"
- Run `npx -y @modelcontextprotocol/server-jira` to verify installation
- Check that Node.js is in your PATH

### Authentication errors
- Verify your API token is correct
- Make sure JIRA_EMAIL matches your JIRA account email

### Connection issues
- Verify your JIRA domain is correct: `nicholasburton2.atlassian.net`
- Check that you have access to the DEV project
