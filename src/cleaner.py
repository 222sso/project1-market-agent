"""
Market Intelligence Data Cleaner
Author: NovaFactory AI Intelligence Team
"""

import os
import sys
import re
import html
import logging
import datetime
from typing import Dict, Any, Tuple
import pandas as pd
from dateutil import parser as date_parser

# Path configurations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "crawled_market_news.csv")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
CLEANED_DATA_PATH = os.path.join(PROCESSED_DIR, "cleaned_market_news.csv")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "cleaner.log")

os.makedirs(PROCESSED_DIR, exist_ok=True)
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


def strip_html_tags(text: Any) -> str:
    """Remove HTML tags and unescape HTML entities."""
    if pd.isna(text):
        return ""
    text_str = str(text)
    # Unescape HTML entities first (e.g., &nbsp;, &amp;)
    text_str = html.unescape(text_str)
    # Remove HTML tags
    clean_re = re.compile(r"<[^>]+>")
    text_str = clean_re.sub(" ", text_str)
    # Normalize multiple whitespace
    text_str = re.sub(r"\s+", " ", text_str).strip()
    return text_str


def normalize_title(title: Any) -> str:
    """Clean and normalize title string."""
    cleaned = strip_html_tags(title)
    # Strip trailing publisher tag if present e.g. "제목 - 언론사"
    # But preserve title itself
    return cleaned


def normalize_date(date_val: Any) -> str:
    """Normalize various date formats into YYYY-MM-DD."""
    if pd.isna(date_val) or not str(date_val).strip():
        return datetime.date.today().strftime("%Y-%m-%d")
    
    date_str = str(date_val).strip()
    try:
        # Check standard YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str
        dt = date_parser.parse(date_str)
        # Cap future dates if necessary
        today = datetime.datetime.now()
        if dt > today + datetime.timedelta(days=365):
            return today.strftime("%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # Fallback to today
        return datetime.date.today().strftime("%Y-%m-%d")


def normalize_url(url: Any) -> str:
    """Normalize URL by stripping trailing whitespace and unnecessary fragments."""
    if pd.isna(url):
        return ""
    url_str = str(url).strip()
    return url_str


def clean_dataset(input_csv: str = RAW_DATA_PATH, output_csv: str = CLEANED_DATA_PATH) -> Dict[str, Any]:
    """Execute complete data cleaning and deduplication pipeline."""
    logger.info(f"Starting data cleaning process on {input_csv}...")
    
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Raw data file not found: {input_csv}")
    
    df_raw = pd.read_csv(input_csv)
    original_count = len(df_raw)
    logger.info(f"Loaded raw dataset with {original_count} records.")
    
    # 1. Clean Text Fields (HTML tags & whitespace)
    logger.info("Cleaning HTML tags and normalizing text fields...")
    df_clean = df_raw.copy()
    
    df_clean["title"] = df_clean["title"].apply(normalize_title)
    df_clean["content"] = df_clean["content"].apply(strip_html_tags)
    df_clean["summary"] = df_clean["summary"].apply(strip_html_tags)
    df_clean["source_url"] = df_clean["source_url"].apply(normalize_url)
    df_clean["source_name"] = df_clean["source_name"].apply(lambda x: strip_html_tags(x) if pd.notna(x) else "Unknown")
    df_clean["date"] = df_clean["date"].apply(normalize_date)
    
    # Fill content from title if content became empty
    df_clean["content"] = df_clean.apply(
        lambda row: row["title"] if not str(row["content"]).strip() else row["content"],
        axis=1
    )
    df_clean["summary"] = df_clean.apply(
        lambda row: row["title"] if not str(row["summary"]).strip() else row["summary"],
        axis=1
    )

    # 2. Filter out Invalid / Missing / Overly Short Titles (< 5 chars)
    logger.info("Filtering out empty, null, or excessively short titles...")
    valid_title_mask = df_clean["title"].apply(lambda t: len(str(t).strip()) >= 5)
    invalid_title_count = int((~valid_title_mask).sum())
    df_clean = df_clean[valid_title_mask].copy()
    logger.info(f"Removed {invalid_title_count} records with invalid/too short titles.")

    # 3. Deduplication (URL duplicate & Title duplicate)
    logger.info("Deduplicating by source_url and normalized title...")
    
    # URL Deduplication
    before_url_dedup = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset=["source_url"], keep="first")
    url_dup_removed = before_url_dedup - len(df_clean)
    logger.info(f"Removed {url_dup_removed} records with duplicate URLs.")
    
    # Title Deduplication (Normalize for case and whitespace)
    before_title_dedup = len(df_clean)
    df_clean["_title_norm"] = df_clean["title"].apply(lambda x: re.sub(r"\s+", "", str(x).lower()))
    df_clean = df_clean.drop_duplicates(subset=["_title_norm"], keep="first")
    df_clean = df_clean.drop(columns=["_title_norm"])
    title_dup_removed = before_title_dedup - len(df_clean)
    logger.info(f"Removed {title_dup_removed} records with duplicate titles.")
    
    total_duplicates_removed = url_dup_removed + title_dup_removed

    # 4. Re-assign unique Cleaned article_ids (CL-0001, CL-0002...)
    df_clean = df_clean.reset_index(drop=True)
    df_clean["article_id"] = [f"CL-{i+1:04d}" for i in range(len(df_clean))]
    
    # Update has_null column
    df_clean["has_null"] = df_clean.apply(
        lambda r: (pd.isna(r["title"]) or pd.isna(r["source_url"]) or pd.isna(r["date"])),
        axis=1
    )
    df_clean["is_duplicate_seed"] = False

    # 5. Schema Ordering and Quality Check
    schema_cols = [
        "article_id", "category", "title", "date", "content", "summary",
        "source_url", "source_name", "company_tag", "keywords",
        "collected_at", "has_null", "is_duplicate_seed", "data_origin"
    ]
    for col in schema_cols:
        if col not in df_clean.columns:
            df_clean[col] = None
    df_clean = df_clean[schema_cols]

    final_count = len(df_clean)
    
    # Save output
    df_clean.to_csv(output_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Saved cleaned dataset ({final_count} records) to {output_csv}.")

    return {
        "original_count": original_count,
        "final_count": final_count,
        "invalid_title_removed": invalid_title_count,
        "url_duplicates_removed": url_dup_removed,
        "title_duplicates_removed": title_dup_removed,
        "total_duplicates_removed": total_duplicates_removed,
        "output_path": output_csv,
        "category_counts": df_clean["category"].value_counts().to_dict(),
        "data_origin_counts": df_clean["data_origin"].value_counts().to_dict()
    }


if __name__ == "__main__":
    stats = clean_dataset()
    print("\n" + "="*50)
    print(" DATA CLEANING EXECUTION SUMMARY")
    print("="*50)
    print(f"- Original Row Count: {stats['original_count']}")
    print(f"- Final Cleaned Row Count: {stats['final_count']}")
    print(f"- Invalid / Short Titles Removed: {stats['invalid_title_removed']}")
    print(f"- Total Duplicates Removed: {stats['total_duplicates_removed']}")
    print(f"  * URL Duplicates: {stats['url_duplicates_removed']}")
    print(f"  * Title Duplicates: {stats['title_duplicates_removed']}")
    print(f"- Category Breakdown: {stats['category_counts']}")
    print(f"- Data Origin Breakdown: {stats['data_origin_counts']}")
    print(f"- Saved Cleaned File: {stats['output_path']}")
    print("="*50)
