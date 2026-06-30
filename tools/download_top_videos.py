from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "https://api.tikwmapi.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
DEFAULT_OUTPUT = "assets/top-videos"
DEFAULT_DATA_OUTPUT = "data/top_videos.json"


def safe_slug(value: str) -> str:
    slug = value.lstrip("@").lower()
    return re.sub(r"[^a-z0-9._-]+", "-", slug).strip("-") or "unknown"


def web_path(path: Path) -> str:
    return path.as_posix()


def fetch_json(url: str, api_key: str | None) -> dict:
    headers = dict(HEADERS)
    if api_key:
        headers["x-tikwmapi-key"] = api_key
    request = Request(url, headers=headers)
    context = ssl._create_unverified_context()
    with urlopen(request, timeout=30, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, output: Path) -> int:
    request = Request(url, headers={**HEADERS, "Accept": "video/mp4,*/*"})
    context = ssl._create_unverified_context()
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=90, context=context) as response:
                content = response.read()
            output.write_bytes(content)
            return len(content)
        except Exception as exc:  # noqa: BLE001 - transient CDN reads are common.
            last_error = exc
            if output.exists():
                output.unlink()
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"download failed: {last_error}")


def fetch_video_page(api_base: str, api_key: str | None, handle: str, post_count: int, cursor: str | None = None) -> dict:
    params = {"unique_id": handle, "count": post_count}
    if cursor:
        params["cursor"] = cursor
    url = f"{api_base.rstrip('/')}/user/posts?{urlencode(params, quote_via=quote)}"
    for attempt in range(6):
        payload = fetch_json(url, api_key)
        if payload.get("code") == 0:
            return payload.get("data") or {}
        message = payload.get("msg") or f"API error for @{handle}"
        if "limit" not in message.lower() or attempt == 5:
            raise RuntimeError(message)
        time.sleep(1.5 + attempt * 0.5)
    return {}


def get_top_videos(
    api_base: str,
    api_key: str | None,
    handle: str,
    post_count: int,
    top_n: int,
    pages: int,
    api_delay: float,
) -> list[dict]:
    videos: list[dict] = []
    seen: set[str] = set()
    cursor: str | None = None

    for _ in range(pages):
        page = fetch_video_page(api_base, api_key, handle, post_count, cursor)
        page_videos = page.get("videos") or []
        for video in page_videos:
            video_id = str(video.get("video_id") or "")
            if video_id and video_id not in seen:
                seen.add(video_id)
                videos.append(video)
        cursor = str(page.get("cursor") or "")
        if not page.get("hasMore") or not cursor:
            break
        time.sleep(api_delay)

    videos = [video for video in videos if video.get("play")]
    videos.sort(key=lambda item: int(item.get("play_count") or 0), reverse=True)
    return videos[:top_n]


def normalize_video(influencer: dict, video: dict, rank: int, account_dir: Path) -> dict:
    video_id = str(video.get("video_id") or f"rank-{rank}")
    base = f"{rank:02d}-{video_id}"
    video_path = account_dir / f"{base}.mp4"
    cover_path = account_dir / f"{base}.webp"

    size = video_path.stat().st_size if video_path.exists() else download_file(video["play"], video_path)
    cover_url = video.get("origin_cover") or video.get("cover") or video.get("ai_dynamic_cover")
    cover_size = None
    if cover_url:
        cover_size = cover_path.stat().st_size if cover_path.exists() else download_file(cover_url, cover_path)

    return {
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
        "video": web_path(video_path),
        "thumbnail": web_path(cover_path) if cover_url else "",
        "bytes": size,
        "thumbnail_bytes": cover_size,
    }


def write_video_data(manifest: list[dict], data_output: Path) -> None:
    grouped: dict[str, list[dict]] = {}
    for item in manifest:
        if item.get("error"):
            continue
        grouped.setdefault(item["handle"], []).append(item)

    for videos in grouped.values():
        videos.sort(key=lambda item: item["rank"])

    data_output.parent.mkdir(parents=True, exist_ok=True)
    data_output.write_text(json.dumps(grouped, ensure_ascii=False, indent=2), encoding="utf-8")
    data_output.with_suffix(".js").write_text(
        "window.TOP_VIDEOS = "
        + json.dumps(grouped, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


def process_account(
    influencer: dict,
    api_base: str,
    api_key: str | None,
    output_dir: Path,
    post_count: int,
    top_n: int,
    pages: int,
    delay: float,
    api_delay: float,
) -> list[dict]:
    handle = influencer["handle"].lstrip("@")
    account_dir = output_dir / safe_slug(handle)
    account_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    videos = get_top_videos(api_base, api_key, handle, post_count, top_n, pages, api_delay)
    for rank, video in enumerate(videos, start=1):
        items.append(normalize_video(influencer, video, rank, account_dir))
        time.sleep(delay)
    return items


def write_manifest(manifest: list[dict], output_dir: Path, data_output: Path) -> None:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_video_data(manifest, data_output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download top TikTok videos for influencers in data/influencers.json")
    parser.add_argument("--data", default="data/influencers.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--data-output", default=DEFAULT_DATA_OUTPUT)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key-env", default="TIKWMAPI_KEY")
    parser.add_argument("--accounts", type=int, default=0, help="Number of accounts to process; 0 means all.")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--post-count", type=int, default=35)
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--api-delay", type=float, default=1.15)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    data_path = Path(args.data)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Missing API key. Set the {args.api_key_env} environment variable.")

    all_influencers = json.loads(data_path.read_text(encoding="utf-8"))
    influencers = all_influencers[: args.accounts] if args.accounts else all_influencers
    manifest: list[dict] = []
    data_output = Path(args.data_output)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                process_account,
                influencer,
                args.api_base,
                api_key,
                output_dir,
                args.post_count,
                args.top,
                args.pages,
                args.delay,
                args.api_delay,
            ): influencer
            for influencer in influencers
        }
        for index, future in enumerate(as_completed(futures), start=1):
            influencer = futures[future]
            try:
                manifest.extend(future.result())
            except Exception as exc:  # noqa: BLE001 - keep batch progress visible.
                manifest.append({"handle": influencer["handle"], "error": str(exc)})
            if index % 10 == 0 or index == len(influencers):
                write_manifest(manifest, output_dir, data_output)
                print(f"processed {index}/{len(influencers)}")

    manifest_path = output_dir / "manifest.json"
    write_manifest(manifest, output_dir, data_output)
    print(
        json.dumps(
            {
                "accounts": len(influencers),
                "items": len(manifest),
                "manifest": str(manifest_path),
                "data": args.data_output,
                "js": str(Path(args.data_output).with_suffix(".js")),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
