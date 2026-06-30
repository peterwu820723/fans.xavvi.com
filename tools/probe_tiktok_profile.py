from __future__ import annotations

import re
import sys
from urllib.request import Request, urlopen


def main() -> None:
    handle = sys.argv[1].lstrip("@") if len(sys.argv) > 1 else "jasminechiswell"
    url = f"https://www.tiktok.com/@{handle}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", "ignore")
    print("status", len(html))
    print("has_avatarLarger", "avatarLarger" in html)
    match = re.search(r"https://[^\"'<>]+(?:avatar|avt)[^\"'<>]+", html)
    print(match.group(0)[:500] if match else "no avatar url")


if __name__ == "__main__":
    main()
