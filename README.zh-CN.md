# xhs-tool 中文说明

English documentation: [README.md](README.md)

`xhs-tool` 是一个 Codex Skill，用于在用户授权和合规边界内，对小红书笔记进行实时采样、整理、分析、报告生成，以及辅助创作小红书内容草稿。

它不是自动发布工具，也不是大规模爬取工具。默认只做小样本研究、结构化报告、内容草稿和视觉方案，所有结论都应表述为“本次采样观察”，不能说成平台官方排名或全网结论。

## 能力概览 / Capabilities

| English | 中文 |
|---|---|
| Collect one note, keyword samples, or notes from one authorized user profile. | 采集单篇笔记、关键词样本，或用户授权范围内的某个账号笔记。 |
| Run high-level research workflows through natural language. | 通过自然语言自动路由到对应研究工作流。 |
| Normalize notes and comments into stable JSON/table files. | 将笔记和评论标准化为稳定的 JSON 和表格文件。 |
| Generate Markdown reports, spreadsheets, media URL indexes, and summaries. | 生成 Markdown 报告、表格、媒体 URL 索引和运行摘要。 |
| Create and refine XHS content drafts. | 生成和迭代小红书标题、正文、标签、封面文案和图文方案草稿。 |
| Keep media as URLs by default; do not publish content. | 默认只保存媒体 URL，不下载媒体，不自动发布内容。 |

## 快速开始 / Quick Start

```bash
bash scripts/bootstrap_env.sh
.venv/bin/python scripts/xhs_auth.py login --wait-auto
.venv/bin/python scripts/xhs_auth.py status --json
.venv/bin/python scripts/xhs_workflow.py --workflow auto --topic "你的研究主题"
```

在 Codex 中使用时，可以直接用自然语言描述目标，例如：

```text
从小红书中整理一份 山东济南 - 锡林郭勒 一家3口, 5日游的攻略
```

如果本地登录态不可用，Skill 会提示：

```text
请在弹出的小红书页面完成登录, 登录成功后我会自动继续采集。
```

## 工作流总览 / Workflow Menu

建议优先使用：

```bash
.venv/bin/python scripts/xhs_workflow.py --workflow auto --topic "你的主题"
```

`auto` 会根据自然语言自动判断应进入哪个工作流，并在 `summary.json` 中记录 `inferred_workflow`。

| English Workflow | 中文工作流 | Workflow ID | 适用场景 / Use For | 主要输出 / Main Output |
|---|---|---|---|---|
| General research | 主题研究 | `general-research` | 主题不明确或不匹配专项流程时的安全兜底。 | 高价值样本、重复关键词、证据链接、开放问题、下一步采样建议。 |
| Travel planning | 旅行攻略研究 | `travel-plan` | 行程、路线、住宿区域、美食、亲子/自驾/预算/避坑研究。 | 路线建议、住宿/餐饮线索、亲子约束、预算线索、交通天气风险、值得阅读的笔记。 |
| Product or brand review | 产品口碑研究 | `product-review` | 产品口碑、真实测评、避雷、竞品、平替和购买判断。 | 正负反馈、适合/不适合人群、价格价值线索、竞品对比、购买建议框架。 |
| Content ideation | 选题生成 | `content-ideation` | 账号运营、内容角度、标题参考、下一篇发什么。 | 高互动标题、常见内容结构、可复用格式、评论 FAQ 选题、下一批内容建议。 |
| Comment insight | 评论洞察 | `comment-insight` | 评论区高频问题、情绪、痛点、异议、用户原话。 | 高赞评论、重复问题、用户顾虑、痛点词、FAQ 和后续回应建议。 |
| Viral pattern analysis | 爆款拆解 | `viral-pattern` | 热门笔记共性、标题/标签/互动结构、爆款模式研究。 | 标题公式、封面/内容钩子、标签线索、互动结构、争议点和可复用模板。 |
| Deep research | 深度调研 | `deep-research` | 深度调研、用户需求、痛点分析、竞品调研、机会/风险判断。 | 扩展检索面、证据质量、样本评分、需求/痛点/决策因素/机会/风险、下一步采样计划。 |
| Topic bank | 选题库 | `topic-bank` | 生成结构化选题库、选题池、内容日历、账号长期选题规划。 | 选题标题、内容角度、目标人群、内容形式、封面钩子、目标、难度和后续创作建议。 |
| Viral reverse engineering | 爆款逆向复盘 | `viral-reverse` | 复盘高互动笔记为什么火，提炼原创可复用结构。 | 高互动样本、可复用线索、标题公式、封面钩子、正文节奏、评论引导、风险提醒。 |

## 每个工作流怎么用 / Workflow Details

### General research / 主题研究

用于泛主题研究，通常作为 `auto` 无法明确匹配专项意图时的兜底流程。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py --workflow general-research --topic "小众旅游"
```

输出重点：样本概览、关键词、证据链接、初步结论、待验证问题和下一步采样方向。

### Travel planning / 旅行攻略研究

用于把小红书样本整理成旅行计划。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow travel-plan \
  --topic "山东济南 锡林郭勒 一家3口 5日游" \
  --max-notes 25 \
  --include-comments
```

输出重点：路线、每日行程、住宿区域、美食、亲子约束、预算线索、天气/交通/排队风险。

### Product or brand review / 产品口碑研究

用于分析产品、品牌、服务或竞品的真实口碑。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow product-review \
  --topic "某防晒产品真实测评 避雷 平替" \
  --max-notes 20 \
  --include-comments
```

输出重点：好评点、差评点、适合人群、不适合人群、替代品、购买建议矩阵。

### Content ideation / 选题生成

用于从样本中提炼内容方向和账号选题灵感。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow content-ideation \
  --topic "露营装备账号 选题 标题" \
  --max-notes 25
```

输出重点：标题参考、内容结构、可复用形式、下一批可写选题。这个流程偏“灵感”，更完整的结构化选题库建议使用 `topic-bank`。

### Comment insight / 评论洞察

用于把评论区转成用户需求、FAQ 和内容/产品改进线索。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow comment-insight \
  --topic "露营装备 评论 痛点 问题" \
  --max-notes 20 \
  --include-comments
```

输出重点：高赞评论、重复问题、用户异议、痛点词、FAQ、下一步回应内容。

### Viral pattern analysis / 爆款拆解

用于研究热门笔记的共同模式。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow viral-pattern \
  --topic "小众旅游 爆款拆解" \
  --max-notes 25 \
  --include-comments
```

输出重点：标题公式、封面/内容钩子、标签、互动结构、评论争议点和可复用模式。结论必须写成“本次样本中观察到”，不要说成官方榜单。

### Deep research / 深度调研

用于更系统地研究用户需求、痛点、竞品机会和风险。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow deep-research \
  --topic "露营装备 用户需求 痛点" \
  --max-notes 30 \
  --include-comments
```

输出重点：扩展 query、证据质量、Research Score、需求信号、痛点/阻碍、决策因素、机会线索、风险/反例和下一步采样计划。评分是内部启发式，不是平台排名。

### Topic bank / 选题库

用于把采样结果整理成结构化选题库或内容日历。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow topic-bank \
  --topic "AI 工具账号 选题库" \
  --max-notes 25 \
  --include-comments
```

输出重点：选题标题、内容角度、目标人群、内容形式、封面钩子、内容目标、制作难度和后续创作建议。下一步通常可以接 `scripts/xhs_content_chat.py` 生成正文和图文方案。

### Viral reverse engineering / 爆款逆向复盘

用于从高互动样本中提炼原创模板。

示例：

```bash
.venv/bin/python scripts/xhs_workflow.py \
  --workflow viral-reverse \
  --topic "露营装备 爆款复盘" \
  --max-notes 25 \
  --include-comments
```

输出重点：高互动样本、Reusable Cue、标题公式、封面钩子、正文节奏、评论引导和风险提醒。只能复用结构，不能复刻原笔记标题、封面和正文。

## 内容生成 / Conversational Content Creation

除了研究流程，`xhs-tool` 也支持内容草稿生成和多轮修改。

```bash
.venv/bin/python scripts/xhs_content_chat.py start --brief "给露营新手写一篇装备清单"
.venv/bin/python scripts/xhs_content_chat.py reply --session "SESSION_ID" --message "改成五个要点，语气更克制"
```

适合输出：标题、正文、标签、封面文案、图片建议、发布前检查。所有内容都是草稿，需要人工核验事实、版权和合规风险。

## 图文视觉方案 / Visual Content Direction

当用户需要小红书封面、多页图文或视觉风格方案时，可以指定页数和风格。

```bash
.venv/bin/python scripts/xhs_content_chat.py start \
  --brief "把露营装备清单做成多页图文" \
  --pages 6 \
  --visual-style "自然纪实、清晰编辑感"
```

输出会包含 3:4 画布规划、封面方向、逐页信息任务、版式建议、图片提示词和发布前检查。只有用户明确要求生成图片文件时，才调用图片生成能力。

## 默认产物 / Default Outputs

| File | 中文说明 |
|---|---|
| `workflow_report.md` | 面向用户的研究报告。 |
| `notes.normalized.json` | 标准化笔记数据。 |
| `comments.normalized.json` | 标准化评论数据，仅在启用评论采集时生成。 |
| `media_index.json` | 图片/视频 URL 索引，默认不下载媒体。 |
| `summary.json` | 运行元信息、采样质量、错误、输出路径和下一步建议。 |
| `checkpoint.json` | 采集中断恢复用的检查点。 |
| `llm_insights.md` | Token Platform 配置可用且启用 `--llm-insights` 时生成。 |

## 安全与边界 / Security And Boundaries

- 只处理用户授权或允许范围内的数据。
- 默认小样本采集，硬限制为 50 篇笔记、8 个 query、每个 query 10 篇笔记、每篇 100 条标准化评论。
- Cookie 从 `.secrets/xhs_cookie.txt` 或 `XHS_COOKIE` 读取，不应出现在聊天、日志、报告或命令参数中。
- API wrapper 只暴露只读研究 allowlist，禁止发布、上传、私信、无水印下载等能力。
- 默认只保存媒体 URL，不下载、不复用媒体素材。
- 不做代理池、反检测、批量爬取、营销骚扰、自动发布。
- 采样结论不能写成“全网最火”“平台第一”“官方排名”。

## 验证 / Verification

```bash
python -m unittest discover -s tests -v
python scripts/verify_runtime.py
```

## Python 兼容性 / Python Compatibility

命令行工具支持 Python 3.9 及以上版本。实时采集运行时还需要 Node.js 18+ 和 npm。

```bash
PYTHON_BIN=python3 bash scripts/bootstrap_env.sh
```

如果 `python3` 指向旧版本，可以显式指定：

```bash
PYTHON_BIN=/path/to/python3.9 bash scripts/bootstrap_env.sh
```
