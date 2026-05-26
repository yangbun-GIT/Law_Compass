# Agent Instructions

Before starting any development, debugging, review, or documentation task in this repository:

1. Read `DEVELOPMENT_PROMPT.md`.
2. Read `SYSTEM_OVERVIEW.md`.
3. Read `docs/GITHUB_COLLABORATION_WORKFLOW.md`.
4. Follow the workflow, architecture boundaries, security rules, verification policy, documentation sync rules, and GitHub collaboration rules defined in those files.

## Operating Rules

- Treat `DEVELOPMENT_PROMPT.md` as the source of truth for how development work should be performed.
- Treat `SYSTEM_OVERVIEW.md` as the source of truth for the current project structure, key files, resources, and known issues.
- Treat `docs/GITHUB_COLLABORATION_WORKFLOW.md` as the source of truth for branch, PR, merge notification, and teammate synchronization rules.
- Before starting work, check the latest `main` and recent merge/commit history as described in `docs/GITHUB_COLLABORATION_WORKFLOW.md`.
- If a change modifies service boundaries, API routes, DTOs, DB schema, Redis keys, storage paths, external integrations, environment variables, execution steps, or known issues, update `SYSTEM_OVERVIEW.md` in the same task.
- If a change modifies development workflow, role definition, verification policy, documentation sync rules, security policy, freshness rules, or service responsibility boundaries, update `DEVELOPMENT_PROMPT.md` in the same task.
- If a change modifies GitHub branch, PR, merge notification, conflict handling, or teammate synchronization rules, update `docs/GITHUB_COLLABORATION_WORKFLOW.md` in the same task.
- Never print or document real secrets such as `.env` values, API keys, JWT secrets, internal service tokens, user passwords, or refresh tokens.
