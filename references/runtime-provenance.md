# Vendored Runtime Provenance

The code under `scripts/runtime/spider_xhs_core` is a vendored Spider_XHS-derived
runtime used for request signing and read-only PC research calls.

The original import did not record an upstream repository URL, commit, or license.
Until that provenance is supplied and reviewed, treat the runtime as third-party code:

- Do not modify or redistribute it independently of this project.
- Do not expand the CLI allowlist without a security and compliance review.
- Verify its checked-in files with `python scripts/verify_runtime.py` before a release.
- Review and regenerate `scripts/runtime/MANIFEST.sha256` whenever an intentional
  runtime update is accepted.

Creator and no-watermark code may exist inside the vendored tree for historical
reasons, but `scripts/xhs_api_tool.py` does not import or expose those surfaces.
