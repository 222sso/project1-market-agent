"""
Market Intelligence Recommender Engine
Author: NovaFactory AI Intelligence Team
"""

import os
import sys
import re
import json
import logging
import datetime
from typing import Dict, Any, List, Tuple
import yaml
import pandas as pd
import requests
from dotenv import load_dotenv

# Path configurations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "company_profile.yaml")
CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "cleaned_market_news.csv")
RECOMMENDED_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "recommended_market_news.csv")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "recommender.log")

load_dotenv(ENV_PATH)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(RECOMMENDED_DATA_PATH), exist_ok=True)

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


def load_company_profile(config_path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Load target company profile."""
    if not os.path.exists(config_path):
        return {
            "company_name": "NovaFactory AI",
            "business_area": "제조업 AI 비전 품질검사",
            "products": ["비전 기반 불량 탐지 SaaS", "제조 품질 리포트 자동화"],
            "target_market": ["중소·중견 제조기업", "스마트팩토리 구축 기업"],
            "competitors": ["VisionForge", "InspectAI", "FactoryMind", "QualiBot", "CogniSense"],
            "interest_keywords": ["AI", "머신비전", "스마트팩토리", "품질검사", "자동화", "제조 AX", "불량 탐지", "엣지 컴퓨팅"],
            "funding_keywords": ["창업지원", "AI 바우처", "스마트공장", "R&D", "사업화 자금", "TIPS"]
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_rule_based_score(row: pd.Series, profile: Dict[str, Any]) -> Tuple[int, str, List[str]]:
    """
    Calculate relevance score and generate rationale based on rule matching.
    Returns: (score, recommendation_reason, matched_tags)
    """
    title = str(row.get("title", ""))
    content = str(row.get("content", ""))
    summary = str(row.get("summary", ""))
    category = str(row.get("category", "")).lower()
    full_text = f"{title} {content} {summary}".lower()

    score = 40  # Base score for passing cleaning pipeline
    matched_tags = []
    reasons = []

    # 1. Company & Product match (+25)
    company_name = profile.get("company_name", "").lower()
    if company_name and company_name in full_text:
        score += 25
        matched_tags.append("자사직접연관")
        reasons.append("자사명 및 비즈니스 모델 직접 언급")

    for prod in profile.get("products", []):
        prod_clean = re.sub(r"[^\w\s]", "", prod).lower()
        for term in prod_clean.split():
            if len(term) >= 2 and term in full_text:
                score += 8
                matched_tags.append(term)
                break

    # 2. Competitor match (+20)
    for comp in profile.get("competitors", []):
        comp_lower = comp.lower()
        if comp_lower in full_text or comp_lower in title.lower():
            score += 20
            matched_tags.append(f"경쟁사:{comp}")
            reasons.append(f"주요 경쟁사 '{comp}' 동향 및 시장 진출 분석 필요")
            break
    if category == "competitor":
        score += 10
        if not any("경쟁사:" in t for t in matched_tags):
            matched_tags.append("경쟁시장동향")
            reasons.append("비전 인스펙션 및 머신비전 업계 경쟁 구도 파악")

    # 3. Interest Keywords match (+10 per keyword, max 30)
    kw_hits = 0
    for kw in profile.get("interest_keywords", []):
        kw_clean = kw.lower()
        if kw_clean in full_text:
            score += 10
            matched_tags.append(kw)
            kw_hits += 1
            if kw_hits >= 3:
                break
    if kw_hits > 0:
        reasons.append(f"핵심 기술 키워드({', '.join(matched_tags[-kw_hits:])}) 일치")

    # 4. Funding & Policy match (+15)
    funding_hits = 0
    for fkw in profile.get("funding_keywords", []):
        fkw_clean = fkw.lower()
        if fkw_clean in full_text:
            score += 12
            matched_tags.append(fkw)
            funding_hits += 1
            if funding_hits >= 2:
                break
    if category in ["funding", "policy"] or funding_hits > 0:
        score += 8
        reasons.append("제조 AI 정부 지원사업 및 R&D 바우처 수혜 기회")

    # 5. Recency boost (+5~10)
    date_str = str(row.get("date", ""))
    try:
        pub_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        days_ago = (datetime.date.today() - pub_dt).days
        if days_ago <= 3:
            score += 10
        elif days_ago <= 7:
            score += 5
    except Exception:
        pass

    # Cap score between 45 and 99
    final_score = min(99, max(45, score))

    # Formulate recommendation reason
    if not reasons:
        reasons.append(f"제조업 및 AI 비전 품질검사 관련 산업 동향 참고 자료")
    
    cat_label = {
        "market": "시장 전략",
        "technology": "기술 개발",
        "competitor": "경쟁 대응",
        "funding": "지원사업 유치",
        "policy": "정책 부합"
    }.get(category, "인텔리전스")
    
    unique_tags = list(dict.fromkeys(matched_tags))
    rec_reason = f"[{cat_label}] " + " / ".join(reasons) + f" (태그: {', '.join(unique_tags[:4]) if unique_tags else '산업동향'})"

    return final_score, rec_reason, unique_tags


def call_gemini_relevance(top_articles: List[Dict[str, Any]], profile: Dict[str, Any], api_key: str) -> List[Dict[str, Any]]:
    """
    Call Gemini API to generate deep tailored executive insights and refine scores.
    Uses Google Gemini REST API.
    """
    logger.info("Evaluating top candidates with Gemini AI...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_prompt = []
    for i, a in enumerate(top_articles[:15]):
        articles_prompt.append(f"[{i+1}] ID: {a['article_id']}, Title: {a['title']}, Category: {a['category']}, Date: {a['date']}, Summary: {a.get('summary', '')[:120]}")

    prompt_text = f"""당신은 AI 기업 '{profile.get('company_name', 'NovaFactory AI')}'의 수석 전략 컨설턴트입니다.
회사 정보:
- 사업 영역: {profile.get('business_area')}
- 주요 제품: {', '.join(profile.get('products', []))}
- 목표 시장: {', '.join(profile.get('target_market', []))}
- 경쟁사: {', '.join(profile.get('competitors', []))}

다음 수집된 상위 뉴스 기사 목록을 분석하여 각 기사별로 회사의 사업 관점에서의 추천 이유(1~2문장)와 조정 점수(60~99)를 JSON 형식으로 응답하세요.

기사 목록:
{chr(10).join(articles_prompt)}

반드시 다음 JSON 형식 배열로만 응답하세요 (코드블록 없이 순수 JSON):
[
  {{"id": "CL-0001", "llm_score": 95, "llm_reason": "[경쟁대응] 경쟁사 X의 비전 검사 신제품 출시에 대응하여 자사 SaaS형 불량 검출 모델의 가격 경쟁력 및 현장 연동성을 강조하는 마케팅 전략이 필요합니다."}}
]
"""
    body = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=20)
        if resp.status_code == 200:
            result = resp.json()
            cand_text = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed_json = json.loads(cand_text)
            lookup = {item["id"]: item for item in parsed_json if "id" in item}
            
            for art in top_articles:
                art_id = art["article_id"]
                if art_id in lookup:
                    info = lookup[art_id]
                    if "llm_score" in info and isinstance(info["llm_score"], (int, float)):
                        art["relevance_score"] = int(info["llm_score"])
                    if "llm_reason" in info and info["llm_reason"]:
                        art["recommendation_reason"] = str(info["llm_reason"])
            logger.info("Successfully enhanced recommendations with Gemini AI.")
        else:
            logger.warning(f"Gemini API returned status {resp.status_code}. Fallback to rule-based.")
    except Exception as e:
        logger.warning(f"Gemini API call failed ({e}). Proceeding with rule-based recommendations.")
    
    return top_articles


def run_recommendation(
    input_csv: str = CLEANED_DATA_PATH,
    output_csv: str = RECOMMENDED_DATA_PATH,
    top_k: int = 30
) -> Dict[str, Any]:
    """Run recommendation engine on cleaned dataset."""
    logger.info(f"Loading cleaned dataset from {input_csv}...")
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Cleaned dataset not found: {input_csv}")
    
    df = pd.read_csv(input_csv)
    profile = load_company_profile(CONFIG_PATH)
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    enable_llm = os.getenv("ENABLE_LLM_RELEVANCE", "false").lower() == "true" or bool(api_key)
    has_gemini = bool(api_key and enable_llm)
    
    # 1. Rule-based scoring
    scores = []
    reasons = []
    tags_list = []
    
    for _, row in df.iterrows():
        sc, r_reason, tags = calculate_rule_based_score(row, profile)
        scores.append(sc)
        reasons.append(r_reason)
        tags_list.append("|".join(tags))
        
    df["relevance_score"] = scores
    df["recommendation_reason"] = reasons
    df["matched_tags"] = tags_list
    
    # Sort by relevance_score descending, then date descending
    df = df.sort_values(by=["relevance_score", "date"], ascending=[False, False]).reset_index(drop=True)
    
    # 2. Select TOP 30
    top_df = df.head(top_k).copy()
    
    # 3. Apply Gemini LLM if API key exists
    llm_used = False
    if has_gemini:
        top_records = top_df.to_dict(orient="records")
        enhanced_records = call_gemini_relevance(top_records, profile, api_key)
        top_df = pd.DataFrame(enhanced_records)
        # Re-sort top_df after LLM scoring
        top_df = top_df.sort_values(by=["relevance_score", "date"], ascending=[False, False]).reset_index(drop=True)
        llm_used = True
    else:
        logger.info("No active Gemini API key found or ENABLE_LLM_RELEVANCE is false. Using rule-based engine.")

    # Assign recommendation rank
    top_df["rank"] = range(1, len(top_df) + 1)
    
    # Save recommended TOP 30 to CSV
    top_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Saved TOP {len(top_df)} recommendations to {output_csv}.")
    
    return {
        "total_recommended": len(top_df),
        "llm_used": llm_used,
        "output_path": output_csv,
        "top_10": top_df.head(10)[["rank", "article_id", "category", "title", "relevance_score", "date", "source_name", "source_url", "recommendation_reason"]].to_dict(orient="records"),
        "category_counts": top_df["category"].value_counts().to_dict(),
        "avg_score": round(float(top_df["relevance_score"].mean()), 2)
    }


if __name__ == "__main__":
    result = run_recommendation()
    print("\n" + "="*50)
    print(" RECOMMENDER EXECUTION SUMMARY")
    print("="*50)
    print(f"- Total Recommended Items: {result['total_recommended']}")
    print(f"- LLM Enhancement Used: {result['llm_used']}")
    print(f"- Average Relevance Score: {result['avg_score']}")
    print(f"- Category Breakdown (TOP 30): {result['category_counts']}")
    print(f"- Output CSV: {result['output_path']}")
    print("\n--- TOP 10 RECOMMENDATIONS ---")
    for item in result['top_10']:
        print(f"[{item['rank']:02d}] (Score: {item['relevance_score']}) [{item['category']}] {item['title'][:60]}...")
        print(f"     Reason: {item['recommendation_reason'][:80]}...")
    print("="*50)
