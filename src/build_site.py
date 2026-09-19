"""
Static Site Builder for GitHub Pages
Author: NovaFactory AI Intelligence Team
"""

import os
import sys
import json
import logging
import datetime
from typing import Dict, Any
import yaml
import pandas as pd

# Path configurations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "company_profile.yaml")
CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "cleaned_market_news.csv")
RECOMMENDED_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "recommended_market_news.csv")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
REPORT_JSON_PATH = os.path.join(DOCS_DIR, "report.json")
INDEX_HTML_PATH = os.path.join(DOCS_DIR, "index.html")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "build_site.log")

os.makedirs(DOCS_DIR, exist_ok=True)
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


def generate_report_json(profile: Dict[str, Any], cleaned_df: pd.DataFrame, rec_df: pd.DataFrame) -> Dict[str, Any]:
    """Compile structured report JSON for dashboard and API use."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cat_counts_all = cleaned_df["category"].value_counts().to_dict()
    cat_counts_rec = rec_df["category"].value_counts().to_dict()
    
    top_10 = rec_df.head(10).to_dict(orient="records")
    top_30 = rec_df.to_dict(orient="records")

    report_data = {
        "metadata": {
            "title": "NovaFactory AI 시장·경쟁사 인텔리전스 데일리 리포트",
            "generated_at": now_str,
            "target_company": profile.get("company_name", "NovaFactory AI"),
            "business_area": profile.get("business_area", "제조업 AI 비전 품질검사"),
            "total_collected": len(cleaned_df),
            "total_recommended": len(rec_df),
            "avg_relevance_score": round(float(rec_df["relevance_score"].mean()), 1) if not rec_df.empty else 0
        },
        "company_profile": profile,
        "category_stats": {
            "total_cleaned_distribution": cat_counts_all,
            "recommended_distribution": cat_counts_rec
        },
        "top_10": top_10,
        "recommendations": top_30
    }
    
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved report JSON to {REPORT_JSON_PATH}.")
    return report_data


def generate_index_html(report_data: Dict[str, Any]) -> None:
    """Generate modern, responsive, interactive static HTML dashboard."""
    meta = report_data["metadata"]
    profile = report_data["company_profile"]
    top_10 = report_data["top_10"]
    recommendations = report_data["recommendations"]
    cat_stats = report_data["category_stats"]["recommended_distribution"]

    # Category badge colors
    cat_colors = {
        "market": "bg-blue-100 text-blue-800 border-blue-200",
        "technology": "bg-purple-100 text-purple-800 border-purple-200",
        "competitor": "bg-rose-100 text-rose-800 border-rose-200",
        "funding": "bg-emerald-100 text-emerald-800 border-emerald-200",
        "policy": "bg-amber-100 text-amber-800 border-amber-200"
    }

    # Generate Top 10 Cards HTML
    top_10_html = ""
    for item in top_10:
        cat = item.get("category", "market")
        badge_style = cat_colors.get(cat, "bg-gray-100 text-gray-800")
        score = item.get("relevance_score", 0)
        score_color = "text-emerald-600 bg-emerald-50 border-emerald-200" if score >= 85 else "text-blue-600 bg-blue-50 border-blue-200"
        
        top_10_html += f"""
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-3">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border {badge_style}">
                {cat.upper()}
              </span>
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-400 font-mono">{item.get('date', '')}</span>
                <span class="px-2 py-0.5 rounded text-xs font-bold border {score_color}">
                  ★ {score}점
                </span>
              </div>
            </div>
            <h3 class="font-bold text-slate-800 text-base line-clamp-2 hover:text-indigo-600 transition-colors mb-2">
              <a href="{item.get('source_url', '#')}" target="_blank" rel="noopener noreferrer" class="hover:underline">
                <span class="text-indigo-600 font-extrabold mr-1">#{item.get('rank', 1)}</span> {item.get('title', '')}
              </a>
            </h3>
            <div class="bg-slate-50 rounded-lg p-3 border border-slate-100 text-xs text-slate-700 leading-relaxed mb-3">
              <strong class="text-indigo-700 block mb-1">💡 추천 및 비즈니스 인사이트</strong>
              {item.get('recommendation_reason', '산업 동향 모니터링 필요')}
            </div>
          </div>
          <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
            <span>출처: <strong class="text-slate-700">{item.get('source_name', 'Google News')}</strong></span>
            <a href="{item.get('source_url', '#')}" target="_blank" rel="noopener noreferrer" class="text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center gap-1">
              원문 보기 →
            </a>
          </div>
        </div>
        """

    # Generate Full Table Rows HTML
    table_rows_html = ""
    for item in recommendations:
        cat = item.get("category", "market")
        badge_style = cat_colors.get(cat, "bg-gray-100 text-gray-800")
        score = item.get("relevance_score", 0)
        
        table_rows_html += f"""
        <tr class="hover:bg-slate-50 transition-colors news-row" data-category="{cat}">
          <td class="px-4 py-3 text-center font-mono font-bold text-indigo-600 text-xs">{item.get('rank', '-')}</td>
          <td class="px-4 py-3">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border {badge_style}">
              {cat}
            </span>
          </td>
          <td class="px-4 py-3">
            <a href="{item.get('source_url', '#')}" target="_blank" rel="noopener noreferrer" class="font-medium text-slate-900 hover:text-indigo-600 hover:underline block text-sm">
              {item.get('title', '')}
            </a>
            <p class="text-xs text-slate-500 mt-1 line-clamp-1">{item.get('recommendation_reason', '')}</p>
          </td>
          <td class="px-4 py-3 text-center">
            <span class="font-bold text-xs text-indigo-700 bg-indigo-50 px-2 py-1 rounded-md">{score}</span>
          </td>
          <td class="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{item.get('source_name', '')}</td>
          <td class="px-4 py-3 text-xs text-slate-400 whitespace-nowrap font-mono">{item.get('date', '')}</td>
          <td class="px-4 py-3 text-center whitespace-nowrap">
            <a href="{item.get('source_url', '#')}" target="_blank" rel="noopener noreferrer" class="text-xs bg-white hover:bg-indigo-50 text-indigo-600 font-semibold px-2.5 py-1 rounded border border-indigo-200 transition-colors inline-block">
              열기 ↗
            </a>
          </td>
        </tr>
        """

    competitors_badges = "".join([f'<span class="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded text-xs">{c}</span>' for c in profile.get("competitors", [])])
    keywords_badges = "".join([f'<span class="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded text-xs">{k}</span>' for k in profile.get("interest_keywords", [])])
    funding_badges = "".join([f'<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded text-xs">{f}</span>' for f in profile.get("funding_keywords", [])])

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{meta['title']}</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    body {{ font-family: 'Pretendard', sans-serif; }}
  </style>
</head>
<body class="bg-slate-100 text-slate-800 min-h-screen flex flex-col">

  <!-- Header Navigation -->
  <header class="bg-indigo-900 text-white shadow-lg sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="bg-indigo-600 p-2.5 rounded-xl shadow-inner font-bold text-xl tracking-wider">
          🤖 NF
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-extrabold tracking-tight">{profile.get('company_name', 'NovaFactory AI')} 인텔리전스 대시보드</h1>
            <span class="bg-indigo-700 text-indigo-200 text-xs px-2 py-0.5 rounded font-mono">v1.0.0</span>
          </div>
          <p class="text-xs text-indigo-200 mt-0.5">제조업 AI 비전 품질검사 실시간 시장·경쟁사·정책 수집 시스템</p>
        </div>
      </div>
      <div class="flex items-center gap-3 text-xs bg-indigo-800/80 px-3 py-2 rounded-lg border border-indigo-700">
        <span class="text-indigo-300">업데이트:</span>
        <span class="font-mono font-medium text-white">{meta['generated_at']}</span>
        <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse ml-1"></span>
      </div>
    </div>
  </header>

  <!-- Main Content Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-8">

    <!-- Company Profile Summary Card -->
    <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
      <div class="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="text-lg">🏢</span>
          <h2 class="text-base font-bold text-slate-800">모니터링 대상 기업 프로필 (<span class="text-indigo-600">{profile.get('company_name')}</span>)</h2>
        </div>
        <span class="text-xs text-slate-400">설정 파일: <code>config/company_profile.yaml</code></span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
          <span class="font-bold text-slate-600 block mb-1">🎯 핵심 제품 & 사업 영역</span>
          <p class="text-slate-800 font-medium">{profile.get('business_area')}</p>
          <p class="text-slate-500 text-xs mt-1">SaaS 불량 탐지, 제조 품질 리포트 자동화, 엣지 AI</p>
        </div>
        <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
          <span class="font-bold text-slate-600 block mb-1.5">⚔️ 모니터링 경쟁사 (5개)</span>
          <div class="flex flex-wrap gap-1">
            {competitors_badges}
          </div>
        </div>
        <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
          <span class="font-bold text-slate-600 block mb-1.5">🔍 핵심 수집 키워드</span>
          <div class="flex flex-wrap gap-1">
            {keywords_badges}
            {funding_badges}
          </div>
        </div>
      </div>
    </div>

    <!-- Executive Metrics Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
        <div class="flex items-center justify-between text-slate-500 text-xs font-semibold">
          <span>전체 수집 기사</span>
          <span class="text-blue-500 text-base">📊</span>
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-slate-900">{meta['total_collected']}</span>
          <span class="text-xs text-slate-400">건</span>
        </div>
        <p class="text-xs text-emerald-600 font-medium mt-1">100% 실시간 공개 수집</p>
      </div>

      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
        <div class="flex items-center justify-between text-slate-500 text-xs font-semibold">
          <span>선별 추천 기사</span>
          <span class="text-indigo-500 text-base">🎯</span>
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-indigo-600">{meta['total_recommended']}</span>
          <span class="text-xs text-slate-400">건 (TOP 30)</span>
        </div>
        <p class="text-xs text-indigo-500 font-medium mt-1">정밀 관련성 평가 완료</p>
      </div>

      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
        <div class="flex items-center justify-between text-slate-500 text-xs font-semibold">
          <span>평균 관련도 점수</span>
          <span class="text-amber-500 text-base">★</span>
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-amber-600">{meta['avg_relevance_score']}</span>
          <span class="text-xs text-slate-400">/ 100점</span>
        </div>
        <p class="text-xs text-amber-600 font-medium mt-1">고관련도 우선 추천</p>
      </div>

      <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
        <div class="flex items-center justify-between text-slate-500 text-xs font-semibold">
          <span>수집 카테고리</span>
          <span class="text-purple-500 text-base">🏷️</span>
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-purple-600">{len(cat_stats)}</span>
          <span class="text-xs text-slate-400">개 영역</span>
        </div>
        <p class="text-xs text-purple-600 font-medium mt-1">시장/경쟁/기술/정책/지원</p>
      </div>
    </div>

    <!-- Visualization Section -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 lg:col-span-1">
        <h3 class="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
          <span>📈</span> 추천 기사 카테고리 분포
        </h3>
        <div class="relative h-64">
          <canvas id="categoryChart"></canvas>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 lg:col-span-2">
        <h3 class="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
          <span>📊</span> 상위 10개 기사 관련성 점수 순위
        </h3>
        <div class="relative h-64">
          <canvas id="scoreChart"></canvas>
        </div>
      </div>
    </div>

    <!-- TOP 10 Executive Highlights Grid -->
    <div>
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <span class="text-xl">🏆</span>
          <h2 class="text-lg font-extrabold text-slate-900">오늘의 핵심 추천 TOP 10</h2>
          <span class="bg-indigo-100 text-indigo-700 font-bold text-xs px-2.5 py-0.5 rounded-full">Executive Pick</span>
        </div>
        <span class="text-xs text-slate-500">NovaFactory AI 비즈니스 맞춤형 인사이트</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {top_10_html}
      </div>
    </div>

    <!-- Complete Recommended TOP 30 Filterable Table -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div class="p-6 border-b border-slate-200 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <span>📋</span> 전체 추천 기사 목록 (TOP 30)
          </h2>
          <p class="text-xs text-slate-500 mt-1">카테고리별 필터 및 키워드 검색을 통해 세부 기사를 탐색할 수 있습니다.</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs font-medium">
            <button class="filter-btn px-3 py-1.5 rounded-md bg-white text-indigo-700 shadow-sm" data-filter="all">전체</button>
            <button class="filter-btn px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900" data-filter="market">시장동향</button>
            <button class="filter-btn px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900" data-filter="technology">기술개발</button>
            <button class="filter-btn px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900" data-filter="competitor">경쟁사</button>
            <button class="filter-btn px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900" data-filter="funding">지원사업</button>
            <button class="filter-btn px-3 py-1.5 rounded-md text-slate-600 hover:text-slate-900" data-filter="policy">정책</button>
          </div>
          <input type="text" id="searchInput" placeholder="제목/내용 검색..." class="text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-44">
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
              <th class="px-4 py-3 text-center w-12">순위</th>
              <th class="px-4 py-3 w-24">분류</th>
              <th class="px-4 py-3">기사 제목 및 추천 비즈니스 인사이트</th>
              <th class="px-4 py-3 text-center w-20">관련도</th>
              <th class="px-4 py-3 w-28">출처</th>
              <th class="px-4 py-3 w-24">날짜</th>
              <th class="px-4 py-3 text-center w-20">링크</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-sm" id="newsTableBody">
            {table_rows_html}
          </tbody>
        </table>
      </div>
    </div>

  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-slate-200 py-6 mt-12 text-center text-xs text-slate-500">
    <div class="max-w-7xl mx-auto px-4">
      <p>NovaFactory AI Market Intelligence Automation Agent • Built with Python & Antigravity</p>
      <p class="mt-1 text-slate-400">데이터 소스: Google News RSS, GeekNews, ArXiv • 배포: GitHub Pages</p>
    </div>
  </footer>

  <!-- Scripts for Charts and Interactivity -->
  <script>
    // Category Chart
    const catLabels = {json.dumps(list(cat_stats.keys()))};
    const catData = {json.dumps(list(cat_stats.values()))};
    
    new Chart(document.getElementById('categoryChart'), {{
      type: 'doughnut',
      data: {{
        labels: catLabels.map(c => c.toUpperCase()),
        datasets: [{{
          data: catData,
          backgroundColor: ['#6366f1', '#a855f7', '#f43f5e', '#10b981', '#f59e0b'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }}
        }}
      }}
    }});

    // Score Bar Chart
    const top10Titles = {json.dumps([f"#{item['rank']} {item['title'][:18]}..." for item in top_10])};
    const top10Scores = {json.dumps([item['relevance_score'] for item in top_10])};

    new Chart(document.getElementById('scoreChart'), {{
      type: 'bar',
      data: {{
        labels: top10Titles,
        datasets: [{{
          label: '관련성 점수 (100점 만점)',
          data: top10Scores,
          backgroundColor: '#4f46e5',
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          y: {{ min: 50, max: 100, grid: {{ color: '#f1f5f9' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }}
        }},
        plugins: {{
          legend: {{ display: false }}
        }}
      }}
    }});

    // Filtering logic
    const filterBtns = document.querySelectorAll('.filter-btn');
    const rows = document.querySelectorAll('.news-row');
    const searchInput = document.getElementById('searchInput');

    function applyFilters() {{
      const activeBtn = document.querySelector('.filter-btn.bg-white');
      const catFilter = activeBtn ? activeBtn.getAttribute('data-filter') : 'all';
      const query = searchInput.value.toLowerCase().trim();

      rows.forEach(row => {{
        const rowCat = row.getAttribute('data-category');
        const text = row.innerText.toLowerCase();
        const matchesCat = (catFilter === 'all' || rowCat === catFilter);
        const matchesSearch = (!query || text.includes(query));
        row.style.display = (matchesCat && matchesSearch) ? '' : 'none';
      }});
    }}

    filterBtns.forEach(btn => {{
      btn.addEventListener('click', () => {{
        filterBtns.forEach(b => {{
          b.classList.remove('bg-white', 'text-indigo-700', 'shadow-sm');
          b.classList.add('text-slate-600');
        }});
        btn.classList.add('bg-white', 'text-indigo-700', 'shadow-sm');
        btn.classList.remove('text-slate-600');
        applyFilters();
      }});
    }});

    searchInput.addEventListener('input', applyFilters);
  </script>
</body>
</html>
"""
    with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"Generated index.html at {INDEX_HTML_PATH} ({len(html_content)} bytes).")


def build_site() -> Dict[str, Any]:
    """Execute complete build pipeline for static documentation."""
    logger.info("Building static dashboard for GitHub Pages...")
    
    if not os.path.exists(CLEANED_DATA_PATH):
        raise FileNotFoundError(f"Cleaned data missing at {CLEANED_DATA_PATH}")
    if not os.path.exists(RECOMMENDED_DATA_PATH):
        raise FileNotFoundError(f"Recommended data missing at {RECOMMENDED_DATA_PATH}")

    profile = yaml.safe_load(open(CONFIG_PATH, "r", encoding="utf-8"))
    cleaned_df = pd.read_csv(CLEANED_DATA_PATH)
    rec_df = pd.read_csv(RECOMMENDED_DATA_PATH)

    report_data = generate_report_json(profile, cleaned_df, rec_df)
    generate_index_html(report_data)

    return {
        "report_json_path": REPORT_JSON_PATH,
        "index_html_path": INDEX_HTML_PATH,
        "total_recommended": len(rec_df),
        "top_10": report_data["top_10"]
    }


if __name__ == "__main__":
    res = build_site()
    print("\n" + "="*50)
    print(" BUILD SITE EXECUTION SUMMARY")
    print("="*50)
    print(f"- Report JSON: {res['report_json_path']}")
    print(f"- Dashboard HTML: {res['index_html_path']}")
    print(f"- Total Recommended Items: {res['total_recommended']}")
    print("="*50)
