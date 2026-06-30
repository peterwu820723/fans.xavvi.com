from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def remove_email_fields(item: dict) -> dict:
    item.pop("email", None)
    item["socials"] = [
        social
        for social in item.get("socials", [])
        if social.get("platform") != "Email" and not str(social.get("url", "")).lower().startswith("mailto:")
    ]
    return item


def update_data() -> None:
    json_path = ROOT / "data" / "influencers.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data = [remove_email_fields(item) for item in data]
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "data" / "influencers.js").write_text(
        "window.INFLUENCERS = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def update_index() -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace("<title>Influencer Gallery</title>", "<title>Xavvi 美国美妆网红名单</title>")
    text = text.replace(
        """      <section class="topbar" aria-label="Overview">
        <div>
          <p class="eyebrow">Influencer Gallery</p>
          <h1>网红名单照片墙</h1>
        </div>""",
        """      <section class="topbar" aria-label="Overview">
        <div class="brand-title">
          <img class="brand-logo" src="assets/xavvi_logo_transp_simple.png" alt="Xavvi" />
          <p class="eyebrow">Beauty Creator Directory</p>
          <h1>Xavvi 美国美妆网红名单</h1>
        </div>""",
    )
    text = text.replace('placeholder="姓名、账号、邮箱、类别"', 'placeholder="姓名、账号、类别"')
    path.write_text(text, encoding="utf-8")


def main() -> None:
    update_data()
    update_index()


if __name__ == "__main__":
    main()
