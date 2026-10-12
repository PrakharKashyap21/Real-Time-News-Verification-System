import time
import re
import logging
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from backend.app.v2.schemas import RadarItem, RadarResponse

logger = logging.getLogger(__name__)

# Supported countries & query parameters for Google News RSS
COUNTRY_CONFIGS: Dict[str, Dict[str, str]] = {
    "IN": {
        "name": "India",
        "flag": "🇮🇳",
        "param": "gl=IN&hl=en-IN&ceid=IN:en",
        "fact_check_query": "fact check OR viral rumor OR farzi khabar OR fake news when:3d",
    },
    "US": {
        "name": "United States",
        "flag": "🇺🇸",
        "param": "gl=US&hl=en-US&ceid=US:en",
        "fact_check_query": "fact check OR debunked OR viral claim OR hoax when:3d",
    },
    "GB": {
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "param": "gl=GB&hl=en-GB&ceid=GB:en",
        "fact_check_query": "fact check OR debunked OR viral claim when:3d",
    },
    "GL": {
        "name": "Global Edition",
        "flag": "🌍",
        "param": "gl=US&hl=en-US&ceid=US:en",
        "fact_check_query": "fact check OR debunked OR viral rumor when:3d",
    },
}

DISPUTED_KEYWORDS = [
    "fact check", "fact-check", "debunk", "false claim", "hoax",
    "viral rumor", "unverified", "claim", "rumor", "fake news",
    "misleading", "conspiracy", "scam", "myth", "disputed", "viral"
]

# Cache format: { (country, category): { "timestamp": float, "items": List[RadarItem], "offset": int } }
_RADAR_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
CACHE_REFETCH_TTL = 120  # 2 minutes TTL for refetching from network
BATCH_SIZE = 12          # Number of stories presented per view
ROTATION_STEP = 6        # Shift by 6 items on rotation to bring fresh cards


def _strip_html(text: str) -> str:
    """Removes HTML tags and unescapes common HTML entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = clean.replace("&nbsp;", " ").replace("&quot;", "\"").replace("&amp;", "&").replace("&#39;", "'")
    return re.sub(r"\s+", " ", clean).strip()


def _format_time_ago(dt: datetime, now: datetime) -> Tuple[str, int]:
    """Returns human-readable relative time string and elapsed minutes."""
    diff_secs = max(0, (now - dt).total_seconds())
    mins = int(diff_secs / 60)
    if mins < 1:
        return "Just now", 0
    if mins < 60:
        return f"{mins}m ago", mins
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago", mins
    days = hours // 24
    return f"{days}d ago", mins


def _parse_pub_date(text_date: str) -> Optional[datetime]:
    """Robustly parses RFC 822 (e.g. RSS pubDate) or ISO 8601 timestamps."""
    if not text_date:
        return None
    cleaned = text_date.strip()
    dt = None
    # 1. Try RFC 822 / 2822 (standard for RSS: 'Mon, 12 Oct 2026 14:15:00 GMT')
    try:
        dt = parsedate_to_datetime(cleaned)
    except Exception:
        pass

    # 2. Try ISO 8601 (standard for Atom: '2026-10-12T14:15:00Z')
    if dt is None:
        try:
            iso_str = cleaned.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
        except Exception:
            pass

    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _fetch_single_rss(feed_url: str, default_source: str, target_cat: str) -> List[RadarItem]:
    """Fetches an individual RSS feed and converts items to RadarItem models."""
    items: List[RadarItem] = []
    now = datetime.now(timezone.utc)

    req = urllib.request.Request(
        feed_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            channel = root.find("channel")
            if channel is None:
                channel = root

            item_elements = channel.findall("item")
            # In Atom feeds, items are named <entry>
            if not item_elements:
                item_elements = root.findall("{http://www.w3.org/2005/Atom}entry")

            for idx, item_elem in enumerate(item_elements[:25]):
                title_elem = item_elem.find("title")
                if title_elem is None:
                    title_elem = item_elem.find("{http://www.w3.org/2005/Atom}title")
                if title_elem is None or not title_elem.text:
                    continue

                raw_title = title_elem.text.strip()
                if len(raw_title) < 15:
                    continue

                source_name = default_source
                clean_title = raw_title
                source_elem = item_elem.find("source")
                if source_elem is not None and source_elem.text:
                    source_name = source_elem.text.strip()
                elif " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    clean_title = parts[0].strip()
                    source_name = parts[1].strip()

                pub_elem = item_elem.find("pubDate")
                if pub_elem is None:
                    pub_elem = item_elem.find("{http://www.w3.org/2005/Atom}published")
                if pub_elem is None:
                    pub_elem = item_elem.find("{http://www.w3.org/2005/Atom}updated")

                pub_iso = None
                time_str = "Just now"
                mins_ago = 10

                if pub_elem is not None and pub_elem.text:
                    dt = _parse_pub_date(pub_elem.text)
                    if dt:
                        pub_iso = dt.isoformat()
                        time_str, mins_ago = _format_time_ago(dt, now)

                desc_elem = item_elem.find("description")
                if desc_elem is None:
                    desc_elem = item_elem.find("{http://www.w3.org/2005/Atom}summary")
                summary = ""
                if desc_elem is not None and desc_elem.text:
                    summary = _strip_html(desc_elem.text)
                if not summary or len(summary) < 20:
                    summary = f"Real-time breaking report originating from {source_name}. Fact-checking verification active."

                link_elem = item_elem.find("link")
                link_url = ""
                if link_elem is not None:
                    link_url = link_elem.text or link_elem.attrib.get("href", "")

                text_corpus = (clean_title + " " + summary).lower()
                is_disputed = any(kw in text_corpus for kw in DISPUTED_KEYWORDS)

                if is_disputed or mins_ago <= 45:
                    velocity = "HIGH"
                elif mins_ago <= 180:
                    velocity = "SURGING"
                else:
                    velocity = "MODERATE"

                category = target_cat
                if target_cat == "All":
                    if any(w in text_corpus for w in ["ai", "tech", "nvidia", "apple", "google", "meta", "openai", "software", "phone"]):
                        category = "Tech & AI"
                    elif any(w in text_corpus for w in ["health", "virus", "cancer", "space", "nasa", "planet", "vaccine", "doctor"]):
                        category = "Science & Health"
                    elif any(w in text_corpus for w in ["market", "stock", "revenue", "fed", "inflation", "economy", "bank", "nifty", "sensex"]):
                        category = "Markets & Finance"
                    else:
                        category = "World & Politics"

                prefilled = f"{clean_title}. {summary[:160]}"
                item_id = f"radar_{hash(clean_title) % 10000000}_{idx}"

                items.append(RadarItem(
                    id=item_id,
                    title=clean_title,
                    summary=summary[:280] + ("..." if len(summary) > 280 else ""),
                    category=category,
                    velocity=velocity,
                    disputed_flag=is_disputed,
                    source_preview=source_name,
                    published_time=time_str,
                    prefilled_query=prefilled,
                    pub_date_iso=pub_iso,
                    link=link_url
                ))
    except Exception as e:
        logger.debug("RSS fetch error for %s: %s", feed_url, e)

    return items


def _build_candidate_pool(country: str, category: str) -> List[RadarItem]:
    """Collects candidate stories from multiple feeds for the given country and category."""
    cfg = COUNTRY_CONFIGS.get(country, COUNTRY_CONFIGS["IN"])
    param = cfg["param"]
    fact_query = cfg["fact_check_query"].replace(" ", "+")

    feed_urls: List[Tuple[str, str]] = []

    if category == "All":
        feed_urls = [
            (f"https://news.google.com/rss?{param}", f"{cfg['name']} Top Headlines"),
            (f"https://news.google.com/rss/search?q={fact_query}&{param}", "Fact Check & Viral"),
        ]
    elif category == "Tech & AI":
        feed_urls = [
            (f"https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?{param}", "Google Tech"),
            (f"https://news.google.com/rss/search?q=artificial+intelligence+OR+AI+model+OR+tech+announcement+when:3d&{param}", "AI & Robotics"),
            ("https://www.theverge.com/rss/index.xml", "The Verge"),
        ]
    elif category == "World & Politics":
        feed_urls = [
            (f"https://news.google.com/rss/headlines/section/topic/WORLD?{param}", "World News"),
            (f"https://news.google.com/rss/headlines/section/topic/NATION?{param}", "National Politics"),
        ]
    elif category == "Science & Health":
        feed_urls = [
            (f"https://news.google.com/rss/headlines/section/topic/SCIENCE?{param}", "Science"),
            (f"https://news.google.com/rss/headlines/section/topic/HEALTH?{param}", "Health & Medicine"),
        ]
    elif category == "Markets & Finance":
        feed_urls = [
            (f"https://news.google.com/rss/headlines/section/topic/BUSINESS?{param}", "Business & Markets"),
            (f"https://news.google.com/rss/search?q=stock+market+OR+cryptocurrency+OR+inflation+when:3d&{param}", "Market Pulse"),
        ]

    pool: List[RadarItem] = []
    seen = set()

    for url, default_src in feed_urls:
        feed_items = _fetch_single_rss(url, default_src, category)
        for item in feed_items:
            norm = re.sub(r"[^a-zA-Z0-9]", "", item.title.lower())
            if norm not in seen:
                seen.add(norm)
                pool.append(item)

    # Sort candidates prioritizing high velocity / disputed claims
    pool.sort(
        key=lambda x: (
            0 if x.disputed_flag else (1 if x.velocity == "HIGH" else 2)
        )
    )
    return pool


def fetch_radar_feed(
    category: Optional[str] = None,
    country: Optional[str] = "IN",
    rotate: Optional[bool] = False
) -> RadarResponse:
    """Returns real-time radar trending feed with multi-country RSS streams and buffer rotation."""
    target_country = (country or "IN").strip().upper()
    if target_country not in COUNTRY_CONFIGS:
        target_country = "IN"

    target_cat = (category or "All").strip()
    valid_categories = ["All", "World & Politics", "Tech & AI", "Science & Health", "Markets & Finance"]
    if target_cat not in valid_categories:
        target_cat = "All"

    cache_key = (target_country, target_cat)
    now_ts = time.time()
    now_utc = datetime.now(timezone.utc)

    cached = _RADAR_CACHE.get(cache_key)

    # Determine if we should refresh candidate pool from network
    needs_network_fetch = (
        cached is None or
        (now_ts - cached["timestamp"]) > CACHE_REFETCH_TTL or
        len(cached.get("items", [])) < 6
    )

    if needs_network_fetch:
        fresh_pool = _build_candidate_pool(target_country, target_cat)
        if fresh_pool:
            _RADAR_CACHE[cache_key] = {
                "timestamp": now_ts,
                "items": fresh_pool,
                "offset": 0
            }
            cached = _RADAR_CACHE[cache_key]

    if not cached or not cached.get("items"):
        # Fallback to general pool if category yielded zero
        general_pool = _build_candidate_pool(target_country, "All")
        _RADAR_CACHE[cache_key] = {
            "timestamp": now_ts,
            "items": general_pool,
            "offset": 0
        }
        cached = _RADAR_CACHE[cache_key]

    pool = cached["items"]
    current_offset = cached.get("offset", 0)

    # If rotate requested, advance offset to present fresh stories from pool
    if rotate and len(pool) > BATCH_SIZE:
        current_offset = (current_offset + ROTATION_STEP) % len(pool)
        cached["offset"] = current_offset

    # Slice batch of stories using current offset
    selected_items: List[RadarItem] = []
    pool_len = len(pool)
    take_count = min(BATCH_SIZE, pool_len)

    for i in range(take_count):
        idx = (current_offset + i) % pool_len
        item = pool[idx]

        # Dynamically refresh relative published_time strings
        it_dict = item.model_dump()
        if item.pub_date_iso:
            try:
                dt = datetime.fromisoformat(item.pub_date_iso)
                it_dict["published_time"], _ = _format_time_ago(dt, now_utc)
            except Exception:
                pass
        selected_items.append(RadarItem(**it_dict))

    return RadarResponse(
        last_updated=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        total_active_stories=pool_len,
        categories=valid_categories,
        country=target_country,
        items=selected_items
    )
