import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

CISA_RSS_URLS = (
    "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml",
    "https://www.cisa.gov/uscert/ncas/alerts.xml",
)
CISA_LIST_URL = "https://www.cisa.gov/news-events/ics-advisories"
CISA_ORIGIN = "https://www.cisa.gov"
CACHE_TTL_SECONDS = 15 * 60
MAX_ITEMS = 5

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_cache = {"items": None, "ts": 0.0}

_ICS_HREF = re.compile(
    r'href="((?:https://www\.cisa\.gov)?/news-events/ics-advisories/(icsa-[a-z0-9-]+))"',
    re.IGNORECASE,
)
_ICS_HREF_TITLE = re.compile(
    r'href="((?:https://www\.cisa\.gov)?/news-events/ics-advisories/icsa-[^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG = re.compile(r"<[^>]+>")
_TIME_DT = re.compile(r'<time[^>]*datetime="([^"]+)"', re.IGNORECASE)


def _local_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _child_text(el, *names: str) -> str:
    wanted = {n.lower() for n in names}
    for child in list(el):
        if _local_tag(child.tag).lower() not in wanted:
            continue
        text = "".join(child.itertext()).strip()
        if text:
            return text
    return ""


def _child_link(el) -> str:
    for child in list(el):
        if _local_tag(child.tag).lower() != "link":
            continue
        href = (child.get("href") or child.text or "").strip()
        if href:
            return href
    return ""


def _absolute_link(link: str) -> str:
    if not link or link == "#":
        return ""
    if link.startswith("//"):
        return f"https:{link}"
    if link.startswith("/"):
        return f"{CISA_ORIGIN}{link}"
    return link


def _clean_title(title: str) -> str:
    text = re.sub(r"^ICS(?:A|MA)?-\d{2}-\d{3}-\d{2}:\s*", "", title or "", flags=re.IGNORECASE)
    text = re.sub(r"^ICS Advisory\s*\|\s*ICS(?:A|MA)?-\d{2}-\d{3}-\d{2}\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalize(title: str, link: str, pub_date: Optional[str]) -> Optional[Dict[str, str]]:
    title = _clean_title(title)
    link = _absolute_link(link)
    if not title or not link or title.lower() in {"read more", "ics advisories"}:
        return None
    return {"title": title, "link": link, "pubDate": pub_date or ""}


def _dedupe(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    unique = []
    for item in items:
        key = item["link"].rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:MAX_ITEMS]


def _parse_xml_feed(xml_text: str) -> List[Dict[str, str]]:
    root = ET.fromstring(xml_text)
    nodes = [el for el in root.iter() if _local_tag(el.tag).lower() in {"item", "entry"}]
    items = []
    for node in nodes:
        items.append(
            _normalize(
                _child_text(node, "title"),
                _child_link(node) or _child_text(node, "link"),
                _child_text(node, "pubDate", "published", "updated", "date"),
            )
        )
    return _dedupe([item for item in items if item])


def _parse_html_listing(html: str) -> List[Dict[str, str]]:
    items = []
    for match in _ICS_HREF_TITLE.finditer(html):
        href, title = match.group(1), _TAG.sub("", match.group(2))
        window_start = max(0, match.start() - 800)
        nearby = html[window_start:match.start()]
        times = _TIME_DT.findall(nearby)
        pub_date = times[-1] if times else ""
        items.append(_normalize(title, href, pub_date))

    if not items:
        for match in _ICS_HREF.finditer(html):
            items.append(_normalize(match.group(2).replace("-", " ").upper(), match.group(1), ""))

    return _dedupe([item for item in items if item])


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    return response.text


async def _load_advisories() -> List[Dict[str, str]]:
    now = time.time()
    if _cache["items"] and now - _cache["ts"] < CACHE_TTL_SECONDS:
        return _cache["items"]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=_HEADERS) as client:
        for rss_url in CISA_RSS_URLS:
            try:
                items = _parse_xml_feed(await _fetch_text(client, rss_url))
                if items:
                    _cache.update({"items": items, "ts": now})
                    return items
            except Exception:
                continue

        try:
            items = _parse_html_listing(await _fetch_text(client, CISA_LIST_URL))
            if items:
                _cache.update({"items": items, "ts": now})
                return items
        except Exception as exc:
            raise HTTPException(status_code=502, detail="CISA advisory source unavailable") from exc

    raise HTTPException(status_code=502, detail="No advisories found")


@router.get("/news")
async def get_ics_news():
    return {"items": await _load_advisories()}
