# Read-Only API Index

`scripts/xhs_api_tool.py` exposes only the PC research methods below. The allowlist is
enforced in code; methods present in the vendored runtime but absent here cannot be
called through the CLI.

## CLI

List allowed methods:

```bash
python scripts/xhs_api_tool.py list --namespace pc
```

Secret-bearing payloads must be supplied through standard input:

```bash
printf '%s' "$PAYLOAD_JSON" | python scripts/xhs_api_tool.py call pc get_note_info --params-stdin
```

Inline `--params` remains available only for non-secret payloads. `--params-file` is
also supported; callers are responsible for giving the file private permissions.

## Allowed PC Methods

- `get_homefeed_all_channel`
- `get_homefeed_recommend_by_num`
- `get_note_info`
- `get_note_out_comment`
- `get_search_keyword`
- `get_user_info`
- `get_user_note_info`
- `get_user_self_info2`
- `search_note`
- `search_some_note`
- `search_some_user`
- `search_user`

## Blocked Surfaces

- Creator publishing and media upload
- Private messages, notifications, likes, and connection feeds
- Unbounded all-comment helpers
- No-watermark image and video helpers
- Any method not explicitly included in the allowlist

The wrapper applies a default 20-second HTTP timeout. The collection client applies a
60-second subprocess timeout and retries read-only failures twice with bounded backoff.
