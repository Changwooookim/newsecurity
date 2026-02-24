# newsecurity 🛡️

국내외 주요 보안 공지 및 위협 인텔리전스를 수집하여 하나의 대시보드에서 확인하는 웹 앱입니다.

## 빠른 시작

### 1. 의존성 설치

```powershell
pip install -r requirements.txt
```

### 2. 서버 실행

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 `http://localhost:8000` 접속

> 서버 시작 시 자동으로 첫 번째 피드 수집이 시작됩니다. 이후 **1시간마다** 자동 갱신됩니다.

---

## 외부 접근 허용 (선택)

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 뉴스 소스 추가/변경

`sources.yaml` 파일을 편집합니다.

### RSS 소스 추가

```yaml
sources:
  - name: "소스 이름"
    tag: "KR"       # KR 또는 EN
    type: rss
    url: "https://example.com/rss"
```

### RSS가 없는 사이트 (크롤러 방식, 추후 지원)

```yaml
  - name: "소스 이름"
    tag: "KR"
    type: scraper
    url: "https://example.com/news"
    scraper_module: "scrapers.example_scraper"
```

크롤러 모듈은 `scrapers/` 디렉토리에 추가하면 됩니다.

---

## API 엔드포인트

| Method | URL | 설명 |
|--------|-----|------|
| `GET`  | `/api/news?limit=100&offset=0` | 뉴스 목록 (최대 500) |
| `GET`  | `/api/sources` | 설정된 소스 목록 |
| `POST` | `/api/refresh` | 즉시 피드 갱신 |

---

## 프로젝트 구조

```
newsecurity/
├── main.py          # FastAPI 앱
├── feed_parser.py   # RSS 파서
├── database.py      # SQLite DB
├── scheduler.py     # 1시간 주기 스케줄러
├── sources.yaml     # 뉴스 소스 설정
├── requirements.txt
├── news.db          # 자동 생성됨 (수집된 뉴스 보관)
└── static/
    └── index.html   # 프론트엔드 대시보드
```
