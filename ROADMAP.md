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

## Phase 6 — plugins and recovery (prototype + initial GUI integrated)
- Implemented: local plugin registry with explicit approval, per-plugin permission grants, disabled-by-default state, and no plugin execution.
- Implemented: versioned file backups with SHA-256 verification, explicit restore confirmation, and atomic destination replacement.
- Implemented: plugin manifest path validation against native and Windows absolute/traversal paths.
- Still to do: process isolation/sandbox, UI for permissions and recovery history, safe installation from trusted sources, and real-world recovery tests.

## Phase 7 — Android and remote access (session primitives implemented)
- Implemented: one-time pairing code, bounded pairing/session TTL, least-privilege permission map, command allowlist, attempt rate limiting, session revocation, and bounded audit events that never store session tokens.
- Intentionally not implemented: network listener, remote screen streaming, Android app, real mouse/keyboard execution over the network, or internet-facing service.
- Still to do: Android client, encrypted authenticated transport, private VPN setup guidance, integration with desktop consent prompts, device management UI, threat-model review, and end-to-end tests on real devices.
- Do not expose a public internet listener or treat the transport-agnostic session module as a complete remote-control system.

## Validation status
- Unit tests are included and run in GitHub Actions on Windows and Linux. Check the latest workflow result before treating a change as validated.
- UI interaction and mouse/keyboard actions still require real-device testing on the user’s Windows PC.
- Desktop UI, Android connectivity, GPU metrics, AI providers, and Roblox Studio integration still require implementation and real-device testing.


## Phase 4 — AI hybrid (initial provider layer implemented)
- Implemented: provider abstraction for local Ollama and OpenAI-compatible chat APIs.
- Implemented: credentials are read from environment variables; no API keys are stored in the repository.
- Implemented: role/content validation, message-size limits, request timeout, response-size limit, and sanitized connection errors.
- Implemented: text-only replies; model output is never executed as a command or applied to files.
- Still to do: OS credential vault, provider selection UI, local model installation guidance, and explicit approval workflow integrated into the app.

## Phase 5 — Roblox Studio Lab (read-only prototype implemented)
- Implemented: read-only scanning of .lua/.luau files with file count/size limits and no script execution.
- Implemented: initial heuristic findings for wait(), loadstring(), FireServer(), OnServerEvent, GetAsync(), and LocalPlayer context.
- Implemented: unified diff preview for proposed text changes; preview does not write to disk.
- Still to do: richer Luau parser/type diagnostics, Studio plugin bridge, backup-before-apply workflow, and project-specific testing.
- Use Roblox Studio's supported workflows; no exploit executor or game-cheat functionality.

## Phase 6–7 implementation notes
The modules `blackcore_core/plugin_manager.py`, `blackcore_core/versioned_backups.py`, and `blackcore_core/remote_sessions.py` provide testable primitives only. Plugin activation does not execute code. Remote sessions are in-memory and transport-agnostic; the Android app and secure network transport remain unbuilt. Passing unit tests does not equal Windows/Android device validation.
