---
name: xhs-report
description: Use this skill when Codex needs to research, collect, normalize, analyze, or report on authorized Xiaohongshu/XHS note data. Supports natural-language workflow routing for travel planning, product review, content ideation, comment insight, viral-pattern analysis, single-note analysis, keyword note research, user note collection, raw Spider_XHS/XhsSkills JSON normalization, Markdown/Excel report generation, media URL indexing, and optional OpenAI-compatible token-platform summarization. Use only for user-authorized or otherwise permitted data handling, not for bypassing platform controls, bulk scraping, spam, resale, media misuse, or automated publishing.
---

# XHS Report

## Overview

Use this skill to turn authorized XHS note data into structured files and an analysis report.
The skill is intentionally business-oriented: understand the user's XHS research goal, collect or import raw data, normalize it into stable fields, then generate Markdown, spreadsheet, and optional media-index outputs.

## High-Level Workflows

For broad user requests, prefer `scripts/xhs_workflow.py --workflow auto` over manually chaining low-level scripts. The script infers the workflow from the user's natural-language topic and records `inferred_workflow` in `summary.json`.

- Travel planning: `--workflow travel-plan`
  Use for requests like “从小红书整理一份山东济南到锡林郭勒一家 3 口 5 日游攻略”.
- Product or brand review: `--workflow product-review`
  Use for product口碑、真实测评、避雷、竞品/平替整理.
- Content ideation: `--workflow content-ideation`
  Use for选题库、标题参考、内容角度、账号运营灵感.
- Comment insight: `--workflow comment-insight`
  Use when the user wants评论高频问题、情绪、痛点、FAQ、需求洞察.
- Viral pattern analysis: `--workflow viral-pattern`
  Use for爆款拆解、热门笔记共性、标题/标签/互动结构研究.

Default workflow outputs:

- `workflow_report.md`: user-facing research report.
- `notes.normalized.json` and note table: normalized sampled notes.
- `comments.normalized.json` and comment table: normalized comments when enabled.
- `media_index.json`: image/video URL index only; do not download media by default.
- `summary.json`: run metadata and output paths.
- Optional `llm_insights.md`: generated only with `--llm-insights` and configured token-platform environment variables.

After producing the report, proactively ask whether the user wants a follow-up package such as: deeper report refinement, note link library, comment FAQ, media URL index review, or authorized media download. Media download requires explicit confirmation of use rights and purpose.

When the user asks broad ranking questions like “当前最热门的话题是什么” or “最火的主播是谁”, frame the result as sampled XHS search evidence, not an official platform-wide ranking. Ask for a category or seed keyword if the request is too broad to sample responsibly.

## Workflow

1. Identify the input type:
   - Broad research/task request: use `scripts/xhs_workflow.py --workflow auto`.
   - Single note URL: use `scripts/collect_notes.py --mode note`.
   - Keyword research: use `scripts/collect_notes.py --mode keyword`.
   - User profile notes: use `scripts/collect_notes.py --mode user`.
   - Include comments only when needed: add `--include-comments`.
   - Existing raw JSON: use `scripts/normalize_xhs.py`.

2. Prefer existing raw JSON when available. Live collection uses the vendored `scripts/xhs_api_tool.py` runtime and requires a user-provided cookie string.

3. Normalize all raw data before analysis. Do not build reports directly from raw XHS response objects.

4. Generate reports with `scripts/build_report.py`. Use Markdown by default; use spreadsheet output when comparison or filtering matters.

5. For live collection, use a `run_id`. If `--out-dir` is omitted, `scripts/collect_notes.py` writes to `<skill-dir>/runs/<run_id>` and creates `summary.json`.

6. On completion, summarize only the useful outputs and next choices. Do not expose cookie values, raw request headers, or internal auth files.

## Auth UX And Secret Handling

Never show raw or redacted cookies in conversation unless the user explicitly asks for debugging output.
Do not paste `XHS_COOKIE` values into chat, logs, generated reports, or command examples shown to the user.

Before live collection, run `scripts/xhs_auth.py status --json`. If local auth is not usable, start the browser login helper with `--wait-auto` and tell the user exactly:

```text
请在弹出的小红书页面完成登录, 登录成功后我会自动继续采集。
```

If the user already gave the keyword/count/task, keep that context in the sentence, for example:

```text
请在弹出的小红书页面完成登录, 登录成功后我会自动采集“小众旅游”关键词下 3 篇笔记及评论，并输出报告。
```

Keep the `scripts/xhs_auth.py login --wait-auto` command running until it exits or times out. Then run `scripts/xhs_auth.py status --json` or `check`.
Do not include cookie values in the response. For collection commands, prefer reading `<skill-dir>/.secrets/xhs_cookie.txt`; avoid passing `--cookies-str` unless the user explicitly provided a cookie in the current shell environment.

## Commands

Install runtime dependencies for PC data collection:

```bash
bash scripts/bootstrap_env.sh
```

`bootstrap_env.sh` uses `PYTHON_BIN` when set, otherwise tries `python3`, then `python`.
It supports Python 3.9 through current Python 3 releases. Python 3.0-3.8 are not
supported because the browser and spreadsheet dependencies no longer support those
end-of-life runtimes reliably.

Set up local browser login for non-technical users:

```bash
.venv/bin/python scripts/xhs_auth.py login --verbose --wait-auto
.venv/bin/python scripts/xhs_auth.py status --json
```

By default, the login helper tries installed Chrome, Edge, Chrome for Testing, common browser executable paths, then Playwright bundled Chromium.
If no controllable browser is found, it automatically installs Playwright Chromium and retries.
To force a specific browser:

```bash
.venv/bin/python scripts/xhs_auth.py login --channel chrome --wait-auto
.venv/bin/python scripts/xhs_auth.py login --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --wait-auto
```

The system default browser can be used only for manual login/cookie-copy fallback; automatic auth export requires a Playwright-controlled Chromium browser.
To disable automatic browser installation:

```bash
.venv/bin/python scripts/xhs_auth.py login --verbose --wait-auto --no-auto-install-browser
```

Install full creator-platform dependencies only when publishing/media upload workflows are explicitly needed:

```bash
.venv/bin/pip install -r scripts/requirements.txt
```

Normalize an existing raw JSON file:

```bash
.venv/bin/python scripts/normalize_xhs.py --input raw.json --out out/notes.normalized.json
```

Build Markdown and spreadsheet reports:

```bash
.venv/bin/python scripts/build_report.py --input out/notes.normalized.json --out-dir out/report
```

Collect a single note through the vendored runtime:

```bash
.venv/bin/python scripts/collect_notes.py \
  --mode note \
  --url "https://www.xiaohongshu.com/explore/..." \
  --out-dir "runs/{run_id}/note"
```

Collect keyword notes:

```bash
.venv/bin/python scripts/collect_notes.py \
  --mode keyword \
  --query "small city travel" \
  --limit 20 \
  --include-comments
```

Run a high-level workflow:

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow auto \
  --topic "山东济南 锡林郭勒 一家3口 5日游" \
  --max-notes 25
```

Add token-platform LLM insights when the environment is configured:

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow auto \
  --topic "小众旅游 爆款拆解" \
  --max-notes 25 \
  --llm-insights
```

Dry-run a workflow plan without live collection:

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow auto \
  --topic "小众旅游" \
  --dry-run
```

Force a specific workflow only when the user's intent is clear:

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow product-review \
  --topic "某防晒产品真实测评 避雷 平替" \
  --max-notes 20
```

## Token Platform

`scripts/token_platform_client.py` supports OpenAI-compatible chat completions through environment variables:

- `TOKEN_PLATFORM_BASE_URL`
- `TOKEN_PLATFORM_API_KEY`
- `TOKEN_PLATFORM_MODEL`

If those variables are missing, reports fall back to deterministic local summaries.
`scripts/xhs_workflow.py --llm-insights` writes `llm_prompt.md` and `llm_insights.md` only when these variables are configured; otherwise it records a non-fatal `llm_insights_error` in `summary.json`.

## Boundaries

- Require user authorization for live collection.
- Keep collection limits small by default.
- Do not add proxy-pool, anti-detection, spam, resale, or automated publishing workflows.
- Do not download media by default; store URLs unless the user explicitly asks and has rights to use the media.
- Keep comment exports minimal and analysis-oriented. Do not use comments for outreach or user profiling.
- Read `references/compliance.md` before extending collection scope.

## References

- Field schema: `references/fields.md`
- Report template: `references/report-template.md`
- Compliance boundaries: `references/compliance.md`
- Manual cookie handling: `references/cookie-guide.md`
- High-level workflow guide: `references/workflows.md`
- Vendored PC/creator API inventory: `references/xhs-api-index.md`
