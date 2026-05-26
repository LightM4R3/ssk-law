# 슥법 (SSK-Law) Django REST Framework 백엔드 가이드

이 저장소는 국회 법률발의안을 수집하고 AI를 통해 요약 큐레이션 및 자연어 질답을 제공하는 **슥법** 서비스의 DRF 백엔드 프로젝트입니다.

---

## 1. 사전 요구사항

다른 컴퓨터에서 구동하기 전에 아래 항목들이 필요합니다.
- **Python 3.11 이상**
- **Ollama 서비스**: 로컬 기기에 설치 및 실행 중이어야 합니다.
  - 사용 모델: **`gemma4:e4b`**가 미리 설치되어 있어야 합니다.
  - 모델 다운로드 명령: `ollama run gemma4:e4b`
- **국회 OpenAPI 인증키**: 기본 키(`7ebbc9b78224446d89af859b2117e88e`)가 설정에 내장되어 있으나, 커스텀 키를 사용하려는 경우 환경 변수(`ASSEMBLY_API_KEY`)로 지정할 수 있습니다.

---

## 2. 개발 환경 설정 및 설치

프로젝트의 `backend` 디렉토리로 이동하여 가상환경을 활성화하고 패키지를 설치합니다.

### Windows (PowerShell/CMD)
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Mac / Linux
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. 데이터베이스 초기화 및 시드 데이터 로드

로컬 SQLite 데이터베이스 파일(`db.sqlite3`) 구조를 만들고 기본 테스트 데이터를 입력합니다.

```bash
# 1. DB 테이블 생성 (마이그레이션 적용)
python manage.py migrate

# 2. 테스트용 시드 데이터 로드
python manage.py seed_data
```

---

## 4. 국회 실시간 법안 수집 및 AI 요약 (동기화 명령어)

슥법 백엔드는 국회 OpenAPI로부터 법안 데이터를 실시간으로 동기화하고 로컬 LLM을 통해 요약 정보를 생성하는 두 가지 명령어를 지원합니다. 

> [!IMPORTANT]
> 명령어를 실행하기 전에 반드시 **Ollama 데스크톱 앱이 실행 중**이어야 하며, `gemma4:e4b` 모델이 로컬에 설치되어 있어야 합니다.

### A. 대량 법안 일괄 수집 및 가공 명령어 (추천)
최신 법률 발의안, 법사위 처리 법안, 본회의 처리 법안을 **각 100개씩** 일괄 수집하고, DB에 존재하지 않는 상위 법안들을 자동 신규 적재한 뒤 AI 요약 가공까지 원클릭으로 처리합니다.
데이터를 최초로 수집할 때나 주기적인 대용량 업데이트 시에 유용합니다.

```bash
# 기본 실행 (일반 100개, 법사위 100개, 본회의 100개 동기화 및 최대 100개 요약 처리)
python manage.py sync_and_process_100_bills

# 테스트용 실행 (1페이지 수집, LLM 처리 대수를 3대로 제한하여 고속 테스트)
python manage.py sync_and_process_100_bills --pages 1 --limit-llm 3
```
- `--pages`: 일반 발의안 API 조회 페이지 수 (페이지당 10개, 기본값: 10)
- `--limit-llm`: 이 실행에서 LLM(Ollama) 요약 가공을 수행할 최대 법안 수 (기본값: 100)

### B. 기본 법안 동기화 명령어
국회 OpenAPI에서 지정된 페이지 수만큼 최근 법안들을 수집하고 단계를 동기화합니다. (AI 요약 가공은 수행하지 않습니다.)

```bash
# 최신 10개 법안 수집 및 법사위/본회의 단계 업데이트
python manage.py sync_bills --pages 1
```
- `--pages`: 조회할 페이지 수 (기본값: 1)


---

## 5. 로컬 개발 서버 실행

장고 API 서버(기본 포트: 8000)를 가동합니다.
```bash
python manage.py runserver
```
- 서버 구동 주소: `http://localhost:8000`

---

## 6. 기능 테스트 및 API 검증

서버가 켜진 상태에서, 전체적인 동작 상태(카테고리 조회, 검색, AI 질답 등)를 테스트할 수 있는 검증 스크립트가 제공됩니다.

### Windows (한글/이모지 인코딩 지원 환경 변수 필요)
```powershell
$env:PYTHONIOENCODING="utf-8"
python test_api_integration.py
```

### Mac / Linux
```bash
python test_api_integration.py
```

- 모든 엔드포인트가 성공하면 터미널 맨 하단에 `=================== ALL TESTS PASSED SUCCESSFULLY! ===================` 문구가 출력됩니다.

---

## 7. 구현된 핵심 API 명세 요약

자세한 요청/응답 스키마는 `backend/docs/API_SPEC.md`를 참고해 주세요.

1. **`GET /api/categories`**
   - 전체 카테고리(노동, 복지, 주거 등) 목록 및 각 카테고리별 법안 누적 개수 반환
2. **`GET /api/home/picks`**
   - 메인 화면 상단 캐러셀용 오늘의 큐레이션 추천 법안 리스트 반환
3. **`GET /api/bills`**
   - 전체 법안 조회. `?category=labor`를 이용한 카테고리 필터링 및 `?sort=-view_count` 등의 인기순 정렬, 페이징 기능 제공
4. **`GET /api/bills/<id>`**
   - 의안 상세 정보, AI 3줄 요약 내용 및 유사 추천 법안 리스트 반환
5. **`POST /api/search`**
   - AI 자연어 검색 지원. 사용자의 입력 문장을 로컬 LLM을 통해 정합성을 대조한 후 관련 3~5개 법안 및 친근한 반말 큐레이션 문장을 JSON으로 반환
6. **`POST /api/chat`**
   - 실시간 AI 챗봇 대화. 관련 법안을 컨텍스트로 제공하여 맞춤형 질답을 생성하고 `session_key` 발급
7. **`GET /api/chat/history`**
   - 세션 키별로 저장된 과거 대화 이력을 로드해 챗봇 대화창 유지 기능 제공
