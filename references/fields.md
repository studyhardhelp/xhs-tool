# Normalized Fields

Each note must be normalized before reporting.

Required fields:

- `note_id`: XHS note id.
- `url`: note URL.
- `note_type`: `image` or `video`.
- `title`: note title.
- `desc`: note body text.
- `author`: author nickname.
- `author_id`: author user id.
- `author_url`: author profile URL when available.
- `publish_time`: source publish timestamp or formatted publish time.
- `ip_location`: source IP location label when present.
- `liked_count`: integer like count.
- `collected_count`: integer collect count.
- `comment_count`: integer comment count.
- `share_count`: integer share count.
- `tags`: list of topic/tag names.
- `images`: list of image URLs.
- `video_url`: video URL when present.
- `comments`: normalized comment objects.

Comment fields:

- `note_id`: note id associated with the comment.
- `note_url`: note URL.
- `comment_id`: comment id.
- `parent_comment_id`: parent comment id for sub-comments.
- `root_comment_id`: root comment id.
- `level`: `1` for root comments, `2` for sub-comments.
- `author`: comment author nickname.
- `author_id`: comment author user id.
- `content`: comment text.
- `like_count`: integer comment like count.
- `publish_time`: source publish timestamp or formatted publish time.
- `ip_location`: source IP location label when present.

Do not build reports from raw Spider_XHS response structures. Always run `normalize_xhs.py` or `collect_notes.py` first.
