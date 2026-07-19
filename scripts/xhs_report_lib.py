#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xhs_security import protect_private_file, write_private_json, write_private_text


NORMALIZED_FIELDS = [
    "note_id",
    "url",
    "note_type",
    "title",
    "desc",
    "author",
    "author_id",
    "author_url",
    "publish_time",
    "ip_location",
    "liked_count",
    "collected_count",
    "comment_count",
    "share_count",
    "tags",
    "images",
    "video_url",
    "comments",
]

COMMENT_FIELDS = [
    "note_id",
    "note_url",
    "comment_id",
    "parent_comment_id",
    "root_comment_id",
    "level",
    "author",
    "author_id",
    "content",
    "like_count",
    "publish_time",
    "ip_location",
]

CHINESE_STOP_WORDS = {
    "一个", "一些", "这个", "那个", "就是", "还是", "可以", "没有", "不是", "自己", "我们",
    "你们", "他们", "真的", "感觉", "比较", "非常", "已经", "因为", "所以", "但是", "如果",
    "然后", "怎么", "什么", "小红书", "笔记", "分享", "一下", "今天", "现在", "大家",
}
FALLBACK_CHINESE_TERMS = {
    "攻略", "路线", "住宿", "酒店", "预算", "交通", "自驾", "亲子", "景点", "美食", "排队",
    "天气", "避坑", "推荐", "不推荐", "值得", "价格", "便宜", "贵", "好用", "难用", "过敏",
    "复购", "成分", "平替", "测评", "真实", "体验", "问题", "售后", "标题", "封面", "收藏",
    "评论", "点赞", "视频", "图片", "清单", "对比", "新手", "实用", "踩雷", "后悔", "适合",
}


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    write_private_json(path, data)


def as_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    unit = 1
    if text.endswith(("w", "W")):
        unit = 10000
        text = text[:-1]
    if text.endswith("万"):
        unit = 10000
        text = text[:-1]
    try:
        return int(float(text) * unit)
    except ValueError:
        return 0


def first_present(*values: Any, default: Any = "") -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return default


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unwrap_xhs_tool_response(data: Any) -> Any:
    if isinstance(data, dict) and "result" in data and "namespace" in data:
        result = data["result"]
        if isinstance(result, list) and len(result) >= 3:
            return result[2]
        return result
    return data


def extract_raw_items(data: Any) -> list[dict[str, Any]]:
    data = unwrap_xhs_tool_response(data)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    if "data" in data and isinstance(data["data"], dict):
        payload = data["data"]
        if isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
        if isinstance(payload.get("notes"), list):
            return [item for item in payload["notes"] if isinstance(item, dict)]
    if "items" in data and isinstance(data["items"], list):
        return [item for item in data["items"] if isinstance(item, dict)]
    if "notes" in data and isinstance(data["notes"], list):
        return [item for item in data["notes"] if isinstance(item, dict)]
    if "note_card" in data or "note_id" in data or "id" in data:
        return [data]
    return []


def normalize_comment(
    comment: dict[str, Any],
    note_url: str = "",
    parent_comment_id: str = "",
    root_comment_id: str = "",
    level: int = 1,
) -> dict[str, Any]:
    user = comment.get("user_info") or comment.get("user") or {}
    comment_id = first_present(comment.get("id"), comment.get("comment_id"))
    return {
        "comment_id": comment_id,
        "note_id": comment.get("note_id", ""),
        "note_url": comment.get("note_url", note_url),
        "parent_comment_id": first_present(comment.get("parent_comment_id"), parent_comment_id),
        "root_comment_id": first_present(comment.get("root_comment_id"), root_comment_id, comment_id),
        "level": as_int(first_present(comment.get("level"), level)),
        "author": first_present(user.get("nickname"), comment.get("nickname"), comment.get("author")),
        "author_id": first_present(user.get("user_id"), comment.get("user_id"), comment.get("author_id")),
        "content": first_present(comment.get("content"), comment.get("text")),
        "like_count": as_int(first_present(comment.get("like_count"), comment.get("liked_count"))),
        "publish_time": first_present(comment.get("create_time"), comment.get("time")),
        "ip_location": comment.get("ip_location", ""),
    }


def flatten_comments(raw_comments: Any, note_url: str = "") -> list[dict[str, Any]]:
    comments = []
    for comment in ensure_list(raw_comments):
        if not isinstance(comment, dict):
            continue
        root = normalize_comment(comment, note_url=note_url, level=1)
        comments.append(root)
        root_id = root["comment_id"]
        for sub_comment in ensure_list(comment.get("sub_comments")):
            if isinstance(sub_comment, dict):
                comments.append(
                    normalize_comment(
                        sub_comment,
                        note_url=note_url,
                        parent_comment_id=root_id,
                        root_comment_id=root_id,
                        level=2,
                    )
                )
    return comments


def normalize_comments_raw(data: Any, note_url: str = "") -> list[dict[str, Any]]:
    data = unwrap_xhs_tool_response(data)
    if isinstance(data, list):
        if any(isinstance(item, dict) and "sub_comments" in item for item in data):
            return flatten_comments(data, note_url=note_url)
        return [
            normalize_comment(comment, note_url=note_url)
            for comment in data
            if isinstance(comment, dict)
        ]
    if isinstance(data, dict):
        if isinstance(data.get("comments"), list):
            return flatten_comments(data["comments"], note_url=note_url)
        payload = data.get("data")
        if isinstance(payload, dict) and isinstance(payload.get("comments"), list):
            return flatten_comments(payload["comments"], note_url=note_url)
    return []


def normalize_note(item: dict[str, Any]) -> dict[str, Any]:
    card = item.get("note_card") or item.get("card") or item
    user = card.get("user") or card.get("user_info") or item.get("user") or {}
    interact = card.get("interact_info") or item.get("interact_info") or {}

    note_id = first_present(item.get("id"), item.get("note_id"), card.get("note_id"))
    url = first_present(
        item.get("url"),
        item.get("note_url"),
        f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
    )
    raw_type = first_present(card.get("type"), item.get("note_type"))
    note_type = "video" if str(raw_type).lower() in {"video", "2"} else "image"

    images = []
    for image in ensure_list(card.get("image_list") or item.get("image_list") or item.get("images")):
        if isinstance(image, str):
            images.append(image)
        elif isinstance(image, dict):
            info_list = image.get("info_list") or []
            url_value = image.get("url")
            if info_list and isinstance(info_list[-1], dict):
                url_value = info_list[-1].get("url") or url_value
            if url_value:
                images.append(url_value)

    video_url = first_present(item.get("video_url"), item.get("video_addr"))
    video = card.get("video") or {}
    streams = (((video.get("media") or {}).get("stream") or {}).get("h264") or [])
    if not video_url and streams and isinstance(streams[0], dict):
        video_url = first_present(streams[0].get("master_url"), streams[0].get("url"))

    tags = []
    for tag in ensure_list(card.get("tag_list") or item.get("tags")):
        if isinstance(tag, str):
            tags.append(tag)
        elif isinstance(tag, dict):
            name = tag.get("name")
            if name:
                tags.append(name)

    comments = normalize_comments_raw(first_present(item.get("comments"), card.get("comments"), default=[]), note_url=url)

    return {
        "note_id": str(note_id or ""),
        "url": str(url or ""),
        "note_type": note_type,
        "title": first_present(card.get("title"), item.get("title"), default="Untitled"),
        "desc": first_present(card.get("desc"), item.get("desc")),
        "author": first_present(user.get("nickname"), item.get("nickname"), item.get("author")),
        "author_id": first_present(user.get("user_id"), item.get("user_id"), item.get("author_id")),
        "author_url": first_present(
            item.get("author_url"),
            f"https://www.xiaohongshu.com/user/profile/{first_present(user.get('user_id'), item.get('user_id'), item.get('author_id'))}" if first_present(user.get("user_id"), item.get("user_id"), item.get("author_id")) else "",
        ),
        "publish_time": first_present(card.get("time"), item.get("upload_time"), item.get("publish_time")),
        "ip_location": first_present(card.get("ip_location"), item.get("ip_location")),
        "liked_count": as_int(first_present(interact.get("liked_count"), item.get("liked_count"))),
        "collected_count": as_int(first_present(interact.get("collected_count"), item.get("collected_count"))),
        "comment_count": as_int(first_present(interact.get("comment_count"), item.get("comment_count"))),
        "share_count": as_int(first_present(interact.get("share_count"), item.get("share_count"))),
        "tags": tags,
        "images": images,
        "video_url": video_url or "",
        "comments": comments,
    }


def normalize_raw(data: Any) -> list[dict[str, Any]]:
    return [normalize_note(item) for item in extract_raw_items(data)]


def load_normalized(path: str | Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict) and isinstance(data.get("notes"), list):
        data = data["notes"]
    if not isinstance(data, list):
        raise ValueError("Normalized input must be a JSON array or an object with a notes array.")
    return [normalize_note(item) for item in data if isinstance(item, dict)]


def parse_publish_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or str(value).strip().isdigit():
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        if timestamp < 1_000_000_000:
            return None
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip().replace("Z", "+00:00")
    for candidate in (text, text[:19], text[:10]):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
        except ValueError:
            continue
    return None


def interaction_score(note: dict[str, Any], now: datetime | None = None) -> int:
    weighted = (
        math.log1p(as_int(note.get("liked_count")))
        + math.log1p(as_int(note.get("collected_count"))) * 1.5
        + math.log1p(as_int(note.get("comment_count"))) * 1.7
        + math.log1p(as_int(note.get("share_count"))) * 1.2
    )
    published = parse_publish_datetime(note.get("publish_time"))
    recency = 1.0
    if published:
        current = now or datetime.now(timezone.utc)
        current = current.replace(tzinfo=current.tzinfo or timezone.utc)
        age_days = max(0.0, (current - published.astimezone(timezone.utc)).total_seconds() / 86400)
        recency += 0.3 * math.exp(-age_days / 180)
    return round(weighted * recency * 100)


def tokenize_chinese_and_ascii(text: str) -> list[str]:
    text = text or ""
    words = [word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)]
    for chunk in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(_cut_chinese_chunk(chunk))
    stop = {"the", "and", "with", "this", "that", "for", "you", "your"}
    return [word for word in words if len(word) >= 2 and word not in stop and word not in CHINESE_STOP_WORDS]


def _cut_chinese_chunk(chunk: str) -> list[str]:
    try:
        import jieba

        jieba.setLogLevel(20)
        return [word.strip() for word in jieba.cut(chunk) if len(word.strip()) >= 2]
    except ImportError:
        matched = [term for term in FALLBACK_CHINESE_TERMS if term in chunk]
        if matched:
            return sorted(set(matched), key=lambda term: chunk.find(term))
        if len(chunk) <= 4:
            return [chunk]
        return [chunk[index:index + 2] for index in range(0, len(chunk) - 1, 2)]


def summarize_notes(notes: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(notes)
    totals = {
        "liked_count": sum(as_int(note.get("liked_count")) for note in notes),
        "collected_count": sum(as_int(note.get("collected_count")) for note in notes),
        "comment_count": sum(as_int(note.get("comment_count")) for note in notes),
        "share_count": sum(as_int(note.get("share_count")) for note in notes),
    }
    ranked = sorted(notes, key=interaction_score, reverse=True)
    tag_counter = Counter(tag for note in notes for tag in ensure_list(note.get("tags")) if tag)
    word_counter = Counter(
        word
        for note in notes
        for word in tokenize_chinese_and_ascii(f"{note.get('title', '')} {note.get('desc', '')}")
    )
    return {
        "count": count,
        "totals": totals,
        "averages": {key: math.floor(value / count) if count else 0 for key, value in totals.items()},
        "top_notes": ranked[:10],
        "top_tags": tag_counter.most_common(20),
        "top_words": word_counter.most_common(30),
        "comments": summarize_comments(flatten_note_comments(notes)),
    }


def flatten_note_comments(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comments = []
    for note in notes:
        note_url = note.get("url", "")
        note_id = note.get("note_id", "")
        for comment in ensure_list(note.get("comments")):
            if not isinstance(comment, dict):
                continue
            if "comment_id" in comment and "level" in comment:
                normalized = dict(comment)
                normalized["note_url"] = normalized.get("note_url") or note_url
            else:
                normalized = normalize_comment(comment, note_url=note_url)
            normalized["note_id"] = normalized.get("note_id") or note_id
            comments.append(normalized)
    return comments


def summarize_comments(comments: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(comments, key=lambda item: as_int(item.get("like_count")), reverse=True)
    word_counter = Counter(
        word
        for comment in comments
        for word in tokenize_chinese_and_ascii(str(comment.get("content") or ""))
    )
    author_counter = Counter(comment.get("author") for comment in comments if comment.get("author"))
    return {
        "count": len(comments),
        "top_comments": ranked[:10],
        "top_words": word_counter.most_common(30),
        "top_authors": author_counter.most_common(20),
    }


def build_markdown_report(notes: list[dict[str, Any]], source: str = "") -> str:
    summary = summarize_notes(notes)
    lines = [
        "# XHS Notes Report",
        "",
        f"- Source: {source or 'N/A'}",
        f"- Notes: {summary['count']}",
        f"- Total likes: {summary['totals']['liked_count']}",
        f"- Total collects: {summary['totals']['collected_count']}",
        f"- Total comments: {summary['totals']['comment_count']}",
        "",
        "## Top Notes",
        "",
        "| Rank | Title | Author | Likes | Collects | Comments | URL |",
        "|---:|---|---|---:|---:|---:|---|",
    ]
    for index, note in enumerate(summary["top_notes"], 1):
        title = str(note.get("title") or "Untitled").replace("|", " ")
        author = str(note.get("author") or "").replace("|", " ")
        lines.append(
            f"| {index} | {title} | {author} | {as_int(note.get('liked_count'))} | "
            f"{as_int(note.get('collected_count'))} | {as_int(note.get('comment_count'))} | {note.get('url', '')} |"
        )

    lines.extend(["", "## Frequent Tags", ""])
    if summary["top_tags"]:
        lines.append(", ".join(f"{tag} ({count})" for tag, count in summary["top_tags"][:15]))
    else:
        lines.append("No tags found.")

    lines.extend(["", "## Frequent Terms", ""])
    if summary["top_words"]:
        lines.append(", ".join(f"{word} ({count})" for word, count in summary["top_words"][:20]))
    else:
        lines.append("No repeated terms found.")

    lines.extend(["", "## Reusable Content Angles", ""])
    for note in summary["top_notes"][:5]:
        lines.append(f"- {note.get('title') or 'Untitled'}: {note.get('desc', '')[:120]}")

    comment_summary = summary.get("comments") or {}
    lines.extend(["", "## Comment Insights", ""])
    if comment_summary.get("count"):
        lines.append(f"- Comments collected: {comment_summary['count']}")
        if comment_summary.get("top_words"):
            lines.append("- Frequent comment terms: " + ", ".join(f"{word} ({count})" for word, count in comment_summary["top_words"][:20]))
        lines.append("")
        lines.append("| Rank | Content | Author | Likes | Note |")
        lines.append("|---:|---|---|---:|---|")
        for index, comment in enumerate(comment_summary.get("top_comments", [])[:10], 1):
            content = str(comment.get("content") or "").replace("|", " ").replace("\n", " ")[:120]
            author = str(comment.get("author") or "").replace("|", " ")
            lines.append(f"| {index} | {content} | {author} | {as_int(comment.get('like_count'))} | {comment.get('note_url', '')} |")
    else:
        lines.append("No comments collected. Run `collect_notes.py --include-comments` to include comment insights.")
    return "\n".join(lines) + "\n"


def write_markdown_report(path: str | Path, notes: list[dict[str, Any]], source: str = "") -> None:
    write_private_text(path, build_markdown_report(notes, source))


def write_csv(path: str | Path, notes: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=NORMALIZED_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for note in notes:
            row = dict(note)
            row["tags"] = ", ".join(map(str, ensure_list(row.get("tags"))))
            row["images"] = "\n".join(map(str, ensure_list(row.get("images"))))
            row["comments"] = json.dumps(row.get("comments") or [], ensure_ascii=False)
            writer.writerow(row)
    protect_private_file(path)


def write_comments_csv(path: str | Path, comments: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMMENT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for comment in comments:
            writer.writerow(comment)
    protect_private_file(path)


def write_xlsx(path: str | Path, notes: list[dict[str, Any]]) -> bool:
    try:
        from openpyxl import Workbook
    except Exception:
        return False
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "notes"
    ws.append(NORMALIZED_FIELDS)
    for note in notes:
        row = []
        for field in NORMALIZED_FIELDS:
            value = note.get(field, "")
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            row.append(value)
        ws.append(row)
    wb.save(path)
    protect_private_file(path)
    return True


def write_comments_xlsx(path: str | Path, comments: list[dict[str, Any]]) -> bool:
    try:
        from openpyxl import Workbook
    except Exception:
        return False
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "comments"
    ws.append(COMMENT_FIELDS)
    for comment in comments:
        ws.append([comment.get(field, "") for field in COMMENT_FIELDS])
    wb.save(path)
    protect_private_file(path)
    return True


def write_table(path_without_suffix: str | Path, notes: list[dict[str, Any]]) -> Path:
    base = Path(path_without_suffix)
    xlsx_path = base.with_suffix(".xlsx")
    if write_xlsx(xlsx_path, notes):
        return xlsx_path
    csv_path = base.with_suffix(".csv")
    write_csv(csv_path, notes)
    return csv_path


def write_comments_table(path_without_suffix: str | Path, comments: list[dict[str, Any]]) -> Path:
    base = Path(path_without_suffix)
    xlsx_path = base.with_suffix(".xlsx")
    if write_comments_xlsx(xlsx_path, comments):
        return xlsx_path
    csv_path = base.with_suffix(".csv")
    write_comments_csv(csv_path, comments)
    return csv_path
