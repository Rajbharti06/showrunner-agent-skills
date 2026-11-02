# Connect Showrunner over MCP

The skills work on their own. The MCP server adds the same tools as typed, callable functions for any client that speaks the Model Context Protocol: scoring, ranking, calendar building, fact lookup, playbooks and experiments. The list is in [tools.md](tools.md).

It has no dependencies beyond Python 3.9 or newer.

## Run it

From a checkout, with nothing installed:

```
PYTHONPATH=engine python -m showrunner.mcp_server
```

Or install it once and use the command:

```
pip install .
showrunner-mcp
```

It speaks MCP over stdio by default and prints `stdio ready` on stderr. It negotiates protocol versions 2025-11-25, 2025-06-18, 2025-03-26 and 2024-11-05. Besides tools it offers three prompts, `start`, `weekly` and `monthly`, which a client can show as shortcuts.

**Safety defaults.** Over stdio the server will not read files from your disk unless you set `SHOWRUNNER_MCP_FILES=1`. Without it, tools take the text itself. Profile, playbook runs and experiment logs are saved in `~/.showrunner` (change it with `SHOWRUNNER_HOME`). Nothing is sent anywhere. The server never posts to any platform.

## Claude Desktop

Add this to `claude_desktop_config.json` and restart the app. If you installed with pip:

```json
{
  "mcpServers": {
    "showrunner": { "command": "showrunner-mcp" }
  }
}
```

If you did not, point at the checkout:

```json
{
  "mcpServers": {
    "showrunner": {
      "command": "python",
      "args": ["-m", "showrunner.mcp_server"],
      "env": { "PYTHONPATH": "/full/path/to/showrunner-agent-skills/engine" }
    }
  }
}
```

## Claude Code

```
claude mcp add showrunner -- showrunner-mcp
```

## Cursor

Put the same `mcpServers` block as above in `.cursor/mcp.json` in your project, or in `~/.cursor/mcp.json` for every project.

## Gemini CLI

Put the same `mcpServers` block in `~/.gemini/settings.json`.

## Any other client

Anything that can start a program and talk to it over stdio can use it: the command is `showrunner-mcp`, or `python -m showrunner.mcp_server` with `PYTHONPATH` set to the `engine` folder.

## ChatGPT

ChatGPT connects to a remote server over HTTPS, so you need to expose the HTTP mode. In ChatGPT the place for this is Settings, Connectors, Advanced, Developer Mode (a beta feature), then Create with a server URL. This was documented as of November 2026 (`showrunner facts --id tooling.chatgpt.mcp`) and may have changed.

```
showrunner-mcp --http 8765 --path /mcp-a-long-random-string --token YOUR_SECRET
```

Then put an HTTPS tunnel or a small reverse proxy in front of port 8765 and give ChatGPT the public URL.

**Please read this before you rely on it.** The HTTP mode is tested with `curl` and with the test suite in this repository. It has **not** been tested against ChatGPT. It supports a bearer token, not OAuth, and a ChatGPT connector screen may ask for something it does not offer. If so, the safest setup is a long random `--path` as the secret with the default read-only surface, and nothing sensitive on the machine. If it does not connect, open an issue with the error text.

What the HTTP mode does to stay safe by default:

- it binds to `127.0.0.1` unless you pass `--host`
- it exposes only the read-only tools, not the ones that save to your disk (add `--stateful` for a single trusted user)
- it never reads files from the server's disk
- it checks the `Origin` header, and `--allow-origin` adds trusted ones
- it answers `GET` with 405, notifications with 202, and returns 401 without the token

If you would rather not run a server, use the zip upload in [docs/chatgpt.md](../docs/chatgpt.md). The skills carry the whole method.

## Check that it works

```
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | showrunner-mcp
```

You should get a JSON line with the tool list. `showrunner doctor` checks the data files and the skills folder.
