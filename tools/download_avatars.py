from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


PROFILE_URL = "https://www.tiktok.com/@{handle}"
API_URL = "https://www.tikwm.com/api/user/info?unique_id={handle}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def safe_slug(handle: str) -> str:
    value = handle.lstrip("@").lower()
    return re.sub(r"[^a-z0-9._-]+", "-", value).strip("-") or "avatar"


def fetch_json(url: str) -> dict:
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def download_bytes(url: str) -> bytes:
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=25) as response:
        return response.read()


def fetch_profile_avatar_url(handle: str) -> str | None:
    request = Request(PROFILE_URL.format(handle=quote(handle)), headers=HEADERS)
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", "ignore")
    match = re.search(r'"avatarLarger":"([^"]+)"', html)
    if not match:
        match = re.search(r'"avatarMedium":"([^"]+)"', html)
    if not match:
        return None
    return json.loads(f'"{match.group(1)}"')


def fetch_api_avatar_url(handle: str) -> str | None:
    payload = fetch_json(API_URL.format(handle=quote(handle)))
    user = (payload.get("data") or {}).get("user") or {}
    return user.get("avatarLarger") or user.get("avatarMedium") or user.get("avatarThumb")


def download_avatar(influencer: dict, output_dir: Path) -> tuple[str, str | None, str | None]:
    handle = influencer["handle"].lstrip("@")
    slug = safe_slug(handle)
    output = output_dir / f"{slug}.webp"
    if output.exists() and output.stat().st_size > 1024:
        return influencer["handle"], f"assets/avatars/{output.name}", None

    try:
        avatar_url = fetch_profile_avatar_url(handle) or fetch_api_avatar_url(handle)
        if not avatar_url:
            return influencer["handle"], None, "missing avatar"

        content = download_bytes(avatar_url)
        if len(content) < 1024:
            return influencer["handle"], None, "avatar response too small"
        output.write_bytes(content)
        time.sleep(0.05)
        return influencer["handle"], f"assets/avatars/{output.name}", None
    except Exception as exc:  # noqa: BLE001 - record per-profile failures without aborting.
        return influencer["handle"], None, str(exc)


def main() -> None:
    if len(sys.argv) not in (4, 5):
        raise SystemExit("Usage: download_avatars.py <data.json> <output-dir> <limit> [workers]")

    data_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    limit = int(sys.argv[3])
    workers = int(sys.argv[4]) if len(sys.argv) == 5 else 8
    output_dir.mkdir(parents=True, exist_ok=True)

    influencers = json.loads(data_path.read_text(encoding="utf-8"))
    selected = influencers[:limit]
    paths: dict[str, str] = {}
    errors: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download_avatar, influencer, output_dir) for influencer in selected]
        for future in as_completed(futures):
            handle, path, error = future.result()
            if path:
                paths[handle] = path
            if error:
                errors.append({"handle": handle, "error": error})

    for influencer in influencers:
        local_path = paths.get(influencer["handle"])
        if local_path:
            influencer["avatarLocal"] = local_path

    data_path.write_text(json.dumps(influencers, ensure_ascii=False, indent=2), encoding="utf-8")
    js_path = data_path.with_suffix(".js")
    js_path.write_text(
        "window.INFLUENCERS = "
        + json.dumps(influencers, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "requested": len(selected),
                "downloaded": len(paths),
                "errors": len(errors),
                "sample_errors": errors[:10],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
