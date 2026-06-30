from __future__ import annotations

import argparse
import json
import re
import ssl
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


API_URL = "https://www.tikwm.com/api/user/posts?unique_id={handle}&count={count}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def safe_slug(value: str) -> str:
    slug = value.lstrip("@").lower()
    return re.sub(r"[^a-z0-9._-]+", "-", slug).strip("-") or "unknown"


def fetch_json(url: str) -> dict:
    request = Request(url, headers=HEADERS)
    context = ssl._create_unverified_context()
    with urlopen(request, timeout=30, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, output: Path) -> int:
    request = Request(url, headers={**HEADERS, "Accept": "video/mp4,*/*"})
    context = ssl._create_unverified_context()
    with urlopen(request, timeout=60, context=context) as response:
        content = response.read()
    output.write_bytes(content)
    return len(content)


def get_top_videos(handle: str, post_count: int, top_n: int) -> list[dict]:
    payload = fetch_json(API_URL.format(handle=quote(handle), count=post_count))
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("msg") or f"API error for @{handle}")
    videos = ((payload.get("data") or {}).get("videos") or [])
    videos = [video for video in videos if video.get("play")]
    videos.sort(key=lambda item: int(item.get("play_count") or 0), reverse=True)
    return videos[:top_n]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download top TikTok videos for influencers in data/influencers.json")
    parser.add_argument("--data", default="data/influencers.json")
    parser.add_argument("--output", default="outputs/top-videos-test")
    parser.add_argument("--accounts", type=int, default=2)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--post-count", type=int, default=35)
    args = parser.parse_args()

    data_path = Path(args.data)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    influencers = json.loads(data_path.read_text(encoding="utf-8"))[: args.accounts]
    manifest: list[dict] = []

    for influencer in influencers:
        handle = influencer["handle"].lstrip("@")
        account_dir = output_dir / safe_slug(handle)
        account_dir.mkdir(parents=True, exist_ok=True)
        try:
            videos = get_top_videos(handle, args.post_count, args.top)
            for rank, video in enumerate(videos, start=1):
                video_id = str(video.get("video_id") or f"rank-{rank}")
                filename = f"{rank:02d}-{video_id}.mp4"
                path = account_dir / filename
                size = path.stat().st_size if path.exists() else download_file(video["play"], path)
                manifest.append(
                    {
                        "handle": influencer["handle"],
                        "name": influencer.get("name"),
                        "rank": rank,
                        "video_id": video_id,
                        "play_count": video.get("play_count"),
                        "digg_count": video.get("digg_count"),
                        "comment_count": video.get("comment_count"),
                        "share_count": video.get("share_count"),
                        "duration": video.get("duration"),
                        "title": video.get("title"),
                        "file": str(path.as_posix()),
                        "bytes": size,
                    }
                )
                time.sleep(0.25)
        except Exception as exc:  # noqa: BLE001 - keep batch progress visible.
            manifest.append({"handle": influencer["handle"], "error": str(exc)})

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"accounts": len(influencers), "items": len(manifest), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
