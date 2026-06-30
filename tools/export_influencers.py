from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import openpyxl


SOCIAL_LINE_RE = re.compile(r"^\s*([^:]+):\s*(https?://\S+)\s*$", re.IGNORECASE)


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def number(value) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def parse_percent(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_social_accounts(raw: str) -> list[dict[str, str]]:
    accounts: list[dict[str, str]] = []
    for line in raw.splitlines():
        match = SOCIAL_LINE_RE.match(line)
        if not match:
            continue
        platform = match.group(1).strip()
        url = match.group(2).strip()
        accounts.append({"platform": platform, "url": url})
    return accounts


def platform_url(unique_id: str) -> str:
    handle = unique_id.lstrip("@")
    return f"https://www.tiktok.com/@{quote(handle)}"


def avatar_url(unique_id: str) -> str:
    handle = unique_id.lstrip("@")
    return f"https://unavatar.io/tiktok/{quote(handle)}"


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: export_influencers.py <workbook.xlsx> <json-output> <js-output>")

    workbook_path = Path(sys.argv[1])
    json_output = Path(sys.argv[2])
    js_output = Path(sys.argv[3])

    workbook = openpyxl.load_workbook(workbook_path, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    header_row_index = None
    headers: list[str] = []

    for index, row in enumerate(rows):
        values = [clean_text(value) for value in row]
        if "Unique Id" in values and "Nickname" in values:
            header_row_index = index
            headers = values
            break

    if header_row_index is None:
        raise SystemExit("Could not find header row with Unique Id and Nickname.")

    influencers = []
    for row in rows[header_row_index + 1 :]:
        record = {headers[index]: row[index] if index < len(row) else None for index in range(len(headers))}
        nickname = clean_text(record.get("Nickname"))
        unique_id = clean_text(record.get("Unique Id"))
        if not nickname or not unique_id:
            continue

        socials = parse_social_accounts(clean_text(record.get("Social Accounts")))
        socials.insert(0, {"platform": "TikTok", "url": platform_url(unique_id)})
        influencers.append(
            {
                "id": clean_text(record.get("User Id")).rstrip("\t"),
                "name": nickname,
                "handle": unique_id if unique_id.startswith("@") else f"@{unique_id}",
                "region": clean_text(record.get("Region")),
                "category": clean_text(record.get("Main product category")) or "Uncategorized",
                "socials": socials,
                "metrics": {
                    "followers": number(record.get("Followers")),
                    "newFollowers30d": number(record.get("New followers(30day)")),
                    "likesFollowers": number(record.get("Likes/Followers")),
                    "videos": number(record.get("Videos")),
                    "averageViews30d": number(record.get("Average View(30 days)")),
                    "engagementRate": parse_percent(record.get("ER Rate")),
                    "sales": number(record.get("Sales")),
                    "gmv": number(record.get("GMV($)")),
                    "gmv30d": number(record.get("30 days GMV($)")),
                    "views30d": number(record.get("30 Days Views")),
                    "likes30d": number(record.get("30 Days Likes")),
                },
                "avatar": avatar_url(unique_id),
            }
        )

    json_output.parent.mkdir(parents=True, exist_ok=True)
    js_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(influencers, ensure_ascii=False, indent=2), encoding="utf-8")
    js_output.write_text(
        "window.INFLUENCERS = "
        + json.dumps(influencers, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(json.dumps({"count": len(influencers), "json": str(json_output), "js": str(js_output)}, indent=2))


if __name__ == "__main__":
    main()
