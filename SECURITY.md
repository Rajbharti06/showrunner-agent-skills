# Security

Showrunner runs on your own machine. The engine makes no network calls, has no dependencies, and never posts anywhere. Its saved state (profile, playbook runs, experiment logs) is plain JSON in `~/.showrunner`, or the folder in `SHOWRUNNER_HOME`.

## The MCP server

- **stdio** (default) does not read files from disk unless you set `SHOWRUNNER_MCP_FILES=1`.
- **HTTP** (`--http PORT`) binds to `127.0.0.1`, exposes only the read-only tools, never reads files, checks the `Origin` header, and requires `Authorization: Bearer TOKEN` when a token is set. It does not implement OAuth. `--stateful` lets the server write to the local folder and is for a single trusted user only. Do not expose it to the internet without a token and a long random `--path`.

## Reporting a problem

If you find a vulnerability, please open a private security advisory on GitHub (Security tab, "Report a vulnerability") instead of a public issue. Include the version, how to reproduce it and what you think the impact is. The maintainer will reply as soon as they can.

Not a vulnerability, but please do tell us: a skill that asks an assistant to do something unsafe, or a tool that reads or writes more than it says it does.
