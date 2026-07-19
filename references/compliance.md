# Compliance Boundaries

Use this skill only for authorized or otherwise permitted data handling.

Rules:

- Require the user to provide authorization for live collection.
- Keep default collection small. The first version caps keyword collection at 50 notes.
- The high-level workflow also caps queries at 8, notes per query at 10, and normalized comments per note at 100.
- Do not add proxy pools, anti-detection logic, mass-account workflows, spam, or resale-oriented exports.
- Do not collect sensitive personal data unless it is strictly necessary and authorized.
- When collecting comments, keep only fields required for analysis and avoid exporting unnecessary profile data.
- Do not download media by default. Store media URLs unless the user explicitly has rights and asks for downloads.
- Do not include automated publishing in this skill. Creator publishing is outside the report tool and blocked by its CLI allowlist.
- Treat AI-generated titles, copy, tags, cover text, and image ideas as drafts. Require human review for factual accuracy, rights, advertising claims, and platform rules before publication.
- Do not fabricate first-hand experience, research evidence, product efficacy, user sentiment, or platform-wide trend claims. Clearly label creative suggestions and uncertainty.
- The CLI enforces a read-only research method allowlist; publishing, media upload, private notification, and no-watermark methods are blocked.
- Keep sanitized raw JSON outputs for auditability. Store all run artifacts with private filesystem permissions and purge retained raw files when no longer needed.
