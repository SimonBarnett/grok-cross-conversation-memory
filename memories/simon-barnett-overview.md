# Simon Barnett — Overview Memory

Persistent context for Simon Barnett (SimonBarnett on GitHub, si@medatechuk.com, UK, Medatech UK).

## Who he is

- Software developer and founder of Medatech UK (dev.medatechuk.com).
- Long-time GitHub user (account since 2012, 55+ public repos).
- SuperGrok subscriber; works with Grok via voice and text.
- Based in the UK; timezone Europe/London.

## Technical profile

- **Primary stack**: Python, Flask web apps, JavaScript front-ends.
- **Notable project**: clubmadeira.io — a Flask-based web app with permission-based routing, user management, role-based pages, and integrations with Amazon and Wix APIs. Blueprints include authentication, content, manager, referral, role_pages, site_request, user_settings, and utility (endpoints: system_stats, ping, log_user_activity, send_sms, render_md, check_domain).
- **Front-end**: modular JavaScript (admin-page.js, community-page.js, admin-events.js, login-page.js, go.js and related files); actively refactors and debugs script loading and terminal errors.
- **AI integration**: uses the xAI/Grok API (console.x.ai, https://api.x.ai/v1); has explored feeding code into API sessions, handling the ~20,000-character per-request limit by chunking, and building session-aware workflows.
- **Data formats**: works with JSON schemas, project manifests (name, description, base_url, main_file, github, files, version, dependencies, technologies), and structured payloads for things like finite capacity planning (labor hours, machine capacity, work cells, routings, tooling availability).

## Working style and preferences

- Prefers concise, direct answers; dislikes filler and over-long responses.
- Values continuity across sessions — this is exactly why he built the grok-cross-conversation-memory repo: memories should be committed on a branch and opened as a PR against main for review before merging, never saved only locally.
- Comfortable with large code pastes (half a megabyte handled fine) and breaking work into chunks when needed.
- Interested in AI, long-term tech trends (fusion, space exploration), and sci-fi — notably the Bobiverse series by Dennis E. Taylor.
- Thinks in terms of protocols and shorthand for recurring tasks (e.g., XREQ transfer-request prompts with sections like Current Requirement and code changes, plus crash-handling).

## Notes from our conversations

- (Add notes here as we discuss.)

## Session notes — 2026-09-27 (SysTray / AgentMonitor FR work)

- **FR #150** (AgentMonitor, open): "tray overspend — read Grok/Cursor pools from the local machine." Tray overspend figure should be sourced from the local machine's Grok and Cursor usage pools rather than whatever source it uses today. Tray-side sourcing change only — the publish path for overspend data is untouched (still available for other consumers). Local pool paths: Grok under `%USERPROFILE%\.grok\agent-health\`, Cursor under its local state. Acceptance: tray overspend reflects local Grok pool; reflects local Cursor pool; published overspend output unchanged; no secrets or tokens committed, local paths only. Updated 2026-09-27 with a note clarifying tray-side-only scope and that FR #148 is now closed.
- **FR #148** (AgentMonitor, closed 2026-09-27, completed): SysTray dialog reset countdown in days/hours/minutes instead of a date. Label format "Until reset: {days} days, {hours} hours, {minutes} minutes" (omit zero components); clamp negative to zero; hide the reset line entirely when the pool has been polled since the reset (percentage still shown); no polling added — formatting only from the known reset timestamp. Implemented in owning TipForm repo: https://github.com/SimonBarnett/agentic_build/pull/422 (`Format-BobResetLabel` countdown), MRB PASS. Seat: marchhare-14764. Comments on #148 record the implementation link and the close reason.
- **FR #149** (AgentMonitor, open): tray Agents menu — the two watch-seat icons (Cursor, Grok) collapsed into one SysTray context-menu item called **Agents**; submenu to select which. Icon = same as the Desktop shortcut (`Icon.ExtractAssociatedIcon` on `Cursor.exe` / `Grok Bot.exe`). Not installed → greyed icon, still clickable, click initialises setup (`tools/Install-AgentMonitor.ps1 -Agent <kind>`); installed → click launches `Desktop\Watch-AgentHealth\Watch-AgentHealth.cmd <cursor|grok>`. Dropdown rebuilds on `DropDownOpening`; one NotifyIcon, no second dialog. Setup ships via skill harvest: new skill `agent-monitor-setup` in `~/.grok/skills`, referenced from `harvest-agent-skills` and `bob-fleet-tray`. Test-Pack BT0 skills + BT0l traySrc assertions added. Implementation was complete on branch `cursor/tray-agents-menu-e6a6` (commit `5a6c587`) but the Cursor cloud agent could not push (403 to `SimonBarnett/agentic_build.git` — its GitHub App install only covers `agentic_irc`); posted as an issue instead. Ask: grant the Cursor GitHub App write access to AgentMonitor (or run a Cloud Agent on `agentic_build`) and open the draft PR. Acceptance: A1 Agents menu with Cursor + Grok; A2 installed icon matches Desktop shortcut, click launches watch seat; A3 not-installed greyed, click initialises setup; A4 agent-monitor-setup skill in `.grok/skills`, BT0 list, harvest-agent-skills; A5 Test-Pack BT0l asserts above; A6 no UAT stamp, harvest as PR not commit to main. Verified PowerShell 7.4.6 parse OK; full Test-Pack + tray UI still need a Windows smoke test. Docs: `docs/feature-request-tray-agents-menu-2026-09-23.md`, `docs/build-and-test-plan-tray-agents-menu-2026-09-23.md`, `docs/skill-harvest-log.md` entry.
- **Related closed systray FRs in agentic_irc** (all completed 2026-09-23): #186 usage-dialog polish (missing icons, ? hover, quota for /anmy model 0, overspend aligned with cursor logo on the right, machine names ALLCAPS); #182 xai/cursor icon disappeared from systray — add back; #179 ? next to each cursor quota group showing group description + included models, 0% shown not n/a, Grok systray data via GET to the digest every minute.
- **Tooling context**: AgentMonitor repo = `SimonBarnett/AgentMonitor` (Watch-AgentHealth.ps1, tools/Watch-AgentWatcher.ps1, tray shortcuts, Watch-BobTray.ps1). Bob Fleet tray = `tools/Watch-BobTray.ps1`, skill `bob-fleet-tray`; not a Windows service — recycle the tray after menu code changes. Watch seats live under `Desktop\Watch-AgentHealth`. Install log: `~\.grok\long-running-background-tasks\install_agent_monitor.log`. Hard rules from the tray Agents FR: do not point a watch seat at a forbidden IRC home (tray only passes cursor/grok, AgentMonitor picks the watch home); no secrets; no UAT stamp.
- **Correction from this session**: when asked to "update the feature request," the wrong issue was initially updated (#150 instead of the intended one) — always confirm which FR number before editing.
