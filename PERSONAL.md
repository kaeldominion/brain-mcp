# Personal 2nd Brain — local, no server

The MCP server exists to let **multiple agents share one vault safely** (tokens, permissions, locking, audit). A personal brain — one human, one agent, one machine — has none of those problems, so it needs none of that machinery. Run it as plain local files next to your agent.

## Setup (2 minutes)

1. Copy the vault template somewhere your agent can read and write:

```bash
git clone --depth 1 https://github.com/kaeldominion/brain-mcp /tmp/brain-mcp
cp -r /tmp/brain-mcp/vault-template ~/2nd-brain-personal
rm -rf /tmp/brain-mcp
```

2. Give your agent (Hermes skill / project instruction) this:

> You maintain my personal 2nd Brain: an Obsidian vault at `~/2nd-brain-personal`, accessed directly on the filesystem.
> Read `_System/AI Agent Instructions.md` and follow its content rules — templates for entity notes, wikilink everything, one note per entity via the Entity Index, preserve sources and dates, no secrets in the vault.
> Search the vault before answering questions about my life/work; read a note before editing it.
> If the vault is empty or I ask, run the interview in `_System/Onboarding Protocol.md` — one question at a time, creating notes as I answer.

3. Optional backup (recommended) — same pattern as the server, one private repo you own:

```bash
cd ~/2nd-brain-personal && git init -b main && git add -A && git commit -m "start"
git remote add origin git@github.com:YOU/personal-brain-backup.git && git push -u origin main
# then commit+push periodically (cron, launchd, or ask your agent to do it after big updates)
```

Open the folder in Obsidian any time — it's your data, in markdown, on your disk.

## When to upgrade to the server

The moment any of these become true, lift the same vault into a full install (`./brain setup`, then move your files into the vault directory — they're identical formats, nothing to convert):

- a second agent or a second machine needs the same brain
- your agent runs on a VPS but you want the vault backed up/managed properly
- you want per-client permissions, audit history, or hash-guarded concurrent writes

Company brains should **always** be the server — never share one local folder between people or agents.
