#!/usr/bin/env python3
from __future__ import annotations

import io
import os
import re
import sys
from typing import List, Tuple

import requests
from PIL import Image

# --------- CONFIG ---------
OUTPUT_PATH = "assets/banner.gif"

# Canvas / animation
CANVAS_W = 1200          # output width (px) – fits nicely on GitHub
CANVAS_H = 70            # output height (px)
PADDING_X = 10           # spacing between badges
SPEED_PX_PER_FRAME = 3   # higher = faster scroll
FPS = 25                 # frames per second
DURATION_SECONDS = 100    # total loop duration

# Background (RGB)
BG = (13, 17, 23)        # GitHub dark-ish; tweak if you use light theme
# --------------------------

BADGE_URLS: List[str] = [
    "https://img.shields.io/badge/Vault-FFD814?style=for-the-badge&logo=vault&logoColor=black",
    "https://img.shields.io/badge/Wazuh-005792?style=for-the-badge&logo=wazuh&logoColor=white",
    "https://img.shields.io/badge/Keycloak-008AAA?style=for-the-badge&logo=keycloak&logoColor=white",
    "https://img.shields.io/badge/wiki.js-1976D2?style=for-the-badge&logo=wikidotjs&logoColor=white",
    "https://img.shields.io/badge/GitLab-FC6D26?style=for-the-badge&logo=gitlab&logoColor=white",
    "https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white",
    "https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white",
    "https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white",
    "https://img.shields.io/badge/Portainer-13BEF9?style=for-the-badge&logo=portainer&logoColor=white",
    "https://img.shields.io/badge/Nextcloud-0082C9?style=for-the-badge&logo=nextcloud&logoColor=white",
    "https://img.shields.io/badge/WordPress-21759B?style=for-the-badge&logo=wordpress&logoColor=white",
    "https://img.shields.io/badge/InfluxDB-22ADF6?style=for-the-badge&logo=influxdb&logoColor=white",
    "https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white",
    "https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white",
    "https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white",
    "https://img.shields.io/badge/ArangoDB-DDE072?style=for-the-badge&logo=arangodb&logoColor=black",
    "https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white",
    "https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white",
    "https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white",
    "https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white",
    "https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white",
    "https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white",
    "https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=cplusplus&logoColor=white",
]

def fetch_badge_png(url: str) -> Image.Image:
    # Convert shields URL to a PNG endpoint:
    # https://img.shields.io/badge/NAME-COLOR?...  ->  https://img.shields.io/badge/NAME-COLOR.png?...
    if "img.shields.io/badge/" in url and not url.endswith(".png"):
        if "?" in url:
            base, qs = url.split("?", 1)
            png_url = base + ".png?" + qs
        else:
            png_url = url + ".png"
    else:
        png_url = url

    headers = {
        "User-Agent": "Mozilla/5.0 (GitHub-README-banner/1.0)",
        "Accept": "image/png,image/*;q=0.9,*/*;q=0.8",
    }

    r = requests.get(png_url, headers=headers, timeout=30)
    r.raise_for_status()

    ctype = (r.headers.get("Content-Type") or "").lower()
    if "image" not in ctype:
        # Helpful debug if shields returns HTML/SVG/error page
        snippet = r.text[:200].replace("\n", " ")
        raise RuntimeError(f"Unexpected Content-Type: {ctype}. Response starts with: {snippet!r}")

    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    return img


def fit_height(img: Image.Image, target_h: int) -> Image.Image:
    w, h = img.size
    if h == target_h:
        return img
    scale = target_h / float(h)
    new_w = max(1, int(w * scale))
    return img.resize((new_w, target_h), Image.LANCZOS)

def compose_strip(badges: List[Image.Image], padding_x: int, bg: Tuple[int,int,int]) -> Image.Image:
    # Normalize heights to a consistent badge height
    badge_h = CANVAS_H - 20  # leave some breathing room
    resized = [fit_height(b, badge_h) for b in badges]

    total_w = sum(b.size[0] for b in resized) + padding_x * (len(resized) - 1)
    strip = Image.new("RGBA", (total_w, badge_h), (*bg, 255))

    x = 0
    for b in resized:
        strip.alpha_composite(b, (x, 0))
        x += b.size[0] + padding_x

    return strip

def main() -> int:
    print(f"Downloading {len(BADGE_URLS)} badges…")
    badges: List[Image.Image] = []
    for url in BADGE_URLS:
        try:
            badges.append(fetch_badge_png(url))
        except Exception as e:
            print(f"[WARN] Failed: {url}\n  -> {e}", file=sys.stderr)

    if not badges:
        print("No badges downloaded. Exiting.", file=sys.stderr)
        return 1

    strip = compose_strip(badges, PADDING_X, BG)

    # Duplicate strip so scrolling wraps seamlessly
    strip2 = Image.new("RGBA", (strip.size[0] * 2 + CANVAS_W, strip.size[1]), (*BG, 255))
    strip2.alpha_composite(strip, (0, 0))
    strip2.alpha_composite(strip, (strip.size[0] + CANVAS_W, 0))

    frames: List[Image.Image] = []
    total_frames = max(1, int(FPS * DURATION_SECONDS))
    y = (CANVAS_H - strip.size[1]) // 2

    # How far we need to move to complete one clean loop
    loop_distance = strip.size[0] + CANVAS_W
    step = max(1, int(loop_distance / total_frames))

    x = 0
    for _ in range(total_frames):
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (*BG, 255))
        # Crop moving window from the long strip2
        window = strip2.crop((x, 0, x + CANVAS_W, strip.size[1]))
        canvas.alpha_composite(window, (0, y))
        frames.append(canvas.convert("P", palette=Image.ADAPTIVE))
        x = (x + step) % loop_distance

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    duration_ms = int(1000 / FPS)
    frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )

    print(f"✅ Wrote {OUTPUT_PATH} ({len(frames)} frames @ {FPS}fps)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
