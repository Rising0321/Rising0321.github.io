"""Render talks ahead of time so visitors do not need a second request or JavaScript."""
import html
import json
import re
from pathlib import Path


def escape(value):
    return html.escape(str(value), quote=True)


def render(talks, page):
    groups = {"frontier": [], "classic": [], "lightboxes": []}
    for i, talk in enumerate(talks):
        title, thumb, url = (escape(talk[key]) for key in ("title", "thumb", "url"))
        metrics = []
        for key, label in (("views", "播放 / Views"), ("likes", "点赞 / Likes"),
                           ("favorites", "收藏 / Favorites")):
            value = talk.get(key)
            text = f"{value:,}" if type(value) is int and value >= 0 else "暂不可用 / Unavailable"
            timestamp = talk.get("views_updated_at" if key == "views" else "engagement_updated_at")
            tooltip = f' title="更新于 / Updated: {escape(timestamp)}"' if timestamp else ""
            metrics.append(f'<span class="talk-views"{tooltip}>{label} {text}</span>')
        translation = (f'<p class="talk-title-en" lang="en">{escape(talk["title_en"])}</p>'
                       if talk.get("title_en") else "")
        note = ""
        if talk.get("stats_status") == "stale":
            note = "统计暂未同步 / Statistics unavailable; showing previously saved counts."
        elif talk.get("stats_status") == "partial":
            note = "点赞和收藏暂未同步 / Views updated; likes and favorites show previously saved counts."
        note = f'<p class="talk-note">{note}</p>' if note else ""
        card = f'''<article class="talk-card">
  <div class="talk-thumb"><a href="#lb-talk-{i}"><img src="{thumb}" alt="{title}" loading="lazy" /></a></div>
  <div class="talk-body">
    <h4><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h4>
    {translation}
    <div class="talk-meta">{" ".join(metrics)}</div>
    {note}
  </div>
</article>'''
        card = "\n".join(line.rstrip() for line in card.splitlines() if line.strip())
        group = "classic" if talk.get("kind") in ("season", "series") else "frontier"
        groups[group].append(card)
        groups["lightboxes"].append(
            f'<div id="lb-talk-{i}" class="lightbox-target"><a href="#" class="lightbox-close">'
            f'close</a><img src="{thumb}" alt="{title}" loading="lazy" /></div>')
    for group, entries in groups.items():
        start, end = f"<!-- talks:{group}:start -->", f"<!-- talks:{group}:end -->"
        pattern = re.escape(start) + r".*?" + re.escape(end)
        page, count = re.subn(pattern, lambda _: start + "\n" + "\n".join(entries) + "\n" + end,
                             page, flags=re.S)
        if count != 1:
            raise ValueError(f"Expected exactly one {group} render slot")
    return page


def write_page(talks):
    path = Path("index.html")
    page = path.read_bytes().decode("utf-8")
    rendered = render(talks, page)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(rendered.encode("utf-8"))
    temporary.replace(path)


if __name__ == "__main__":
    write_page(json.loads(Path("data/talks.json").read_text(encoding="utf-8")))
