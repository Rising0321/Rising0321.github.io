"""Refresh public Bilibili statistics, preserving old values on upstream failures."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class UpstreamError(Exception):
    pass


class Client:
    def __init__(self):
        self.blocked = set()

    def get(self, path, **params):
        if path in self.blocked:
            raise UpstreamError(f"{path}: blocked earlier in this run; not retrying")
        url = "https://api.bilibili.com" + path + "?" + urllib.parse.urlencode(params)
        for attempt in range(3):
            time.sleep(1)
            request = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bilibili.com/",
                "Accept": "application/json",
            })
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    payload = json.load(response)
                if payload.get("code") in (-412, -352):
                    self.blocked.add(path)
                    raise UpstreamError(f"{path}: Bilibili risk control ({payload['code']})")
                if payload.get("code") != 0:
                    raise UpstreamError(f"{path}: API code {payload.get('code')}")
                return payload["data"]
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 412, 429):
                    self.blocked.add(path)
                    raise UpstreamError(f"{path}: HTTP {exc.code}; upstream refused request") from exc
                if exc.code < 500 or attempt == 2:
                    raise UpstreamError(f"{path}: HTTP {exc.code}") from exc
            except (OSError, ValueError) as exc:
                if attempt == 2:
                    raise UpstreamError(f"{path}: {type(exc).__name__}") from exc
            time.sleep(2 ** (attempt + 1))


def count(value):
    if type(value) is not int or value < 0:
        raise UpstreamError("Missing or invalid statistic")
    return value


def collection_videos(client, talk):
    videos = {}
    page = 1
    expected = None
    while True:
        if talk["kind"] == "season":
            data = client.get("/x/polymer/web-space/seasons_archives_list",
                              mid=talk["mid"], season_id=talk["collection_id"],
                              page_num=page, page_size=30)
        else:
            data = client.get("/x/series/archives", mid=talk["mid"],
                              series_id=talk["collection_id"], pn=page, ps=30)
        total = count(data["page"]["total"])
        if expected is not None and total != expected:
            raise UpstreamError("Collection changed during pagination; retry next run")
        expected = total
        items = data["archives"]
        before = len(videos)
        for item in items:
            videos[item["bvid"]] = item
        if len(videos) == total:
            return list(videos.values())
        if len(videos) > total or len(videos) == before:
            raise UpstreamError("Incomplete collection pagination; refusing partial total")
        page += 1


def video_stats(client, bvid):
    data = client.get("/x/web-interface/view", bvid=bvid)
    stat = data["stat"]
    return {"views": count(stat["view"]), "likes": count(stat["like"]),
            "favorites": count(stat["favorite"])}


def refresh(talk, client, now):
    problems = []
    updated = False
    if talk.get("kind") in ("season", "series"):
        try:
            videos = collection_videos(client, talk)
            views = sum(count(video["stat"]["view"]) for video in videos)
            talk.update(views=views, video_count=len(videos), views_updated_at=now)
            updated = True
        except (UpstreamError, KeyError, TypeError) as exc:
            talk["stats_status"] = "stale"
            return False, [str(exc)]
        try:
            stats = [video_stats(client, video["bvid"]) for video in videos]
            # Only publish engagement totals if every member was fetched.
            talk.update(likes=sum(s["likes"] for s in stats),
                        favorites=sum(s["favorites"] for s in stats),
                        engagement_updated_at=now)
        except (UpstreamError, KeyError, TypeError) as exc:
            problems.append(str(exc))
    else:
        try:
            talk.update(video_stats(client, talk["bvid"]))
            talk.update(views_updated_at=now, engagement_updated_at=now)
            updated = True
        except (UpstreamError, KeyError, TypeError) as exc:
            problems.append(str(exc))
    talk["stats_status"] = "partial" if problems and updated else "stale" if problems else "fresh"
    return updated, problems


def main():
    path = Path("data/talks.json")
    talks = json.loads(path.read_text(encoding="utf-8"))
    client = Client()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = ["## Bilibili statistics", "",
            "Collection counts sum all distinct videos, not unique viewers or collectors.", ""]
    updated = 0
    degraded = 0
    for talk in talks:
        success, problems = refresh(talk, client, now)
        updated += success
        degraded += bool(problems)
        label = talk.get("bvid", f"{talk.get('kind')}:{talk.get('collection_id')}")
        rows.append(f"- {label}: {talk['stats_status']}")
        for problem in problems:
            print(f"::warning::{label}: {problem}; previous statistics retained")
            rows.append(f"  - {problem}")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(talks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    rows.append(f"\nUpdated {updated}/{len(talks)} entries; {degraded} entries need attention.")
    summary = "\n".join(rows) + "\n"
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as file:
            file.write(summary)
    # Do not mask upstream failures as a successful full refresh.
    return 1 if degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
