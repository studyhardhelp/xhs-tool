# Compliance Boundaries

Use this skill only for authorized or otherwise permitted data handling.

Rules:

- Require the user to provide authorization for live collection.
- Keep default collection small. The first version caps keyword collection at 50 notes.
- Do not add proxy pools, anti-detection logic, mass-account workflows, spam, or resale-oriented exports.
- Do not collect sensitive personal data unless it is strictly necessary and authorized.
- When collecting comments, keep only fields required for analysis and avoid exporting unnecessary profile data.
- Do not download media by default. Store media URLs unless the user explicitly has rights and asks for downloads.
- Do not include automated publishing in this skill. Keep creator publishing separate from reporting workflows.
- Keep raw JSON outputs for auditability, but avoid exposing cookies in generated artifacts.
