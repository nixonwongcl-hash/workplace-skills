# Unified Local Workplace Skills Store Implementation Plan

## Requirements Summary

- Use C:UsersUSERWorkplace-Skills as the single canonical Git checkout.
- Expose the 11 canonical workplace skills to Codex, Claude Code, shared agents, and Antigravity.
- Preserve all unrelated agent-specific skills.
- Eliminate manual skill copying and stale version drift.
- Back up every replaced workplace skill folder before linking.
- Pull GitHub updates automatically without overwriting local edits.
- Provide audit, repair, restore, and validation commands.
- Deliver a reusable prompt for onboarding other agents.

## Acceptance Criteria

1. C:UsersUSERWorkplace-Skills is a valid checkout of nixonwongcl-hash/workplace-skills.
2. skill_versions.json validates all 11 canonical SKILL.md version declarations.
3. Each configured agent root contains 11 directory junctions resolving to the matching canonical folders.
4. Non-workplace skill folders remain unchanged.
5. Every replaced local folder exists in a timestamped backup.
6. Editing a canonical skill through any linked agent path is immediately visible through all other linked paths.
7. The updater performs only fast-forward pulls and refuses to pull when the canonical worktree is dirty.
8. Link audit exits nonzero for missing, incorrect, or non-junction workplace skill paths.
9. Restore mode removes only managed junctions and restores the selected backup.
10. A scheduled update check runs at user logon and periodically without force-resetting or auto-pushing.
11. Codex, Claude Code, shared agents, and Antigravity all pass installed-root version verification.
12. A reusable onboarding prompt is delivered to the user.

## Implementation Steps

1. Add agent_targets.json at the repository root.
   - Define stable target IDs, display names, and absolute skill-root paths.
   - Include Codex, Claude Code, shared agents, and Antigravity.
   - Keep target configuration editable for future agents.

2. Add scripts/manage_skill_links.py.
   - Implement audit, dry-run install, install, repair, and restore subcommands.
   - Read the 11 managed skill names from skill_versions.json.
   - Detect existing directories, files, symlinks, and junctions.
   - Move existing real workplace skill directories to timestamped backups.
   - Create one Windows junction per managed skill.
   - Refuse to touch names outside the manifest.
   - Persist migration metadata for deterministic restore.

3. Add scripts/update_workplace_skills.py.
   - Confirm the canonical checkout has no uncommitted changes.
   - Fetch origin and use git pull --ff-only.
   - Run scripts/verify_skill_versions.py.
   - Run link audit for every configured target.
   - Write a compact timestamped status log.
   - Never commit, reset, force-push, or resolve conflicts automatically.

4. Add scripts/install_update_schedule.ps1.
   - Register a per-user scheduled task at logon and every six hours.
   - Run the updater hidden.
   - Provide an uninstall switch.
   - Use the canonical checkout path explicitly.

5. Update README.md, CLAUDE.md, and .agents/AGENTS.md.
   - Declare the canonical local checkout.
   - Explain live junction behavior and version requirements.
   - Document audit, repair, update, restore, and schedule commands.
   - Tell agents to edit only through the canonical-linked path.

6. Validate before migration.
   - Parse all Python and PowerShell files.
   - Run skill version validation.
   - Exercise link management in temporary fixture directories.
   - Test backup, junction resolution, representative cross-path editing, audit failure, and restore.

7. Migrate the laptop.
   - Ensure the canonical checkout exists at C:UsersUSERWorkplace-Skills.
   - Run dry-run and review exact targets.
   - Install junctions with backups.
   - Audit all targets and verify installed versions.
   - Install the update schedule.
   - Start new sessions for each agent so skill discovery refreshes.

8. Publish.
   - Increment the repository update as needed without changing skill versions unless skill behavior changes.
   - Commit with Lore trailers.
   - Push the existing branch and update draft PR #1.
   - Report the canonical path, backup path, schedule, verification evidence, and remaining risks.

## Risks and Mitigations

- Junction support differs by agent: keep links per skill and validate discovery after new sessions.
- Local edits block pulls: updater reports a dirty worktree and takes no destructive action.
- Existing folders contain unique files: move complete folders into timestamped backups before linking.
- Scheduled task fails silently: write status logs and expose a manual update command.
- GitHub main does not yet contain PR #1: install from the validated branch initially, then switch canonical tracking to main after merge.
- OneDrive or antivirus interferes with junctions: canonical checkout stays outside OneDrive and audit detects broken links.

## Verification Steps

- Run verify_skill_versions.py against canonical and all configured roots.
- Run manage_skill_links.py audit and require zero mismatches.
- Resolve every junction target and compare it with the canonical folder.
- Modify and revert a temporary marker through one junction; confirm visibility through every other junction.
- Run update_workplace_skills.py with a clean tree and with a deliberately dirty tree.
- Test restore using temporary fixtures before any live restore.
- Query the scheduled task and confirm its next run time and last result.
- Confirm git status in the canonical checkout contains only intentional changes.