# SSK-Law Backend

슥법(SSK-Law) Django REST Framework 백엔드입니다.

## 명세서

- [API 명세서](docs/API_SPEC.md) — 엔드포인트 정의, 요청/응답 형식, 프론트엔드 연동 가이드
- [데이터베이스 명세서](docs/DATABASE_SPEC.md) — 테이블 정의, ER 다이어그램, 인덱스 전략

## 기술 스택

- Python 3.11+
- Django 5.x
- Django REST Framework 3.x
- SQLite (개발) / PostgreSQL (운영)
- Ollama (AI 요약 · 챗봇)

## MVP 기능

1. **국회 법률발의안 수집 · AI 요약**: 열린국회정보 API 연동 → DB 저장 → Ollama 3줄 요약 생성
2. **AI 챗봇**: 법률 관련 자연어 질문에 AI가 법안 데이터 기반으로 답변

## 디렉토리 구조 (예정)

```text
backend/
├── config/              # Django 프로젝트 설정
├── bills/               # 법안 앱 (모델, 뷰, 시리얼라이저)
├── chat/                # 챗봇 앱
├── services/            # 외부 서비스 연동 (국회 API, Ollama)
├── docs/                # 명세서
│   ├── API_SPEC.md
│   └── DATABASE_SPEC.md
├── manage.py
├── requirements.txt
└── README.md
```
