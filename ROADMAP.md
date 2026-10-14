# BLACKCORE ULTIMATE — roadmap

This roadmap is a plan, not a claim that every capability already exists.

## Phase 1 — reliable local foundation
- Preserve the existing Tkinter application and launcher.
- Add modular read-only metrics, explicit action authorization, local backup/restore helpers, plugin manifest validation, and unit tests.
- CI compiles the Python modules and runs unit tests on Windows and Linux.

## Phase 2 — desktop controls (partially implemented)
- Implemented: local mouse movement and left-click at validated screen coordinates, each with visible confirmation.
- Implemented: allowlisted keyboard actions (Enter, Esc, Tab, Space, Ctrl+C/V/Z/S, Alt+Tab), with confirmation for each action.
- Implemented: disk usage in the UI and optional cumulative network counters when `psutil` is installed.
- Still to do: task/process controls with allowlists, cancellation, and real-device testing of mouse/keyboard behavior.
- Administrative operations remain out of scope unless explicitly opted into; never elevate privileges silently.

## Phase 3 — monitoring (partially implemented)
- Implemented: compact in-interface text sparklines for recent CPU/RAM/disk samples, with bounded history.
- Implemented: disk usage and optional cumulative network counters when `psutil` is installed.
- Still to do: full historical charts and network throughput history.
- GPU/game metrics still require a selected, documented provider; show “unavailable” when unsupported.
- Avoid promising universal GPU metrics without compatible hardware/drivers.

## Phase 4 — AI hybrid
- Add provider abstraction for local and hosted models.
- Store API credentials only in local OS-protected configuration or a backend secret store; never commit credentials.
- Require confirmation before AI-proposed commands modify files, launch processes, or change system settings.

## Phase 5 — Roblox Studio Lab
- Project inspection, Luau diagnostics, test plans, and proposed patches.
- Back up files before changes and show diffs before applying them.
- Use Roblox Studio's supported workflows; no exploit executor or game-cheat functionality.

## Phase 6 — plugins and recovery
- Validate plugin manifests and permission requests before installation.
- Run third-party plugins in an isolated process/sandbox before enabling them.
- Maintain versioned backups and require explicit confirmation for restoration or repair.

## Phase 7 — Android and remote access
- First build a LAN pairing flow with one-time pairing, device revocation, session expiry, and least-privilege commands.
- Remote-from-anywhere access must use a secure transport, authenticated pairing, rate limits, audit logs, and no exposed unauthenticated control port.
- Do not ship a public internet listener or pretend that LAN-only code is internet-ready. Validate the threat model and setup before enabling this phase.

## Validation status
- Unit tests are included and run in GitHub Actions on Windows and Linux. Check the latest workflow result before treating a change as validated.
- UI interaction and mouse/keyboard actions still require real-device testing on the user’s Windows PC.
- Desktop UI, Android connectivity, GPU metrics, AI providers, and Roblox Studio integration still require implementation and real-device testing.
