# Unified Local Workplace Skills Store Design

Date: 2026-07-22
Status: Approved

## Objective

Provide every supported AI agent on this Windows laptop with immediate access to the same current workplace skills, while retaining GitHub history and eliminating stale duplicate copies.

## Architecture

Use C:UsersUSERWorkplace-Skills as the canonical Git checkout of nixonwongcl-hash/workplace-skills.

Each supported agent keeps its normal skill root. Only the 11 workplace skill directories inside that root are replaced with Windows directory junctions pointing to the matching canonical folders. Agent-specific and third-party skills remain untouched.

GitHub is the durable remote source and audit history. Local edits are immediately visible through every junction. Pulling updates changes every agent view at once. Publishing remains explicit and occurs only after validation.

## Components

1. Canonical Git checkout containing the root skill folders, version manifest, verification tool, and sync/link management tool.
2. Machine-readable agent target configuration listing installed skill roots.
3. Link manager that discovers supported roots, backs up existing workplace skill directories, creates or repairs per-skill junctions, never replaces an entire agent skill root, and supports audit and restore operations.
4. Version validation that checks every canonical SKILL.md against skill_versions.json.
5. Update workflow that fetches GitHub, fast-forwards the canonical checkout, validates, and reports the active versions.

## Supported Initial Targets

- Codex: C:UsersUSER.codexskills
- Claude Code: C:UsersUSER.claudeskills
- Shared agent skills: C:UsersUSER.agentsskills
- Antigravity project agents: C:UsersUSER.geminiantigravityplaygroundazure-radiation.agentsskills

Additional agents can be added through configuration without changing the link manager.

## Data Flow

1. GitHub changes are pulled into the canonical checkout.
2. Validation confirms the manifest and skill metadata agree.
3. Every agent reads the same canonical folders through junctions.
4. An agent editing a linked skill changes the canonical file immediately.
5. Before publication, validation runs and the affected semantic version must be incremented.
6. Approved changes are committed and pushed to GitHub.

## Safety and Recovery

- Existing workplace skill directories are moved into a timestamped backup before junction creation.
- Existing junctions are inspected before changes.
- The manager refuses to replace unknown files outside the configured 11 skill names.
- Failed validation prevents GitHub publication.
- Restore mode removes managed junctions and returns the latest backup.
- No automatic force-push, destructive reset, or deletion of agent-specific skills.

## Testing

- Dry-run reports all planned changes.
- Link audit confirms every target resolves to the canonical folder.
- Version checker passes across all 11 canonical skills.
- Representative edits made through one agent path appear through all other agent paths.
- Git status confirms the canonical checkout records the edit.
- Restore test confirms a backed-up local folder can be recovered.

## User-Facing Setup

Provide a reusable prompt instructing another agent to locate the canonical checkout, add its skill root to the target configuration, run a dry-run, create per-skill junctions with backups, and verify all versions.