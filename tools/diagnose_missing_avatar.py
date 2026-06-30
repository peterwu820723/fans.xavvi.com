from __future__ import annotations

import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen


def main() -> None:
    handle = sys.argv[1].lstrip("@")
    request = Request(
        f"https://www.tiktok.com/@{quote(handle)}",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    html = urlopen(request, timeout=20).read().decode("utf-8", "ignore")
    snippets = re.findall(r'"statusCode":\d+|"statusMsg":"[^"]*"|"userInfo":\{[^<]{0,400}', html)
    print(f"handle={handle}")
    print(f"bytes={len(html)}")
    print(f"has_avatar_larger={'avatarLarger' in html}")
    print(f"has_avatar_medium={'avatarMedium' in html}")
    print(f"has_handle={handle in html}")
    print("snippets:")
    for snippet in snippets[:12]:
        print(snippet[:500])


if __name__ == "__main__":
    main()
