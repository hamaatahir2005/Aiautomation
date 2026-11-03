# Installation and operation

1. Use a successful Windows installer workflow artifact; verify its SHA256 against `SHA256.txt`.
2. Run `AI-Company-OS-Setup.exe` on Windows 10/11 64-bit. Choose installation directory.
3. Open AI Company OS and create your local owner password (12+ characters).
4. Open Settings and configure an OpenAI-compatible provider, or Ollama with a downloaded model at `http://127.0.0.1:11434/v1`.
5. For Gmail, enable Google 2-Step Verification and generate a separate App Password. Enter Gmail address and that App Password, test, then save. Your main Google password is never needed. Availability is determined by Google account policy.
6. Send a test only to a recipient who authorized it.
7. Add contacts or import a CSV/XLSX containing `name,email,country,industry`. Imported records have no marketing consent. Record real permission and its evidence before selecting campaign recipients.
8. Create a campaign draft, review the content and recipients, and approve it. Keep the app running for scheduled work. Sending is globally paced and pauses on provider errors; Google limits may be lower than your configured target. Do not use discovered lead addresses as consent.
9. Record payments and expenses with receipt/payment references. USD and IQD totals remain separate; no exchange rate is invented.

Local data: `%APPDATA%/AI Company OS/data/company.db`, uploads and exports in adjacent directories. Credentials: Windows Credential Manager under `AI Company OS`. Back up the data directory while the app is closed. Restoring data does not restore credentials: reconnect on the destination device.

## Troubleshooting

- Backend failed to launch: verify Windows x64, available disk space and write access to the app data directory. Check antivirus quarantine. Rebuild with the supplied workflow if files are missing.
- AI task failed: verify endpoint, model availability, key and provider quota. Retry explicitly; failed jobs never create sales or revenue records.
- Gmail test failed: verify a Google App Password, 2-Step Verification, account restrictions, firewall and access to smtp.gmail.com:587 with STARTTLS. A normal account password will not work.
- Campaign paused: inspect the delivery error type. Check Gmail Sent Mail and provider limits before resuming. Interrupted sends are marked uncertain and are never automatically resent.
- Video failed: verify that the input is playable and unencrypted, install the video requirements for source development, and check the local `exports/video-ID.log`. First transcription requires model download access. Sorani accuracy requires owner review.
- Scheduled tasks wait while the application is closed. Opening the application resumes due work after owner unlock; there is no Windows background service.
- Password forgotten: there is no remote password reset. Back up data before an intentional local reset. Protect the Windows user account and disk with OS access controls and BitLocker.

## Database migrations

The backend applies schema version 1 on first launch and records it in `schema_migrations`. `backend/migrations/001_initial.sql` is the reviewable initial SQLite schema. Do not manually rerun it on an existing database. Future schema changes must add a new versioned migration and preserve the existing owner, consent ledger and delivery states. SQLite/PostgreSQL data migration is not automatic in this release.

## Optional official social publishing

Connect your Mastodon server's HTTPS origin and your own access token in Settings. Use a token with `write:statuses` permission and account verification access. Create and review Marketing content, choose a publish time, and approve the exact content. The app must remain running and unlocked. Provider responses supply the actual post ID/URL; failed or interrupted publication is marked for owner review and is not blindly retried. Other social networks are not connected by this adapter.
