# XHS Workflow Guide

## Product Shape

Treat `xhs-tool` as an XHS research assistant rather than only a report generator.
The normal loop is:

1. Clarify the user's goal and map it to a workflow.
2. Check local auth; if needed, ask the user to complete browser login.
3. Collect a small, relevant sample of notes and comments.
4. Normalize data into stable JSON/table files.
5. Generate a Markdown report, evidence summary, spreadsheet files, and media URL index.
6. Ask what follow-up package the user needs next.

Use `scripts/xhs_workflow.py --workflow auto` unless the user or operator explicitly chooses a workflow.

## Workflow Menu

### general-research

Use as the automatic fallback when a topic does not clearly match a specialized
workflow. Outputs should emphasize sampled high-value notes, repeated terms, evidence
links, open questions, and what should be collected next. Do not silently classify an
unknown topic as a viral-pattern request.

### travel-plan

Use for itinerary and destination research.

Good inputs:

- “山东济南到锡林郭勒，一家 3 口，5 日游攻略”
- “上海周边亲子两日游避坑”

Outputs should emphasize route, accommodation areas, food, parent-child constraints, budget clues, weather/traffic risks, and notes worth reading.

### product-review

Use for product口碑、测评、避雷、竞品/平替.

Outputs should emphasize positive feedback, negative feedback, suitable users, unsuitable users, price/value cues, competing products, and purchase decision framing.

### content-ideation

Use for账号运营、选题库、标题参考、内容角度.

Outputs should emphasize high-interaction titles, common structures, repeatable formats, comment-derived FAQ ideas, and next posts the user could create.

### comment-insight

Use when comments are the core evidence.

Outputs should emphasize high-like comments, repeated questions, objections, pain points, user vocabulary, and what the user should answer next.

### viral-pattern

Use for爆款拆解 and popularity pattern analysis.

Important: frame conclusions as sample-based, not an official platform-wide ranking.
Outputs should emphasize title formulas, cover/content hooks if inferable, tags, interaction structure, controversies, and repeatable templates.

## Output Quality

The workflow summary includes `evidence_quality`:

- `low`: too few notes/comments for confident conclusions. Present as early exploration.
- `medium`: enough for a useful first-pass report. Recommend targeted follow-up if the decision matters.
- `high`: enough sampled evidence for a stronger internal recommendation.

Even with `high`, conclusions remain sampling-based and should not be described as official XHS rankings.

## Follow-Up Options

After the default report, ask which follow-up would help:

- Deep report: refine the Markdown into a decision memo, travel plan, product brief, or content plan.
- Token-platform insight: run `--llm-insights` to generate a model-written decision memo from the sampled evidence.
- Note library: curate the most useful note links with reasons to read each one.
- Comment FAQ: turn comments into user questions and suggested answers.
- Media index: review image/video URLs and identify candidate素材.
- Authorized media download: download images/videos only after the user confirms rights and purpose.

## Boundaries

- Keep default samples small and relevant.
- Do not claim “全网最火” or “平台第一” unless the source provides that ranking.
- Do not automate publishing, spam, private-data profiling, or anti-detection behavior.
- Do not download or reuse media by default.
