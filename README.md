# xhs-tool

Codex skill for authorized Xiaohongshu research, reporting, and conversational content drafting.

Chinese documentation: [README.zh-CN.md](README.zh-CN.md)

## Capabilities

- Collect one note, keyword samples, or notes from one authorized user profile.
- Run general research, travel planning, product review, content ideation, comment insight, viral pattern analysis, deep research, topic bank, and viral reverse engineering workflows.
- Normalize notes and comments, rank evidence, and export private JSON, Markdown, and spreadsheet files.
- Create and refine titles, body copy, hashtags, cover copy, visual systems, and page-by-page carousel plans through AI conversation.
- Keep media as a URL index. The project does not download media or publish content.

## Workflow Menu

| Workflow | Chinese Name | Use For |
|---|---|---|
| `general-research` | 主题研究 | Safe fallback for broad XHS topic research. |
| `travel-plan` | 旅行攻略研究 | Itineraries, routes, accommodation areas, food, budget clues, and travel risks. |
| `product-review` | 产品口碑研究 | Product reputation, reviews, alternatives, pros/cons, and purchase framing. |
| `content-ideation` | 选题生成 | Content angles, title references, account operation ideas, and next-post inspiration. |
| `comment-insight` | 评论洞察 | Repeated questions, objections, pain points, FAQ, and user vocabulary from comments. |
| `viral-pattern` | 爆款拆解 | Common patterns in popular notes, titles, tags, hooks, and interaction structures. |
| `deep-research` | 深度调研 | User needs, pain points, decision factors, opportunity clues, risks, and next sampling plans. |
| `topic-bank` | 选题库 | Structured topic libraries and content calendars from sampled XHS evidence. |
| `viral-reverse` | 爆款逆向复盘 | Reverse-engineering high-interaction notes into original reusable content templates. |

## Quick Start

```bash
bash scripts/bootstrap_env.sh
.venv/bin/python scripts/xhs_doctor.py
.venv/bin/python scripts/xhs_auth.py login --wait-auto
.venv/bin/python scripts/xhs_auth.py status --json
.venv/bin/python scripts/xhs_workflow.py --workflow auto --topic "your research topic"
```

Start a standalone content-creation conversation with the configured OpenAI-compatible Token Platform:

```bash
.venv/bin/python scripts/xhs_content_chat.py start --brief "给露营新手写一篇装备清单"
.venv/bin/python scripts/xhs_content_chat.py reply --session "SESSION_ID" --message "改成五个要点，语气更克制"
```

Add a structured visual plan only when needed:

```bash
.venv/bin/python scripts/xhs_content_chat.py start \
  --brief "把露营装备清单做成多页图文" \
  --pages 6 \
  --visual-style "自然纪实、清晰编辑感"
```

The same workflow works directly in Codex by asking `$xhs-tool` to write, revise, or visually direct a draft. Content-chat sessions are private local artifacts and never publish automatically. If the Token Platform is not configured, the standalone command creates a local template draft and reports the fallback.

Live collection is limited to 50 notes, 8 queries, 10 notes per query, and 100
normalized comments per note. Defaults are smaller. A failed note or query is recorded
and does not discard successful results.

## Install Doctor

Run the local doctor after installation or before a demo:

```bash
.venv/bin/python scripts/xhs_doctor.py
.venv/bin/python scripts/xhs_doctor.py --json
```

By default, doctor checks Python, Node.js, npm, Python dependencies, Node dependencies, runtime integrity, browser availability, local auth structure, Token Platform configuration, and run-directory write access. It does not call the live XHS API unless explicitly requested:

```bash
.venv/bin/python scripts/xhs_doctor.py --online-auth-check
```

Workflow reports also include recommended follow-up packages so the user can continue from research to a decision memo, topic bank, content draft, visual plan, FAQ, note library, or media URL review.

## Security And Data Retention

- Cookies are read from `.secrets/xhs_cookie.txt` or `XHS_COOKIE`; secret-bearing API payloads use standard input, not process arguments.
- The API wrapper exposes a read-only research allowlist. Creator publishing and no-watermark methods are blocked.
- Run directories use mode `0700`; reports, tables, checkpoints, and sanitized raw files use mode `0600` where supported.
- Raw responses redact cookies, request headers, sessions, and access tokens before storage.
- Preview raw files older than 30 days with `python scripts/manage_runs.py --older-than-days 30`; add `--execute` to remove only those raw files.

## Verification

```bash
python -m unittest discover -s tests -v
python scripts/verify_runtime.py
.venv/bin/python scripts/xhs_doctor.py
```

## Python Compatibility

The command-line tools support Python 3.9 through current Python 3 releases. Python
3.0-3.8 are not supported because current browser, spreadsheet, and HTTP dependencies
no longer install reliably on those end-of-life versions.

The live API runtime also requires Node.js 18+ and npm. `bootstrap_env.sh` checks both
before creating the environment.

Create the local environment with any Python 3.9+ interpreter:

```bash
PYTHON_BIN=python3 bash scripts/bootstrap_env.sh
```

If `python3` points to an older interpreter, provide an explicit executable, for example:

```bash
PYTHON_BIN=/path/to/python3.9 bash scripts/bootstrap_env.sh
```

See `SKILL.md` for workflows and command examples.
