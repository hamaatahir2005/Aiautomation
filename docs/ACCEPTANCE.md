# Acceptance and release status

This is an implemented desktop development release, not a claim that every production integration has been validated.

| Requirement | Evidence / limit |
| --- | --- |
| Desktop and installer | Windows Actions builds PyInstaller backend + Electron NSIS installer. A successful final workflow, including installation and actual desktop UI checks, is required. |
| Interactive office | Real Three.js scene, animated employees, selectable departments, camera rotation/zoom. Local Chromium regression passed against the actual backend. Windows test exercises the installed app. |
| Agent execution | OpenAI-compatible HTTP tasks, structured manager plans, explicit approval before delegation, persisted states and owner department permissions. Provider calls require a model/key or running Ollama; no live provider credential was supplied. |
| Video | Actual FFmpeg MP4 production and decode validated by integration test. Optional Whisper transcription, scene detection, speech-rich selection, silence selection, crop/resize, normalized audio, fade, owner-licensed music, preview, editable JSON/SRT. Model weights and language accuracy require live validation. |
| Lead research | Authorized Brave Search API, source URLs/dates, deduplication, optional evidence-based AI relevance scoring, CSV/XLSX. API contract/dedup tests use controlled responses; no live search key was supplied. Results are research evidence requiring review, never invented verified customers. |
| Contacts | Manual editing/deletion, CSV/XLSX, duplicate email handling, search, explicit consent evidence, unsubscribe. Imported lists do not establish consent. API and UI persistence tests passed locally. |
| Gmail | STARTTLS SMTP, Windows WinVault secret storage, test/send endpoints, optional read-only IMAP sync. SMTP ordering and secret isolation tested with a transport double; live Gmail connection/send requires owner App Password and authorized test recipient. |
| Campaigns | Draft/preview/approval, timezone-aware scheduling, consent recheck, global pacing across restart, target <=300, provider-error pause, durable delivery history, unsubscribe suppression. App must remain open and unlocked. No system service. |
| Inbox | Optional IMAP fetch of last 100 messages, known-customer matching, rule-based reply classification, interested flags, unsubscribe processing, AI response drafts. Exact human approval is required for outgoing responses, with duplicate-reply protection. Not a complete mailbox or guaranteed bounce parser. |
| Sales and support | Catalog, deal statuses, customer-linked records, proposal drafting, reminders, invoice PDF, conversations and human takeover status. Confirmed payments must be separately recorded in Finance. |
| Marketing | AI content drafts, local calendar/content records. Official Mastodon API supports owner-approved scheduled public posts, persisted publication status and idempotency keys. Live publication requires an owner access token. Other platforms require their own official adapters. |
| Finance/analytics | Integer accounting amounts, separate USD/IQD totals, recorded payments/expenses with evidence, date-filtered activity, CSV exports. No automatic payment processor verification, invented exchange rates or earnings. |
| Security | Local owner password, authenticated loopback bridge, sandboxed renderer, credential revocation, owner permissions, audit trail, rate limiting, bounded files and formula-safe exports. Local disk encryption remains an OS responsibility. |
| Persistence | SQLite connection disposal/reopen test and real UI writes passed locally. Installed Windows test restarts the actual application and verifies the saved customer. |

Local checks: **19 passed, 1 Windows-only test skipped**; TypeScript/Vite build passed; Chromium UI smoke passed. Windows WinVault and installed-app acceptance passed on the Windows runner for commit 7950b18; the final workflow must also pass for the additional social and response workflows.

Known scope: optional PostgreSQL/Redis are not configured, social platforms beyond the Mastodon adapter are not connected, asynchronous work stops when the application closes, no code-signing certificate is supplied, and no live Gmail/AI/search credential was supplied. All external activity and revenue counts originate in stored application events; SMTP acceptance indicates server acceptance, not proof of delivery or sales.
