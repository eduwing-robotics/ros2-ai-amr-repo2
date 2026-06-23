# Ops Harness Tech Ref

Claude/Codex skill harness, intake routing, evidence, doc sync 작업의 빠른 진입점이다.

## Read First

1. `AGENTS.md`
2. `.claude/commands/intake.md`
3. `.claude/skills/README.md`
4. `.claude/skills/task-intake-router/SKILL.md`
5. `docs/ref/TECH-INDEX.md`

## Current Harness Shape

- Root entry files stay short: `AGENTS.md`, `AGENT.md`, `CLAUDE.md`, `ai-context/START-HERE.md`.
- `.claude/skills/README.md` chooses operational skills.
- `docs/ref/TECH-INDEX.md` chooses technology refs.
- Skill bodies should stay short; long procedures move to `references/`.
- Technology refs should stay short; source-of-truth details stay in `docs/ref/*`, `docs/status/*`, scripts, or skill references.

## Verify

- `task-intake-router` can name one technology ref for a clear request.
- `TECH-INDEX.md` links every file in `docs/ref/tech/`.
- `rg -n "docs/ref/TECH-INDEX|docs/ref/tech/UNITY" AGENTS.md AGENT.md CLAUDE.md ai-context/START-HERE.md .claude/skills docs/ref docs/status` shows the routing is discoverable.
- Evidence Status is updated before completion.
