#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from collect_notes import fetch_note_details, load_cookie, resolve_tool, result_payload, call_xhs
from xhs_report_lib import (
    as_int,
    ensure_list,
    flatten_note_comments,
    interaction_score,
    summarize_comments,
    summarize_notes,
    tokenize_chinese_and_ascii,
    write_comments_table,
    write_json,
    write_table,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = {
    "travel-plan": {
        "label": "旅行攻略研究",
        "suffixes": ["攻略", "路线", "避坑", "亲子游", "住宿", "美食", "自驾", "5日游"],
        "triggers": ["旅游", "旅行", "攻略", "路线", "行程", "亲子", "自驾", "酒店", "住宿", "景点", "美食", "几日游"],
        "default_comments": True,
    },
    "product-review": {
        "label": "产品口碑研究",
        "suffixes": ["真实测评", "好用吗", "避雷", "使用感", "平替", "对比", "成分", "复购"],
        "triggers": ["产品", "品牌", "测评", "口碑", "好用", "避雷", "平替", "对比", "成分", "复购", "值得买吗"],
        "default_comments": True,
    },
    "content-ideation": {
        "label": "选题生成",
        "suffixes": ["爆款", "选题", "干货", "新手", "避坑", "攻略", "合集", "标题"],
        "triggers": ["选题", "内容", "标题", "运营", "账号", "发什么", "怎么写", "种草文案", "脚本"],
        "default_comments": False,
    },
    "comment-insight": {
        "label": "评论洞察",
        "suffixes": ["真实体验", "评论", "吐槽", "问题", "避雷", "评价", "后悔", "推荐"],
        "triggers": ["评论", "痛点", "问题", "需求", "吐槽", "高赞评论", "faq", "FAQ", "问得最多"],
        "default_comments": True,
    },
    "viral-pattern": {
        "label": "爆款拆解",
        "suffixes": ["爆款", "热门", "高赞", "合集", "必看", "保姆级", "避坑", "攻略"],
        "triggers": ["爆款", "热门", "最火", "高赞", "趋势", "话题", "榜单", "共性", "拆解"],
        "default_comments": True,
    },
}


def default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def expand_queries(workflow: str, topic: str, max_queries: int) -> list[str]:
    topic = " ".join(topic.split())
    suffixes = WORKFLOWS[workflow]["suffixes"]
    queries = [topic]
    queries.extend(f"{topic} {suffix}" for suffix in suffixes if suffix not in topic)
    deduped = []
    seen = set()
    for query in queries:
        if query not in seen:
            deduped.append(query)
            seen.add(query)
    return deduped[:max_queries]


def infer_workflow(topic: str) -> str:
    text = topic.lower()
    scores = {}
    for workflow, config in WORKFLOWS.items():
        score = 0
        for trigger in config.get("triggers", []):
            if str(trigger).lower() in text:
                score += 1
        scores[workflow] = score
    best_workflow, best_score = max(scores.items(), key=lambda item: item[1])
    return best_workflow if best_score > 0 else "viral-pattern"


def resolve_workflow(workflow: str, topic: str) -> tuple[str, bool]:
    if workflow == "auto":
        return infer_workflow(topic), True
    return workflow, False


def dedupe_notes(notes: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for note in notes:
        key = note.get("note_id") or note.get("url") or json.dumps(note, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        result.append(note)
        seen.add(key)
    return result


def collect_workflow_notes(
    workflow: str,
    topic: str,
    limit_per_query: int,
    max_notes: int,
    include_comments: bool,
    xhs_apis_skill: str | None,
    cookies_str: str,
) -> tuple[list[str], list[dict], list[dict]]:
    tool = resolve_tool(xhs_apis_skill)
    queries = expand_queries(workflow, topic, max_queries=8)
    raw_batches = []
    notes = []
    for query in queries:
        search_raw = call_xhs(
            tool,
            "pc",
            "search_some_note",
            {"query": query, "require_num": limit_per_query, "cookies_str": cookies_str},
        )
        search_items = result_payload(search_raw)
        if not isinstance(search_items, list):
            search_items = []
        detail_raw, comment_raw, query_notes = fetch_note_details(
            tool,
            search_items,
            cookies_str,
            "pc_search",
            limit_per_query,
            include_comments,
        )
        raw_batches.append(
            {
                "query": query,
                "search_raw": search_raw,
                "detail_raw": detail_raw,
                "comment_raw": comment_raw,
                "notes_count": len(query_notes),
            }
        )
        notes.extend(query_notes)
        notes = dedupe_notes(notes)
        if len(notes) >= max_notes:
            notes = notes[:max_notes]
            break
    return queries, raw_batches, notes


def top_terms(notes: list[dict], limit: int = 24) -> list[tuple[str, int]]:
    from collections import Counter

    counter = Counter()
    for note in notes:
        counter.update(tokenize_chinese_and_ascii(f"{note.get('title', '')} {note.get('desc', '')}"))
        counter.update(str(tag).strip() for tag in ensure_list(note.get("tags")) if str(tag).strip())
    return counter.most_common(limit)


def media_index(notes: list[dict]) -> list[dict]:
    rows = []
    for note in sorted(notes, key=interaction_score, reverse=True):
        rows.append(
            {
                "note_id": note.get("note_id", ""),
                "title": note.get("title", ""),
                "author": note.get("author", ""),
                "url": note.get("url", ""),
                "images": ensure_list(note.get("images")),
                "video_url": note.get("video_url", ""),
            }
        )
    return rows


def evidence_quality(notes: list[dict], comments: list[dict]) -> dict:
    note_count = len(notes)
    comment_count = len(comments)
    with_media = sum(1 for note in notes if ensure_list(note.get("images")) or note.get("video_url"))
    score = 0
    if note_count >= 20:
        score += 2
    elif note_count >= 8:
        score += 1
    if comment_count >= 80:
        score += 2
    elif comment_count >= 20:
        score += 1
    if with_media >= max(1, note_count // 2):
        score += 1
    level = "high" if score >= 4 else "medium" if score >= 2 else "low"
    return {
        "level": level,
        "notes": note_count,
        "comments": comment_count,
        "notes_with_media": with_media,
    }


def question_candidates(comments: list[dict], limit: int = 12) -> list[str]:
    markers = ("?", "？", "吗", "么", "怎么", "哪里", "多少", "适合", "有没有", "能不能", "值不值")
    seen = set()
    questions = []
    ranked = sorted(comments, key=lambda item: as_int(item.get("like_count")), reverse=True)
    for comment in ranked:
        content = str(comment.get("content") or "").strip().replace("\n", " ")
        if not content or len(content) < 4:
            continue
        if not any(marker in content for marker in markers):
            continue
        compact = content[:120]
        if compact in seen:
            continue
        questions.append(compact)
        seen.add(compact)
        if len(questions) >= limit:
            break
    return questions


def next_actions(workflow: str) -> list[str]:
    common = [
        "整理成可直接交付的报告/攻略/内容方案",
        "导出高价值笔记链接库，标注推荐阅读理由",
        "基于评论整理 FAQ 和用户原话素材",
        "检查 `media_index.json`，筛选可授权使用的图片/视频候选",
    ]
    workflow_actions = {
        "travel-plan": ["把路线拆成逐日行程、预算、住宿区域和避坑清单"],
        "product-review": ["输出购买建议矩阵：适合买/谨慎买/不建议买/替代品"],
        "content-ideation": ["生成 20 个选题、标题和首段开头"],
        "comment-insight": ["把评论问题转成客服话术、FAQ 或内容答疑清单"],
        "viral-pattern": ["拆解标题结构、标签结构和可复用爆款模板"],
    }
    return workflow_actions.get(workflow, []) + common


def note_table_rows(notes: list[dict], limit: int = 10) -> list[str]:
    lines = [
        "| Rank | Title | Author | Score | Likes | Collects | Comments | URL |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for index, note in enumerate(sorted(notes, key=interaction_score, reverse=True)[:limit], 1):
        title = str(note.get("title") or "Untitled").replace("|", " ")[:80]
        author = str(note.get("author") or "").replace("|", " ")
        lines.append(
            f"| {index} | {title} | {author} | {interaction_score(note)} | "
            f"{as_int(note.get('liked_count'))} | {as_int(note.get('collected_count'))} | "
            f"{as_int(note.get('comment_count'))} | {note.get('url', '')} |"
        )
    return lines


def bullet_terms(terms: list[tuple[str, int]], limit: int = 16) -> str:
    if not terms:
        return "暂无高频词。"
    return ", ".join(f"{word}({count})" for word, count in terms[:limit])


def build_workflow_report(workflow: str, topic: str, queries: list[str], notes: list[dict], comments: list[dict]) -> str:
    summary = summarize_notes(notes)
    comment_summary = summarize_comments(comments)
    terms = top_terms(notes)
    quality = evidence_quality(notes, comments)
    label = WORKFLOWS[workflow]["label"]
    lines = [
        f"# {label}: {topic}",
        "",
        "> 说明：本结果基于小红书搜索采样生成，不代表官方榜单或全站结论。默认用于内容研究、攻略整理和内部参考。",
        "",
        "## 采样概览",
        "",
        f"- 工作流: `{workflow}`",
        f"- 主题: {topic}",
        f"- 查询词: {', '.join(queries)}",
        f"- 笔记数: {summary['count']}",
        f"- 评论数: {comment_summary['count']}",
        f"- 证据质量: {quality['level']}（笔记 {quality['notes']}，评论 {quality['comments']}，含媒体笔记 {quality['notes_with_media']}）",
        f"- 总点赞: {summary['totals']['liked_count']}",
        f"- 总收藏: {summary['totals']['collected_count']}",
        f"- 高频词/标签: {bullet_terms(terms)}",
        "",
        "## 高价值参考笔记",
        "",
        *note_table_rows(notes),
        "",
    ]
    if workflow == "travel-plan":
        lines.extend(build_travel_section(topic, notes, comments, terms))
    elif workflow == "product-review":
        lines.extend(build_product_section(topic, notes, comments, terms))
    elif workflow == "content-ideation":
        lines.extend(build_ideation_section(topic, notes, comments, terms))
    elif workflow == "comment-insight":
        lines.extend(build_comment_section(topic, comments))
    elif workflow == "viral-pattern":
        lines.extend(build_viral_section(topic, notes, comments, terms))
    lines.extend(build_common_appendix(workflow, notes, comments))
    return "\n".join(lines) + "\n"


def build_llm_prompt(workflow: str, topic: str, notes: list[dict], comments: list[dict]) -> str:
    top_notes = sorted(notes, key=interaction_score, reverse=True)[:12]
    top_comments = sorted(comments, key=lambda item: as_int(item.get("like_count")), reverse=True)[:20]
    payload = {
        "workflow": workflow,
        "topic": topic,
        "notes": [
            {
                "title": note.get("title", ""),
                "desc": str(note.get("desc", ""))[:500],
                "author": note.get("author", ""),
                "liked_count": as_int(note.get("liked_count")),
                "collected_count": as_int(note.get("collected_count")),
                "comment_count": as_int(note.get("comment_count")),
                "tags": ensure_list(note.get("tags"))[:10],
                "url": note.get("url", ""),
            }
            for note in top_notes
        ],
        "comments": [
            {
                "content": str(comment.get("content", ""))[:240],
                "like_count": as_int(comment.get("like_count")),
                "note_url": comment.get("note_url", ""),
            }
            for comment in top_comments
        ],
    }
    return (
        "你是小红书研究分析助手。请基于下面的授权采样数据输出中文洞察，"
        "不要声称这是官方全站榜单。请包含：核心结论、证据、风险/反例、可执行建议、下一步采集建议。\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def maybe_build_llm_insights(workflow: str, topic: str, notes: list[dict], comments: list[dict], out_dir: Path) -> tuple[str, str]:
    if not (
        os.environ.get("TOKEN_PLATFORM_BASE_URL")
        and os.environ.get("TOKEN_PLATFORM_API_KEY")
        and os.environ.get("TOKEN_PLATFORM_MODEL")
    ):
        return "", "TOKEN_PLATFORM_* environment variables are not set."
    try:
        from token_platform_client import chat_completion
    except Exception as exc:
        return "", f"token platform client unavailable: {exc}"
    prompt = build_llm_prompt(workflow, topic, notes, comments)
    prompt_path = out_dir / "llm_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    try:
        insights = chat_completion(prompt)
    except Exception as exc:
        return "", f"token platform request failed: {exc}"
    insights_path = out_dir / "llm_insights.md"
    insights_path.write_text(insights, encoding="utf-8")
    return str(insights_path.resolve()), ""


def build_travel_section(topic: str, notes: list[dict], comments: list[dict], terms: list[tuple[str, int]]) -> list[str]:
    return [
        "## 攻略草案",
        "",
        "- 路线建议：优先从高收藏/高评论笔记中提取路线、住宿、餐饮和避坑信息，再按天数组织。",
        "- 亲子关注点：车程强度、住宿舒适度、卫生间/补给点、儿童可参与项目、天气和防晒防寒。",
        "- 住宿餐饮：把高频地点和评论里重复出现的店名/区域作为候选，不把单篇种草直接当结论。",
        "- 避坑提醒：重点看评论中的否定词、排队、价格、天气、交通、住宿落差等反馈。",
        "",
        "## 5日行程骨架",
        "",
        "| 天数 | 目标 | 小红书验证重点 |",
        "|---|---|---|",
        "| Day 1 | 出发与中转 | 车程、住宿落点、补给 |",
        "| Day 2 | 核心景点 1 | 亲子可玩性、拍照点、排队 |",
        "| Day 3 | 核心景点 2 | 草原/自然体验、天气备选 |",
        "| Day 4 | 轻松休整 | 餐饮、短途体验、孩子体力 |",
        "| Day 5 | 返程 | 返程路线、伴手礼、避开拥堵 |",
        "",
    ]


def build_product_section(topic: str, notes: list[dict], comments: list[dict], terms: list[tuple[str, int]]) -> list[str]:
    return [
        "## 口碑结论框架",
        "",
        "- 正向反馈：从高收藏测评和评论高频词中提炼使用场景、复购理由和人群匹配。",
        "- 负向反馈：重点看评论里的避雷、后悔、过敏、踩雷、价格、售后等词。",
        "- 竞品/平替：记录笔记中同时出现的品牌、型号、价格带。",
        "- 决策建议：把用户需求分成必买理由、谨慎购买理由、替代方案。",
        "",
        f"- 当前样本高频表达: {bullet_terms(terms)}",
        "",
    ]


def build_ideation_section(topic: str, notes: list[dict], comments: list[dict], terms: list[tuple[str, int]]) -> list[str]:
    top_titles = [note.get("title") for note in sorted(notes, key=interaction_score, reverse=True) if note.get("title")][:12]
    ideas = []
    for word, _ in terms[:12]:
        ideas.append(f"{topic}：关于“{word}”的避坑/攻略/清单型选题")
    return [
        "## 选题库",
        "",
        *(f"- {idea}" for idea in ideas[:20]),
        "",
        "## 标题参考",
        "",
        *(f"- {title}" for title in top_titles),
        "",
        "## 内容角度",
        "",
        "- 避坑型：总结用户踩坑和反常识经验。",
        "- 清单型：把选择标准、路线、用品、预算拆成表格。",
        "- 对比型：按人群/预算/季节/场景做选择建议。",
        "- 评论答疑型：把评论高频问题整理成 FAQ。",
        "",
    ]


def build_comment_section(topic: str, comments: list[dict]) -> list[str]:
    summary = summarize_comments(comments)
    questions = question_candidates(comments)
    lines = [
        "## 评论洞察",
        "",
        f"- 评论样本数: {summary['count']}",
        f"- 高频评论词: {bullet_terms(summary.get('top_words', []))}",
        "",
        "## 高赞评论",
        "",
        "| Rank | Content | Author | Likes | Note |",
        "|---:|---|---|---:|---|",
    ]
    for index, comment in enumerate(summary.get("top_comments", [])[:15], 1):
        content = str(comment.get("content") or "").replace("|", " ").replace("\n", " ")[:140]
        author = str(comment.get("author") or "").replace("|", " ")
        lines.append(f"| {index} | {content} | {author} | {as_int(comment.get('like_count'))} | {comment.get('note_url', '')} |")
    lines.extend(["", "## 可转化为内容的问题", ""])
    if questions:
        lines.extend(f"- {question}" for question in questions)
    else:
        lines.append("- 从高赞评论和疑问句中提炼 FAQ、避坑、对比和后续选题。")
    lines.append("")
    return lines


def build_viral_section(topic: str, notes: list[dict], comments: list[dict], terms: list[tuple[str, int]]) -> list[str]:
    return [
        "## 爆款共性",
        "",
        "- 标题：观察高互动笔记是否集中在攻略、避坑、清单、对比、真实体验、保姆级等结构。",
        "- 内容：优先拆解收藏高的笔记，它们通常更接近可复用信息价值。",
        "- 评论：评论多的笔记适合提炼争议点、追问点和后续选题。",
        "- 标签：把高频标签作为内容分发和选题扩展依据。",
        "",
        f"- 样本高频词/标签: {bullet_terms(terms)}",
        "",
        "## 可复用模板",
        "",
        f"- 《{topic}避坑清单：这些点先确认再出发/下单》",
        f"- 《{topic}新手攻略：一次讲清路线/预算/选择标准》",
        f"- 《{topic}真实体验：哪些值得，哪些不建议》",
        f"- 《{topic}高频问题答疑：评论区问得最多的 10 个问题》",
        "",
    ]


def build_common_appendix(workflow: str, notes: list[dict], comments: list[dict]) -> list[str]:
    lines = [
        "## 建议下一步",
        "",
        *(f"- {action}" for action in next_actions(workflow)),
        "",
        "## 素材包说明",
        "",
        "- 默认只整理笔记链接、图片 URL、视频 URL，不下载媒体文件。",
        "- 如需下载图片/视频，应先确认使用权和用途边界。",
        "",
    ]
    if comments:
        questions = question_candidates(comments, limit=8)
        lines.extend(
            [
                "## 评论附录",
                "",
                f"- 已采集评论: {len(comments)}",
                "- 详见 `comments.normalized.json` 和评论表格。",
                "",
            ]
        )
        if questions:
            lines.extend(["### 评论高频疑问", ""])
            lines.extend(f"- {question}" for question in questions)
            lines.append("")
    return lines


def build_workflow_summary(
    run_id: str,
    workflow: str,
    inferred_workflow: bool,
    topic: str,
    queries: list[str],
    include_comments: bool,
    notes: list[dict],
    comments: list[dict],
    outputs: dict | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "workflow": workflow,
        "workflow_label": WORKFLOWS[workflow]["label"],
        "inferred_workflow": inferred_workflow,
        "topic": topic,
        "queries": queries,
        "include_comments": include_comments,
        "notes_count": len(notes),
        "comments_count": len(comments),
        "evidence_quality": evidence_quality(notes, comments),
        "next_actions": next_actions(workflow),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "outputs": outputs or {},
    }


def resolve_out_dir(out_dir: str, run_id: str) -> Path:
    if out_dir:
        return Path(out_dir.replace("{run_id}", run_id))
    return PROJECT_ROOT / "runs" / run_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run higher-level XHS research workflows.")
    parser.add_argument("--workflow", choices=["auto", *sorted(WORKFLOWS)], default="auto")
    parser.add_argument("--topic", required=True, help="User research goal or topic.")
    parser.add_argument("--limit-per-query", type=int, default=5)
    parser.add_argument("--max-notes", type=int, default=25)
    parser.add_argument("--max-queries", type=int, default=8)
    parser.add_argument("--include-comments", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--cookies-str", default="")
    parser.add_argument("--xhs-apis-skill", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--out-dir", default="", help="Defaults to <skill-dir>/runs/<run-id>. Supports {run_id}.")
    parser.add_argument("--dry-run", action="store_true", help="Only write workflow plan, do not collect live data.")
    parser.add_argument("--llm-insights", action="store_true", help="Optionally add token-platform LLM insights when TOKEN_PLATFORM_* is configured.")
    args = parser.parse_args()

    workflow, inferred_workflow = resolve_workflow(args.workflow, args.topic)
    run_id = args.run_id or default_run_id()
    out_dir = resolve_out_dir(args.out_dir, run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    include_comments = args.include_comments
    if include_comments is None:
        include_comments = bool(WORKFLOWS[workflow].get("default_comments"))
    queries = expand_queries(workflow, args.topic, max_queries=args.max_queries)

    if args.dry_run:
        plan = build_workflow_summary(
            run_id,
            workflow,
            inferred_workflow,
            args.topic,
            queries,
            include_comments,
            [],
            [],
        )
        plan["limit_per_query"] = args.limit_per_query
        plan["max_notes"] = args.max_notes
        plan["max_queries"] = args.max_queries
        write_json(out_dir / "workflow_plan.json", plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    cookies_str = load_cookie(args.cookies_str)
    if not cookies_str:
        raise ValueError("XHS auth is required. Run scripts/xhs_auth.py login --wait-auto first.")

    queries, raw_batches, notes = collect_workflow_notes(
        workflow,
        args.topic,
        args.limit_per_query,
        args.max_notes,
        include_comments,
        args.xhs_apis_skill,
        cookies_str,
    )
    comments = flatten_note_comments(notes)
    report = build_workflow_report(workflow, args.topic, queries, notes, comments)
    llm_insights_path = ""
    llm_insights_error = ""
    if args.llm_insights:
        llm_insights_path, llm_insights_error = maybe_build_llm_insights(workflow, args.topic, notes, comments, out_dir)
        if llm_insights_path:
            report += f"\n## Token 平台洞察\n\n详见 `{llm_insights_path}`。\n"
        elif llm_insights_error:
            report += f"\n## Token 平台洞察\n\n未生成：{llm_insights_error}\n"

    raw_path = out_dir / "raw.workflow.json"
    notes_path = out_dir / "notes.normalized.json"
    comments_path = out_dir / "comments.normalized.json"
    media_path = out_dir / "media_index.json"
    report_path = out_dir / "workflow_report.md"
    summary_path = out_dir / "summary.json"
    table_path = write_table(out_dir / "notes", notes)
    comments_table_path = write_comments_table(out_dir / "comments", comments)

    outputs = {
            "raw": str(raw_path.resolve()),
            "notes": str(notes_path.resolve()),
            "comments": str(comments_path.resolve()),
            "media_index": str(media_path.resolve()),
            "report": str(report_path.resolve()),
            "summary": str(summary_path.resolve()),
            "table": str(table_path.resolve()),
            "comments_table": str(comments_table_path.resolve()),
            "llm_insights": llm_insights_path,
    }
    summary = build_workflow_summary(
        run_id,
        workflow,
        inferred_workflow,
        args.topic,
        queries,
        include_comments,
        notes,
        comments,
        outputs,
    )
    summary["llm_insights_error"] = llm_insights_error
    write_json(raw_path, {"batches": raw_batches})
    write_json(notes_path, notes)
    write_json(comments_path, comments)
    write_json(media_path, media_index(notes))
    write_json(summary_path, summary)
    report_path.write_text(report, encoding="utf-8")

    print(f"run_id: {run_id}")
    print(f"workflow: {workflow}")
    print(f"inferred_workflow: {inferred_workflow}")
    print(f"out_dir: {out_dir.resolve()}")
    print(f"summary: {summary_path.resolve()}")
    print(f"report: {report_path.resolve()}")
    print(f"notes: {notes_path.resolve()}")
    print(f"table: {table_path.resolve()}")
    print(f"comments: {comments_path.resolve()}")
    print(f"media_index: {media_path.resolve()}")


if __name__ == "__main__":
    main()
