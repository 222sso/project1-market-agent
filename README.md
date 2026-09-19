# 🚀 Project 1: Market Intelligence Agent (`project1-market-agent`)

> **NovaFactory AI** 맞춤형 시장 분석, 경쟁사 모니터링 및 정부 지원사업 기회 탐색 자동화 AI 에이전트

---

## 📌 1. 프로젝트 개요
본 프로젝트는 **NovaFactory AI(제조업 AI 비전 품질검사 SaaS 전문 기업)**를 위한 인텔리전스 수집 에이전트입니다.
공개 웹 및 RSS 피드를 통해 시장 트렌드, 경쟁사 동향, 정부 지원사업 소식을 자동 수집하고, 네트워크 장애나 수집량 부족 시 검증된 합성 데이터셋(`data/fallback/fallback_market_news.csv`)을 활용하여 분석 리포트를 생성한 뒤 GitHub Pages로 자동 배포합니다.

---

## 📁 2. 프로젝트 디렉터리 구조
```text
project1-market-agent/
├── .github/
│   └── workflows/              # GitHub Actions 자동화 및 GitHub Pages 배포 워크플로
├── config/
│   └── company_profile.yaml    # 기업 정보, 제품, 경쟁사 및 검색 키워드 설정
├── data/
│   └── fallback/
│       └── fallback_market_news.csv  # 비상용 합성 뉴스 데이터셋 (800행)
├── docs/                       # 산출물 및 GitHub Pages 정적 웹 페이지
├── logs/                       # 에이전트 실행 및 수집 로그
├── src/                        # 에이전트 소스 코드 (수집기, 필터링, 요약 등)
├── .env.example                # 환경 변수 템플릿
├── .gitignore                  # Git 추적 제외 규칙
├── requirements.txt            # 의존성 패키지 목록
└── README.md                   # 프로젝트 문서
```

---

## 🏢 3. 타깃 기업 프로필 (`config/company_profile.yaml`)
* **기업명**: NovaFactory AI
* **주요 사업 영역**: 제조업 AI 비전 품질검사
* **주요 제품/서비스**:
  - 비전 기반 불량 탐지 SaaS
  - 제조 품질 리포트 자동화
  - 엣지 비전 AI 불량 검출 디바이스
* **타깃 시장**: 중소·중견 제조기업, 스마트팩토리 구축 기업, 2차전지/자동차 부품 협력사
* **모니터링 대상 경쟁사 (5개)**: `VisionForge`, `InspectAI`, `FactoryMind`, `QualiBot`, `CogniSense`
* **주요 관심 키워드 (8개)**: `AI`, `머신비전`, `스마트팩토리`, `품질검사`, `자동화`, `제조 AX`, `불량 탐지`, `엣지 컴퓨팅`
* **지원사업 키워드 (6개)**: `창업지원`, `AI 바우처`, `스마트공장`, `R&D`, `사업화 자금`, `딥테크 팁스(TIPS)`

---

## 🛠️ 4. 설치 및 실행 가이드
1. **가상환경 구성 및 패키지 설치**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows PowerShell
   pip install -r requirements.txt
   ```
2. **환경 변수 설정**
   ```bash
   cp .env.example .env
   # .env 파일에 필요한 GEMINI_API_KEY 등을 입력합니다.
   ```
