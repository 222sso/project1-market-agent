"""
Market Intelligence Pipeline Orchestrator
Author: NovaFactory AI Intelligence Team
"""

import os
import sys
import time
import logging
import datetime
from typing import Dict, Any

# Configure paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
PIPELINE_LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")
DATA_RAW_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "crawled_market_news.csv")
DATA_CLEANED_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "cleaned_market_news.csv")
DATA_RECOMMENDED_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "recommended_market_news.csv")
DOCS_INDEX_PATH = os.path.join(PROJECT_ROOT, "docs", "index.html")

os.makedirs(LOG_DIR, exist_ok=True)

# Set up logging for pipeline
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(PIPELINE_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Pipeline")

# Import modular pipeline components
try:
    from crawler import run_collection
    from cleaner import clean_dataset
    from recommender import run_recommendation
    from build_site import build_site
except ImportError as e:
    logger.critical(f"Failed to import core pipeline modules: {e}")
    sys.exit(1)


def execute_pipeline() -> Dict[str, Any]:
    """Execute end-to-end intelligence collection, cleaning, scoring, and dashboard build."""
    start_time = time.time()
    logger.info("=" * 65)
    logger.info("🚀 STARTING NOVAFACTORY AI MARKET INTELLIGENCE PIPELINE")
    logger.info("=" * 65)
    
    stages_status = {}
    summary = {
        "start_time": datetime.datetime.now().astimezone().isoformat(),
        "stages": stages_status,
        "success": False
    }

    # =========================================================================
    # STEP 1: Collection (crawler.py)
    # =========================================================================
    logger.info("\n>>> [STEP 1/4] EXECUTING DATA COLLECTION (crawler.py)...")
    try:
        crawl_res = run_collection()
        total_collected = crawl_res.get("total_count", 0)
        failed_sources = crawl_res.get("failed_sources", [])
        
        if total_collected >= 200:
            status = "SUCCESS" if len(failed_sources) == 0 else "WARNING"
            stages_status["1_crawler"] = {
                "status": status,
                "total_collected": total_collected,
                "live_crawled": crawl_res.get("live_count", 0),
                "fallback_used": crawl_res.get("fallback_count", 0),
                "failed_sources_count": len(failed_sources)
            }
            logger.info(f"[{status}] Collection completed with {total_collected} records (Live: {crawl_res.get('live_count')}, Fallback: {crawl_res.get('fallback_count')}).")
        else:
            stages_status["1_crawler"] = {
                "status": "WARNING",
                "message": f"Total records ({total_collected}) is below optimal 200.",
                "total_collected": total_collected
            }
            logger.warning(f"[WARNING] Crawling finished but returned only {total_collected} records.")
    except Exception as e:
        logger.error(f"[FAILED] Step 1 (Collection) encountered critical error: {e}", exc_info=True)
        stages_status["1_crawler"] = {"status": "FAILED", "error": str(e)}

    # =========================================================================
    # STEP 2: Cleaning & Normalization (cleaner.py)
    # =========================================================================
    logger.info("\n>>> [STEP 2/4] EXECUTING DATA CLEANING & DEDUPLICATION (cleaner.py)...")
    try:
        if not os.path.exists(DATA_RAW_PATH):
            raise FileNotFoundError(f"Raw data file missing: {DATA_RAW_PATH}")
            
        clean_res = clean_dataset()
        stages_status["2_cleaner"] = {
            "status": "SUCCESS",
            "original_count": clean_res.get("original_count", 0),
            "cleaned_count": clean_res.get("final_count", 0),
            "duplicates_removed": clean_res.get("total_duplicates_removed", 0),
            "invalid_removed": clean_res.get("invalid_title_removed", 0)
        }
        logger.info(f"[SUCCESS] Cleaning completed: {clean_res.get('final_count')} valid records preserved ({clean_res.get('total_duplicates_removed')} duplicates removed).")
    except Exception as e:
        logger.error(f"[FAILED] Step 2 (Cleaning) encountered critical error: {e}", exc_info=True)
        stages_status["2_cleaner"] = {"status": "FAILED", "error": str(e)}

    # =========================================================================
    # STEP 3: Tailored Recommendation Scoring (recommender.py)
    # =========================================================================
    logger.info("\n>>> [STEP 3/4] EXECUTING RELEVANCE SCORING & RECOMMENDATION (recommender.py)...")
    try:
        if not os.path.exists(DATA_CLEANED_PATH):
            raise FileNotFoundError(f"Cleaned data file missing: {DATA_CLEANED_PATH}")
            
        rec_res = run_recommendation()
        stages_status["3_recommender"] = {
            "status": "SUCCESS",
            "recommended_count": rec_res.get("total_recommended", 0),
            "avg_score": rec_res.get("avg_score", 0),
            "llm_used": rec_res.get("llm_used", False)
        }
        logger.info(f"[SUCCESS] Recommendation completed: TOP {rec_res.get('total_recommended')} selected (Avg Score: {rec_res.get('avg_score')}, LLM: {rec_res.get('llm_used')}).")
    except Exception as e:
        logger.error(f"[FAILED] Step 3 (Recommendation) encountered critical error: {e}", exc_info=True)
        stages_status["3_recommender"] = {"status": "FAILED", "error": str(e)}

    # =========================================================================
    # STEP 4: Static Site & Dashboard Build (build_site.py)
    # =========================================================================
    logger.info("\n>>> [STEP 4/4] EXECUTING GITHUB PAGES STATIC DASHBOARD BUILD (build_site.py)...")
    try:
        site_res = build_site()
        stages_status["4_build_site"] = {
            "status": "SUCCESS",
            "index_html_path": site_res.get("index_html_path"),
            "report_json_path": site_res.get("report_json_path"),
            "items_rendered": site_res.get("total_recommended", 0)
        }
        logger.info(f"[SUCCESS] Dashboard generated at {site_res.get('index_html_path')} and JSON at {site_res.get('report_json_path')}.")
    except Exception as e:
        logger.error(f"[FAILED] Step 4 (Build Site) encountered critical error: {e}", exc_info=True)
        stages_status["4_build_site"] = {"status": "FAILED", "error": str(e)}

    # =========================================================================
    # Overall Pipeline Verification & Summary
    # =========================================================================
    elapsed = round(time.time() - start_time, 2)
    summary["elapsed_seconds"] = elapsed
    summary["end_time"] = datetime.datetime.now().astimezone().isoformat()
    
    # Check if all 4 key artifacts exist
    artifacts_ready = (
        os.path.exists(DATA_RAW_PATH) and
        os.path.exists(DATA_CLEANED_PATH) and
        os.path.exists(DATA_RECOMMENDED_PATH) and
        os.path.exists(DOCS_INDEX_PATH)
    )
    summary["success"] = artifacts_ready

    logger.info("\n" + "=" * 65)
    logger.info(f"🏁 PIPELINE EXECUTION COMPLETED ({'SUCCESS' if artifacts_ready else 'PARTIAL/FAILED'}) in {elapsed}s")
    logger.info("=" * 65)
    for stage_name, stage_info in stages_status.items():
        st = stage_info.get("status", "UNKNOWN")
        logger.info(f" - {stage_name.upper():<16}: [{st}] {stage_info}")
    logger.info(f" - Raw CSV        : {'EXISTS' if os.path.exists(DATA_RAW_PATH) else 'MISSING'}")
    logger.info(f" - Cleaned CSV    : {'EXISTS' if os.path.exists(DATA_CLEANED_PATH) else 'MISSING'}")
    logger.info(f" - Recommended CSV: {'EXISTS' if os.path.exists(DATA_RECOMMENDED_PATH) else 'MISSING'}")
    logger.info(f" - Docs Index HTML: {'EXISTS' if os.path.exists(DOCS_INDEX_PATH) else 'MISSING'}")
    logger.info("=" * 65)

    return summary


if __name__ == "__main__":
    result = execute_pipeline()
    if not result["success"]:
        sys.exit(1)
