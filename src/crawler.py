"""
Market, Competitor & Policy Intelligence Crawler
Author: NovaFactory AI Intelligence Team
"""

import os
import sys
import time
import logging
import datetime
import urllib.parse
from typing import List, Dict, Any, Tuple
import xml.etree.ElementTree as ET

import yaml
import pandas as pd
import requests
import feedparser

# Configure paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "company_profile.yaml")
DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_FALLBACK_DIR = os.path.join(PROJECT_ROOT, "data", "fallback")
OUTPUT_CSV = os.path.join(DATA_RAW_DIR, "crawled_market_news.csv")
FALLBACK_CSV = os.path.join(DATA_FALLBACK_DIR, "fallback_market_news.csv")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "crawler.log")

os.makedirs(DATA_RAW_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}


def load_company_profile(config_path: str) -> Dict[str, Any]:
    """Load company profile configuration."""
    if not os.path.exists(config_path):
        logger.warning(f"Company profile not found at {config_path}. Using default fallback config.")
        return {
            "company_name": "NovaFactory AI",
            "business_area": "제조업 AI 비전 품질검사",
            "competitors": ["VisionForge", "InspectAI", "FactoryMind", "QualiBot", "CogniSense"],
            "interest_keywords": ["AI", "머신비전", "스마트팩토리", "품질검사", "자동화", "제조 AX", "불량 탐지"],
            "funding_keywords": ["창업지원", "AI 바우처", "스마트공장", "R&D", "사업화 자금", "TIPS"]
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_pub_date(entry: Any) -> str:
    """Parse date from feed entry into YYYY-MM-DD."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return time.strftime("%Y-%m-%d", entry.published_parsed)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return time.strftime("%Y-%m-%d", entry.updated_parsed)
    return datetime.date.today().strftime("%Y-%m-%d")


def crawl_google_news_rss(query: str, category: str, limit: int = 100) -> Tuple[List[Dict[str, Any]], bool, str]:
    """Crawl Google News RSS for a specific query."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    logger.info(f"Fetching Google News RSS for '{query}' (Category: {category})...")
    
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        if resp.status_code != 200:
            return [], False, f"HTTP Status {resp.status_code}"
        
        feed = feedparser.parse(resp.content)
        articles = []
        now_iso = datetime.datetime.now().astimezone().isoformat()
        
        for entry in feed.entries[:limit]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "").strip()
            pub_date = parse_pub_date(entry)
            source_name = "Google News"
            if hasattr(entry, "source") and entry.source and "title" in entry.source:
                source_name = entry.source.title
            
            if title and link:
                articles.append({
                    "category": category,
                    "title": title,
                    "date": pub_date,
                    "content": summary or title,
                    "summary": summary or title,
                    "source_url": link,
                    "source_name": source_name,
                    "company_tag": None,
                    "keywords": query.replace(" ", "|"),
                    "collected_at": now_iso,
                    "has_null": False,
                    "is_duplicate_seed": False,
                    "data_origin": "live_crawl"
                })
        
        logger.info(f"Successfully collected {len(articles)} items for query '{query}'.")
        return articles, True, "OK"
    except Exception as e:
        logger.error(f"Failed to crawl Google News RSS for '{query}': {e}")
        return [], False, str(e)


def crawl_geeknews_rss(limit: int = 50) -> Tuple[List[Dict[str, Any]], bool, str]:
    """Crawl GeekNews RSS for IT and technology trends."""
    url = "https://news.hada.io/rss/news"
    logger.info("Fetching GeekNews RSS (Category: technology)...")
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        if resp.status_code != 200:
            return [], False, f"HTTP Status {resp.status_code}"
        
        feed = feedparser.parse(resp.content)
        articles = []
        now_iso = datetime.datetime.now().astimezone().isoformat()
        
        for entry in feed.entries[:limit]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "").strip()
            pub_date = parse_pub_date(entry)
            
            if title and link:
                articles.append({
                    "category": "technology",
                    "title": title,
                    "date": pub_date,
                    "content": summary or title,
                    "summary": summary or title,
                    "source_url": link,
                    "source_name": "GeekNews",
                    "company_tag": None,
                    "keywords": "AI|기술동향|IT",
                    "collected_at": now_iso,
                    "has_null": False,
                    "is_duplicate_seed": False,
                    "data_origin": "live_crawl"
                })
        logger.info(f"Successfully collected {len(articles)} items from GeekNews.")
        return articles, True, "OK"
    except Exception as e:
        logger.error(f"Failed to crawl GeekNews RSS: {e}")
        return [], False, str(e)


def crawl_arxiv_api(query: str = "defect detection vision", limit: int = 30) -> Tuple[List[Dict[str, Any]], bool, str]:
    """Crawl ArXiv Open API for computer vision & defect detection research."""
    encoded = urllib.parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded}&start=0&max_results={limit}"
    logger.info(f"Fetching ArXiv API for '{query}' (Category: technology)...")
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if resp.status_code != 200:
            return [], False, f"HTTP Status {resp.status_code}"
        
        feed = feedparser.parse(resp.content)
        articles = []
        now_iso = datetime.datetime.now().astimezone().isoformat()
        
        for entry in feed.entries:
            title = entry.get("title", "").replace("\n", " ").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "").replace("\n", " ").strip()
            pub_date = parse_pub_date(entry)
            
            if title and link:
                articles.append({
                    "category": "technology",
                    "title": title,
                    "date": pub_date,
                    "content": summary,
                    "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                    "source_url": link,
                    "source_name": "ArXiv",
                    "company_tag": None,
                    "keywords": "Computer Vision|Defect Detection|Research",
                    "collected_at": now_iso,
                    "has_null": False,
                    "is_duplicate_seed": False,
                    "data_origin": "live_crawl"
                })
        logger.info(f"Successfully collected {len(articles)} items from ArXiv.")
        return articles, True, "OK"
    except Exception as e:
        logger.error(f"Failed to fetch ArXiv API: {e}")
        return [], False, str(e)


def run_collection() -> Dict[str, Any]:
    """Execute collection pipeline following source plan with automatic fallback."""
    profile = load_company_profile(CONFIG_PATH)
    all_articles: List[Dict[str, Any]] = []
    failed_sources: List[Dict[str, str]] = []
    
    # 1. Primary Queries from Company Profile
    queries = [
        # (Query, Category, Source Type)
        ("스마트팩토리 AI 제조", "market", "Google News RSS"),
        ("제조 AX 공정 자동화", "market", "Google News RSS"),
        ("머신비전 품질검사 불량탐지", "technology", "Google News RSS"),
        ("AI 바우처 스마트공장 지원사업", "funding", "Google News RSS"),
        ("중기부 스마트제조 R&D 지원", "policy", "Google News RSS"),
        ("비전 AI 검사 솔루션", "technology", "Google News RSS"),
    ]
    
    # Add Competitor Queries
    competitors = profile.get("competitors", [])
    if competitors:
        comp_query = " OR ".join(competitors[:4])
        queries.append((comp_query, "competitor", "Google News RSS (Competitors)"))
        # Also add real industry competitor search query for machine vision market
        queries.append(("머신비전 비전검사 솔루션 경쟁사", "competitor", "Google News RSS (Competitors)"))
    
    # Execute primary queries
    for q, cat, source_label in queries:
        items, success, err = crawl_google_news_rss(q, category=cat, limit=100)
        if success:
            all_articles.extend(items)
        else:
            failed_sources.append({"source": f"{source_label}: {q}", "error": err})
        time.sleep(0.3)
    
    # 2. Check volume; if under 200, invoke secondary sources
    seen_urls = set()
    unique_articles = []
    for art in all_articles:
        if art["source_url"] not in seen_urls:
            seen_urls.add(art["source_url"])
            unique_articles.append(art)
    
    logger.info(f"Current unique live articles count: {len(unique_articles)}")
    
    if len(unique_articles) < 200:
        logger.info("Live collection count < 200. Invoking secondary sources (GeekNews, ArXiv, extra queries)...")
        # GeekNews
        gn_items, gn_ok, gn_err = crawl_geeknews_rss(limit=50)
        if gn_ok:
            for item in gn_items:
                if item["source_url"] not in seen_urls:
                    seen_urls.add(item["source_url"])
                    unique_articles.append(item)
        else:
            failed_sources.append({"source": "GeekNews RSS", "error": gn_err})
            
        # ArXiv API
        ax_items, ax_ok, ax_err = crawl_arxiv_api("defect detection machine vision manufacturing", limit=30)
        if ax_ok:
            for item in ax_items:
                if item["source_url"] not in seen_urls:
                    seen_urls.add(item["source_url"])
                    unique_articles.append(item)
        else:
            failed_sources.append({"source": "ArXiv API", "error": ax_err})
            
        # Additional keywords if still needed
        extra_keywords = ["딥테크 TIPS 창업지원", "산업용 AI 검사", "스마트 팩토리 비전 센서"]
        for eq in extra_keywords:
            if len(unique_articles) >= 200:
                break
            e_items, e_ok, e_err = crawl_google_news_rss(eq, category="market", limit=50)
            if e_ok:
                for item in e_items:
                    if item["source_url"] not in seen_urls:
                        seen_urls.add(item["source_url"])
                        unique_articles.append(item)
            else:
                failed_sources.append({"source": f"Google News RSS Extra: {eq}", "error": e_err})
            time.sleep(0.3)

    live_count = len(unique_articles)
    fallback_count = 0
    final_articles = list(unique_articles)
    
    # 3. Fallback blending if still under 200
    if len(final_articles) < 200:
        logger.warning(f"Live collection count ({len(final_articles)}) is under 200. Blending fallback dataset...")
        if os.path.exists(FALLBACK_CSV):
            fallback_df = pd.read_csv(FALLBACK_CSV)
            needed = 200 - len(final_articles) + 20  # buffer
            fallback_sample = fallback_df.head(needed)
            fallback_records = fallback_sample.to_dict(orient="records")
            final_articles.extend(fallback_records)
            fallback_count = len(fallback_records)
            logger.info(f"Added {fallback_count} records from fallback dataset.")
        else:
            logger.error(f"Fallback CSV not found at {FALLBACK_CSV}!")
    else:
        logger.info(f"Live collection exceeded target ({len(final_articles)} >= 200).")

    # 4. Standardize and assign article IDs
    df = pd.DataFrame(final_articles)
    
    # Assign article IDs if not present or live crawl
    article_ids = []
    for idx, row in df.iterrows():
        if pd.notna(row.get("article_id")) and str(row.get("article_id")).startswith("FB-"):
            article_ids.append(row["article_id"])
        else:
            article_ids.append(f"CR-{idx+1:04d}")
    df["article_id"] = article_ids
    
    # Ensure all required schema columns exist
    schema_cols = [
        "article_id", "category", "title", "date", "content", "summary",
        "source_url", "source_name", "company_tag", "keywords",
        "collected_at", "has_null", "is_duplicate_seed", "data_origin"
    ]
    for col in schema_cols:
        if col not in df.columns:
            df[col] = None
    
    # Reorder columns
    df = df[schema_cols]
    
    # Save to CSV
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(df)} records to {OUTPUT_CSV}.")
    
    return {
        "total_count": len(df),
        "live_count": live_count,
        "fallback_count": fallback_count,
        "failed_sources": failed_sources,
        "output_path": OUTPUT_CSV,
        "categories": df["category"].value_counts().to_dict(),
        "data_origin": df["data_origin"].value_counts().to_dict()
    }


if __name__ == "__main__":
    result = run_collection()
    print("\n" + "="*50)
    print(" CRAWLER EXECUTION SUMMARY")
    print("="*50)
    print(f"- Total Collected: {result['total_count']}")
    print(f"- Live Crawled: {result['live_count']}")
    print(f"- Fallback Used: {result['fallback_count']}")
    print(f"- Data Origin Breakdown: {result['data_origin']}")
    print(f"- Category Breakdown: {result['categories']}")
    print(f"- Failed Sources Count: {len(result['failed_sources'])}")
    if result['failed_sources']:
        for fs in result['failed_sources']:
            print(f"  * {fs['source']}: {fs['error']}")
    print(f"- Saved CSV: {result['output_path']}")
    print("="*50)
