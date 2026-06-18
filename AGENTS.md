# Agent Instructions

Before starting any development, debugging, review, or documentation task in this repository:

1. Read `DEVELOPMENT_PROMPT.md`.
2. Read `SYSTEM_OVERVIEW.md`.
3. Read `docs/GITHUB_COLLABORATION_WORKFLOW.md`.
4. Read `docs/README.md` to choose the right project, Agent, video, data, operations, deployment, handoff, or archive document for the task.
5. If the user asks for code review, PR review, teammate commit review, professor review preparation, or change inspection, read `docs/CODE_REVIEW_PROMPT.md` before giving findings.
6. If the task touches Agent architecture, MCP/tool execution, Task-Plan-Goal flow, specialist personas, evidence routing, video observations, or judgment contracts, read `docs/agent/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md`.
7. Follow the workflow, architecture boundaries, security rules, verification policy, documentation sync rules, and GitHub collaboration rules defined in those files.

## Operating Rules

- Treat `DEVELOPMENT_PROMPT.md` as the source of truth for how development work should be performed.
- Treat `SYSTEM_OVERVIEW.md` as the source of truth for the current project structure, key files, resources, and known issues.
- Treat `docs/GITHUB_COLLABORATION_WORKFLOW.md` as the source of truth for branch, PR, merge notification, and teammate synchronization rules.
- Treat `docs/README.md` as the document map for selecting the right detailed reference before work.
- Treat `docs/CODE_REVIEW_PROMPT.md` as the source of truth for review stance, severity, verification, and output format when the user requests a code review or change inspection.
- Treat `docs/agent/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md` as the working roadmap for Agent/MCP/Task-Plan-Goal restructuring work. If new required work appears during that effort, add it to the correct phase in that document before continuing.
- Before starting work, check the latest `main` and recent merge/commit history as described in `docs/GITHUB_COLLABORATION_WORKFLOW.md`.
- If a change modifies service boundaries, API routes, DTOs, DB schema, Redis keys, storage paths, external integrations, environment variables, execution steps, or known issues, update `SYSTEM_OVERVIEW.md` in the same task.
- If a change modifies development workflow, role definition, verification policy, documentation sync rules, security policy, freshness rules, or service responsibility boundaries, update `DEVELOPMENT_PROMPT.md` in the same task.
- If a change modifies GitHub branch, PR, merge notification, conflict handling, or teammate synchronization rules, update `docs/GITHUB_COLLABORATION_WORKFLOW.md` in the same task.
- Never print or document real secrets such as `.env` values, API keys, JWT secrets, internal service tokens, user passwords, or refresh tokens.
