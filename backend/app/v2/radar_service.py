import time
import logging
from typing import List, Optional
from backend.app.v2.schemas import RadarItem, RadarResponse

logger = logging.getLogger(__name__)

# Curated high-impact real-world and viral benchmark stories
CURATED_RADAR_STORIES: List[RadarItem] = [
    RadarItem(
        id="radar_ai_gpt5",
        title="OpenAI Officially Launches Autonomous Operating System Agent",
        summary="Viral claims across X assert OpenAI has quietly deployed an autonomous OS agent operating across desktop environments without human oversight.",
        category="Tech & AI",
        velocity="HIGH",
        disputed_flag=True,
        source_preview="Viral on X / Tech Blogs",
        published_time="18m ago",
        prefilled_query="OpenAI launched an autonomous operating system agent that controls desktop computers without user oversight."
    ),
    RadarItem(
        id="radar_james_webb",
        title="James Webb Space Telescope Confirms Atmospheric Signs of Life on Exoplanet K2-18b",
        summary="Headlines circulate claiming NASA and ESA confirmed definitive biosignatures and alien life evidence in exoplanet K2-18b's dimethyl sulfide spectrum.",
        category="Science & Health",
        velocity="HIGH",
        disputed_flag=True,
        source_preview="Social Media / Science Forums",
        published_time="42m ago",
        prefilled_query="James Webb Space Telescope confirmed definitive proof of alien life on exoplanet K2-18b."
    ),
    RadarItem(
        id="radar_trent_earnings",
        title="Tata Group Retail Arm Trent Reports Surging Q2 Net Profit Growth",
        summary="Financial outlets and market commentary report Tata's Trent registered a 46% year-on-year surge in standalone revenue led by Zudio and Westside expansion.",
        category="Markets & Finance",
        velocity="SURGING",
        disputed_flag=False,
        source_preview="Financial Express / Business Standard",
        published_time="1h ago",
        prefilled_query="Tata Trent Q2 standalone revenue grew 46 percent year-on-year driven by store expansion in Zudio."
    ),
    RadarItem(
        id="radar_eu_climate",
        title="European Union Legally Mandates 100% Zero-Emission New Passenger Cars by 2035",
        summary="Reports claim the EU has officially enacted a complete prohibition on sales of new internal combustion engine cars starting in 2035.",
        category="World & Politics",
        velocity="SURGING",
        disputed_flag=False,
        source_preview="Reuters / EU Commission Portal",
        published_time="2h ago",
        prefilled_query="European Union approves law banning the sale of new internal combustion engine cars by 2035."
    ),
    RadarItem(
        id="radar_lemon_cure",
        title="Viral Health Directive Claims Warm Alkaline Lemon Water Completely Eradicates Cancer",
        summary="Widely forwarded WhatsApp and Facebook chain post claims drinking boiling lemon water with baking soda destroys malignant cancer cells without chemotherapy.",
        category="Science & Health",
        velocity="HIGH",
        disputed_flag=True,
        source_preview="WhatsApp Chain / Viral Facebook Post",
        published_time="3h ago",
        prefilled_query="Drinking hot lemon water cures all forms of cancer and eliminates need for chemotherapy."
    ),
    RadarItem(
        id="radar_nvidia_chip",
        title="Nvidia Unveils Next-Generation AI Architecture Accelerators with 5x Efficiency",
        summary="Tech publications analyze Nvidia's latest data center silicon roadmap promising fivefold energy efficiency gains for large language model inference.",
        category="Tech & AI",
        velocity="MODERATE",
        disputed_flag=False,
        source_preview="Reuters / TechCrunch",
        published_time="4h ago",
        prefilled_query="Nvidia announced next-generation AI accelerators with significant inference performance improvements."
    ),
    RadarItem(
        id="radar_un_treaty",
        title="United Nations High Seas Treaty Enters Ratification Milestone Ahead of Global Deadline",
        summary="Diplomats announce over 60 member nations have deposited instruments of ratification to legally protect international marine biodiversity.",
        category="World & Politics",
        velocity="MODERATE",
        disputed_flag=False,
        source_preview="UN Press / Associated Press",
        published_time="5h ago",
        prefilled_query="United Nations High Seas Treaty reaches global ratification threshold to protect biodiversity in international waters."
    ),
    RadarItem(
        id="radar_moon_helium",
        title="Private Lunar Mission Claims Extraction of High-Purity Helium-3 for Clean Fusion",
        summary="Social posts claim a private aerospace startup successfully landed on the lunar South Pole and extracted commercial Helium-3 canisters.",
        category="Science & Health",
        velocity="HIGH",
        disputed_flag=True,
        source_preview="Viral Thread / Unverified Video",
        published_time="6h ago",
        prefilled_query="Private space company extracted commercial Helium-3 from the moon for nuclear fusion."
    )
]

def fetch_radar_feed(category: Optional[str] = None) -> RadarResponse:
    """Returns real-time radar trending feed with optional category filter."""
    items = list(CURATED_RADAR_STORIES)
    
    # Try fetching fresh live news via DuckDuckGo news search if available
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            search_query = "breaking news fact check" if not category or category == "All" else f"breaking {category}"
            live_news = list(ddgs.news(keywords=search_query, max_results=4))
            for i, news in enumerate(live_news):
                title = news.get("title", "").strip()
                body = news.get("body", "").strip()
                source = news.get("source", "Live Web News")
                date = news.get("date", "Just now")
                if title and len(title) > 15:
                    cat = category if category and category != "All" else "World & Politics"
                    items.insert(i, RadarItem(
                        id=f"live_radar_{i}_{int(time.time())}",
                        title=title,
                        summary=body or f"Breaking real-time report from {source}.",
                        category=cat,
                        velocity="SURGING",
                        disputed_flag=False,
                        source_preview=source,
                        published_time="Live Now",
                        prefilled_query=f"{title}. {body[:150]}"
                    ))
    except Exception as e:
        logger.debug("Live DDG news search in radar feed fallback to curated catalog: %s", e)

    if category and category.strip().lower() != "all":
        c_low = category.strip().lower()
        items = [
            item for item in items
            if c_low in item.category.lower()
            or item.category.lower() in c_low
            or (c_low.startswith("tech") and "tech" in item.category.lower())
            or (c_low.startswith("sci") and "sci" in item.category.lower())
            or (c_low.startswith("pol") and "pol" in item.category.lower())
            or (c_low.startswith("fin") or c_low.startswith("bus") and "market" in item.category.lower())
        ]

    categories = ["All", "World & Politics", "Tech & AI", "Science & Health", "Markets & Finance"]

    return RadarResponse(
        last_updated=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        total_active_stories=len(items),
        categories=categories,
        items=items[:12]
    )
