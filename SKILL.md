---
name: xhs-tool
description: 小红书/XHS/Rednote content and research skill. Use when the user asks to 写小红书笔记, 写一篇小红书, 小红书风格, 小红书攻略, 自驾攻略, 旅游攻略, 探店, 种草, 测评, 避雷, 爆款标题, 正文, 标签, 话题, 封面文案, 配图建议, 图文/轮播脚本, cover, carousel, image prompts, account content ideation, comment insight, viral pattern analysis, or authorized Xiaohongshu data collection/reporting. Trigger especially for requests like “帮我写一篇小红书的自驾甘南攻略”. For broad content requests, first ask adaptive brief questions, then produce a human-reviewed draft. Every completed draft response must end with a “下一步确认” asking whether to save the draft as a document, refine carousel/cover planning, or generate images. Do not log in, collect data, save files, generate images, upload, or publish unless the user explicitly confirms that step.
---

# XHS Tool

## Overview

Use this skill to research authorized XHS note data or create human-reviewed XHS content drafts through natural-language conversation.
For research, collect or import data, normalize it, and generate reports. For content creation, turn the user's brief and follow-up messages into titles, body copy, hashtags, cover copy, image suggestions, and compliance notes without publishing.

## High-Level Workflows

For broad user requests, prefer `scripts/xhs_workflow.py --workflow auto` over manually chaining low-level scripts. The script infers the workflow from the user's natural-language topic and records `inferred_workflow` in `summary.json`.

Clean Chinese trigger examples:

- "帮我写一篇小红书的自驾甘南攻略" -> conversational content creation unless the user asks to collect live XHS data.
- "从小红书整理一份甘南自驾攻略" -> travel planning research workflow.
- "改成小红书风格，标题更抓人，标签也补上" -> conversational content refinement.
- "做成 6 页小红书图文/封面/轮播图脚本" -> visual content direction.

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
- General research: `--workflow general-research`
  Safe fallback for topics that do not match a specialized workflow.
- Conversational content creation: `scripts/xhs_content_chat.py`
  Use for requests like “帮我写一篇露营装备清单”“标题更有冲突感”“语气克制一点”. Keep the same session for follow-up edits.
- Visual content direction: `scripts/xhs_content_chat.py --pages N`
  Use for covers, 3:4 carousels, page-by-page visual plans, style selection, image prompts, rendered-image preparation, or layout review. Do not force a carousel onto copy-only requests.

Default workflow outputs:

- `workflow_report.md`: user-facing research report.
- `notes.normalized.json` and note table: normalized sampled notes.
- `comments.normalized.json` and comment table: normalized comments when enabled.
- `media_index.json`: image/video URL index only; do not download media by default.
- `summary.json`: run metadata, partial failures, evidence quality, and output paths.
- `checkpoint.json` and partial JSON files: incremental recovery data while collection is running.
- Optional `llm_insights.md`: generated only with `--llm-insights` and configured token-platform environment variables.

After producing the report, proactively ask whether the user wants a follow-up package such as: deeper report refinement, note link library, comment FAQ, media URL index review, or authorized media download. Media download requires explicit confirmation of use rights and purpose.

When the user asks broad ranking questions like “当前最热门的话题是什么” or “最火的主播是谁”, frame the result as sampled XHS search evidence, not an official platform-wide ranking. Ask for a category or seed keyword if the request is too broad to sample responsibly.

## Workflow

1. Identify the input type:
   - Content creation or refinement: respond with a draft directly in the AI conversation. Use `scripts/xhs_content_chat.py` when persistent sessions or standalone Token Platform generation are needed.
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

## Conversational Content Creation

Treat the current AI conversation as the primary interface. For the first turn, gather a clear creative brief before drafting unless the user explicitly says to skip questions, use assumptions, or draft immediately. First classify the request type, then ask one compact grouped clarification with only the key missing fields for that type; do not run a long interview or use one fixed questionnaire for every XHS task.

Use an adaptive brief across XHS scenarios:

- Universal fields: target reader, content objective, topic/product/place/person, tone, deliverable format, must-include facts, and prohibited claims or angles.
- Travel/自驾/探店/本地生活: ask for location or route, dates/season, people scenario, budget/comfort level, desired modules such as route,住宿,餐饮,费用,避雷,拍照点, and whether the tone should be攻略型 or 种草型.
- Product/种草/测评/避雷: ask for product name/category, user scenario, real experience or evidence, key selling points and shortcomings, comparison targets, price/channel constraints, claim boundaries, and whether the goal is 种草,测评,避雷, or转化.
- Brand/account/content ideation: ask for account positioning, audience, niche, content pillars, competitive references, update frequency, commercial boundaries, and preferred voice.
- Comment insight/viral pattern/research report: ask for seed keyword or note links, sample size, whether comments are needed, output format, and whether the result should be framed as sampled evidence.
- Cover/carousel/visual direction: ask for page count, key message, available original or licensed assets, visual style preference, text density, output level (plan/prompts/rendered images), and whether to generate one representative image after confirmation.

Example first response for "帮我写一篇小红书的自驾甘南攻略": "我先按自驾攻略场景确认 5 点再写：1. 从哪里出发？2. 几天几夜、几月出行？3. 几个人/亲子/情侣/朋友？4. 偏硬核路线还是种草轻攻略？5. 要正文笔记，还是标题+正文+标签+封面文案一起给？"

After the user answers, return a usable draft, not a discussion of how to write one. If the user only answers part of the questions, make the smallest necessary assumptions and label them briefly.

For the first turn, provide 3-5 title options, one selected title, body copy, hashtags, cover copy, image suggestions, and publishing checks. For follow-up turns, preserve all fields the user did not ask to change. Clearly distinguish researched evidence from creative suggestions, never invent personal experience or performance claims, and keep every result marked as a draft.

Mandatory closeout: every completed content draft, visual plan, carousel script, or image-prompt plan must end with a short "下一步确认" section. Always cover all three next-step categories: save the result, refine/export prompts, and generate actual rendered images in two stages. The wording may adapt to the user's current task, but it must stay concise, natural Chinese, and include all three categories. Example clean Chinese templates:

```text
下一步确认
1. 需要我保存成 Markdown/Word 风格文档吗？
2. 要不要继续细化成可直接作图的逐页提示词？
3. 是否先生成一张封面图/关键页用于确认风格？确认后再继续生成逐页配图。
```

```text
下一步可以继续做三件事：
- 保存成文档，方便后续修改或交付。
- 继续细化封面和逐页作图提示词。
- 先生成一张封面/关键页确认风格，再决定是否批量出图。
```

This closeout is required even when the draft already includes cover copy, image suggestions, visual plans, or prompts. Do not write files, generate rendered images, download media, upload, or publish unless the user confirms that next step. Never generate a full image set before the user has approved one representative cover/key-page image, unless the user explicitly says to skip style confirmation and generate all images. Before sending, scan the closeout for mojibake characters such as `闇`, `鏄`, `纭`, `鈥`, `涓`, `绋`, or `鍥`; if any appear, rewrite that section in normal Chinese.

If the user confirms saving, persist the draft under a local `runs/content-chat/<session-id>/` or task-specific output directory with at least `draft.md` and `draft.json`; include title options, selected title, body, hashtags, cover copy, image suggestions, visual plan, assumptions, and compliance notes. If the user confirms image generation, read `references/visual-content.md`, create or reuse the visual plan first, then use the bundled `scripts/studyhard_image_gen.py` client to generate one representative cover/key page and ask for approval before batch images.

Read `references/content-creation.md` before producing or extending a content-creation workflow. Use the session CLI for persistent standalone conversations:

```bash
.venv/bin/python scripts/xhs_content_chat.py start \
  --brief "给第一次露营的人写一篇装备清单" \
  --audience "周末轻量露营新手" \
  --tone "真诚、实用"
```

Continue with the returned session ID:

```bash
.venv/bin/python scripts/xhs_content_chat.py reply \
  --session "{session_id}" \
  --message "把标题改得更具体，正文压缩到五个要点"

.venv/bin/python scripts/xhs_content_chat.py show --session "{session_id}"
```

Sessions are stored privately under `runs/content-chat/<session-id>/` as `session.json`, `draft.json`, and `draft.md`. Without Token Platform configuration, the command writes a local template draft and records a non-fatal fallback reason.

## Visual Content Direction

Read `references/visual-content.md` for cover, carousel, visual-style, image-prompt, or layout-review requests. Match the visual system to the content rather than defaulting to dark technology aesthetics.

When the request is sufficiently specific, proceed with explicit assumptions. When audience, objective, core claim, available assets, and desired action leave materially different visual directions, ask one grouped clarification instead of forcing a fixed questionnaire. For full carousel or image-file requests, act as a visual director: produce a brief analysis, style judgment, visual master, page rhythm, and task-state list before any image generation.

For multi-page requests, create a unified visual direction and page-by-page plan. Lock a 1080x1440px 3:4 canvas, safe margins, color and typography tokens, component language, and page numbering across the series. Give each page one primary communication task and vary only its main visual and information structure.

Use the bundled image generation client only when the user explicitly asks for image files. Do not call an external image-generation skill. Generate one representative cover or key page first and request style confirmation before batch generation, unless the user explicitly asks to skip confirmation. Track this as `production_tasks`: `plan` completed, `confirm-image` awaiting confirmation, and `batch-images` ready only after approval. Never claim an image was generated unless a real file or returned asset exists. Do not publish the result.

The bundled client is `scripts/studyhard_image_gen.py`. It uses the StudyHard image gateway directly and reads API configuration from Codex config/auth files or `STUDYHARD_IMAGE_*` environment overrides. Set `STUDYHARD_IMAGE_OUT_DIR` to a task directory such as `<skill-dir>/runs/image-gen/<run_id>` when generating XHS assets so task state and cached images stay inside this skill's run outputs. Default model is `gpt-image-2`; use 3:4 output for XHS covers and carousel pages.

Representative cover/key-page generation example:

```bash
STUDYHARD_IMAGE_OUT_DIR="runs/image-gen/{run_id}" python scripts/studyhard_image_gen.py submit-generation \
  --prompt "<3:4 XHS cover or key-page prompt>" \
  --model "gpt-image-2" \
  --ratio "3:4" \
  --n 1
```

Create a persistent six-page visual draft when needed:

```bash
.venv/bin/python scripts/xhs_content_chat.py start \
  --brief "把露营装备清单做成多页小红书图文" \
  --pages 6 \
  --visual-style "自然纪实、清晰编辑感"
```

The content-chat CLI also accepts loose inputs inspired by MCP-style tool parameters while keeping this skill non-publishing:

```bash
.venv/bin/python scripts/xhs_content_chat.py start \
  --brief "把露营装备清单做成 6 页小红书图片" \
  --topics "露营,装备清单,新手" \
  --images "cover.png,detail.png" \
  --reference-assets "ref-style.png"
```

Inputs are parsed into private session fields (`topics`, `assets`) and draft fields (`brief_analysis`, `visual_master`, `production_tasks`). They are for planning and image-preparation only; the skill must not upload or publish.

## Auth UX And Secret Handling

Never show raw or redacted cookies in conversation unless the user explicitly asks for debugging output.
Do not paste `XHS_COOKIE` values into chat, logs, generated reports, or command examples shown to the user.

Before live collection, run `scripts/xhs_auth.py status --json`. If local auth is not usable, start the browser login helper with `--wait-auto`; by default it uses the user's installed Chrome/Edge/Chromium and does not download a browser. Tell the user exactly:

```text
请在弹出的小红书页面完成登录, 登录成功后我会自动继续采集。
```

If the user already gave the keyword/count/task, keep that context in the sentence, for example:

```text
请在弹出的小红书页面完成登录, 登录成功后我会自动采集“小众旅游”关键词下 3 篇笔记及评论，并输出报告。
```

Keep the `scripts/xhs_auth.py login --wait-auto` command running until it exits or times out. If no controllable installed browser is found, stop and report that real-time sampling needs either Chrome/Edge/Chromium installed or explicit permission to install the skill-local Playwright Chromium fallback. Do not silently download a browser. Then run `scripts/xhs_auth.py status --json` or `check`.
Do not include cookie values in the response. Collection commands read `<skill-dir>/.secrets/xhs_cookie.txt` or `XHS_COOKIE`; they do not accept cookies as command-line arguments.

## Commands

Install runtime dependencies for PC data collection:

```bash
bash scripts/bootstrap_env.sh
```

`bootstrap_env.sh` uses `PYTHON_BIN` when set, otherwise tries `python3`, then `python`.
It supports Python 3.9 through current Python 3 releases. Python 3.0-3.8 are not
supported because the browser and spreadsheet dependencies no longer support those
end-of-life runtimes reliably. The signing runtime also requires Node.js 18+ and npm.
It does not install Chromium by default. Set `XHS_INSTALL_BROWSER=1` only when the user explicitly agrees to install the optional skill-local Playwright Chromium fallback under `<skill-dir>/.browsers/`.

Set up local browser login for non-technical users. Prefer Chrome explicitly when it is available:

```bash
.venv/bin/python scripts/xhs_auth.py login --channel chrome --verbose --wait-auto
.venv/bin/python scripts/xhs_auth.py status --json
```

By default, the login helper uses an installed Chrome/Edge/Chromium so ordinary users do not wait for a browser download.
If no controllable installed browser is found, do not continue with non-sampled output. Ask the user to install Chrome/Edge/Chromium or explicitly allow the optional skill-local Chromium fallback:

```bash
.venv/bin/python scripts/xhs_auth.py login --channel chrome --wait-auto
.venv/bin/python scripts/xhs_auth.py login --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --wait-auto
.venv/bin/python scripts/xhs_auth.py login --browser-mode auto --auto-install-browser --wait-auto
```

The system default browser should not be used for normal skill auth because automatic auth export requires a Playwright-controlled Chromium-family browser launched by Playwright. The optional fallback downloads Chromium under `<skill-dir>/.browsers/`, not as a system Chrome installation.

The API command exposes only a read-only research allowlist. Creator publishing, media upload, private notification, and no-watermark methods are not callable through this skill.

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
  --include-comments \
  --comment-limit 50
```

Run a high-level workflow:

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow auto \
  --topic "山东济南 锡林郭勒 一家3口 5日游" \
  --max-notes 25 \
  --comment-limit 50
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
`scripts/xhs_content_chat.py` uses the same variables for multi-turn draft generation. It validates message sizes and response structure, forces `status: draft`, and falls back locally if the model is unavailable or returns malformed content.
Visual plans remain planning artifacts unless the user explicitly requests image generation; the Token Platform chat endpoint itself does not render images.

## Boundaries

- Require user authorization for live collection.
- Keep collection limits small by default.
- Enforce hard limits of 50 notes, 8 queries, 10 notes per query, and 100 normalized comments per note.
- Do not add proxy-pool, anti-detection, spam, resale, or automated publishing workflows.
- Keep generated content as a draft and require human fact, copyright, and compliance review before publication.
- Do not claim that sampled research proves platform-wide trends, or turn unverified content into factual product, health, finance, or performance claims.
- Do not download media by default; store URLs unless the user explicitly asks and has rights to use the media.
- Keep comment exports minimal and analysis-oriented. Do not use comments for outreach or user profiling.
- Read `references/compliance.md` before extending collection scope.

## References

- Field schema: `references/fields.md`
- Report template: `references/report-template.md`
- Compliance boundaries: `references/compliance.md`
- Manual cookie handling: `references/cookie-guide.md`
- High-level workflow guide: `references/workflows.md`
- Conversational content creation: `references/content-creation.md`
- Visual content direction and carousel QA: `references/visual-content.md`
- Read-only API inventory: `references/xhs-api-index.md`
- Vendored runtime provenance and integrity: `references/runtime-provenance.md`
