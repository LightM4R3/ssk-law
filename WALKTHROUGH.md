# SSK-Law 서비스 통합 및 실시간 API 연동 보고서 (Walkthrough)

이 문서는 프론트엔드의 대규모 하드코딩 더미 데이터를 완전히 제거하고, Django DRF 백엔드 API 및 로컬 Ollama AI 서비스와 완벽하게 연동될 수 있도록 구축한 작업 내역을 정리한 것입니다.

다른 컴퓨터에서 이 프로젝트를 인계받아 마저 실행하거나 테스트하려는 경우, 아래 가이드를 참고해 주세요.

---

## 1. 주요 변경 사항 및 호환성 개선 내역

### 1) 프론트엔드 연동 및 리팩토링 (더미 폴백 완전 제거)
- **`index.html`**:
  - 프론트엔드가 백엔드 개발 서버를 올바르게 호출하도록 script 로드 직전 `window.SSK_API_BASE = "http://localhost:8000";` 설정을 동적으로 주입했습니다.
- **`scripts/data.js`**:
  - 기존에 하드코딩되어 있던 대규모 법안 및 인기 법안 데이터 배열 (`CATEGORIES`, `PICKS`, `BILLS`, `WEEKLY` 변수들)을 완전히 삭제하고 빈 배열 `[]`로 초기화했습니다.
- **`scripts/api.js`**:
  - 백엔드에 없는 `/api/weekly` 엔드포인트를 장고 API 정렬 방식인 `GET /api/bills?sort=-view_count&page_size=10`으로 조회수 순 상위 10개 법안을 조회하도록 자동 맵핑했습니다.
  - API 호출 에러 시 임시/더미 데이터로 복구하는 폴백 로직을 전면 제거하여 백엔드 DB 서버의 오동작이나 연결 실패를 확실하게 인지할 수 있도록 하였습니다.
- **`scripts/search.js`**:
  - AI 자연어 검색 시 모의 어시스턴트(`window.claude.complete`) 호출 및 로컬 키워드 매칭 폴백 코드를 제거하고, 백엔드의 `POST /api/search` API와 실시간 비동기 연동을 마쳤습니다.
  - 검색 결과로 들어온 새 법안 정보는 전역 색인 사전인 `ALL_BY_ID`에 동적으로 정합되게 설계하여 검색 결과 카드나 상세 모달 팝업이 완벽히 동작합니다.
- **`scripts/modal.js`**:
  - 법안 상세 정보 로드 시 로컬 메모리 참조 대신 실시간으로 백엔드의 상세 API `GET /api/bills/{bill_id}`를 호출하여 AI 3줄 요약, 예상 영향 및 유사 법안 리스트를 출력합니다.
  - 상세 정보 조회 시 백엔드 DB 내부에서 조회수(`view_count`)가 정상적으로 누적 카운트되는 것을 확인했습니다.

### 2) 백엔드 AI 설정 및 JSON 파싱 에러 수정
- **로컬 LLM 연동**:
  - 로컬 장비의 Ollama 모델 기본 설정을 실제 탑재 모델인 `gemma4:e4b`로 조정하고, 국회 API 수집을 위한 기본키를 매핑했습니다.
- **Ollama 응답 파싱 버그 해결**:
  - 줄바꿈이 있는 구조화된 JSON 응답 파싱 시 첫 줄만 잘라내어 파싱 실패가 뜨던 부분을 정규식 및 JSON 중괄호 매칭을 기반으로 전체 문자열을 온전히 잡아내 파싱하도록 `backend/services/ollama.py`를 보완했습니다.

### 3) 로컬 LLM 기반 법안 분야(카테고리) 자동 분류 및 폴백 기능 도입
- **AI 기반 자동 분류 (`ollama.py`)**:
  - `ollama.summarize_bill` 함수에서 3줄 요약과 예상 영향, 시민 호감도와 더불어, **9가지 대분류 분야(labor, welfare, housing, economy, education, env, digital, health, safety) 중 가장 깊이 연관된 1~2개 슬러그를 선택하여 JSON 배열**(`"categories"`)로 동적으로 리턴하도록 프롬프트 및 스키마를 고도화했습니다.
- **수집 파이프라인 연계 및 폴백 장치 (`sync_bills.py`)**:
  - `sync_bills` 커맨드에서 국회 법안을 수집할 때 로컬 LLM을 호출하여 생성된 요약 및 AI 분류 슬러그 리스트를 DB의 `BillCategory`에 매핑합니다.
  - 로컬 AI 오동작, 인코딩 에러, 카테고리 누락 등이 발생하더라도 데이터 정합성을 유지할 수 있도록, **기존 소관위원회 기반 하드코딩 매핑(`_map_categories`) 폴백 메커니즘**을 탑재했습니다.
  - 프론트엔드가 호출하는 `/api/bills/` API 및 상세/카테고리 필터링 API 스펙과 일관되게 연결되어, AI가 자동 태깅한 분류가 사용자 UI 상단에 실시간으로 표시됩니다.

---

## 2. 개발 및 실행 환경 구동 방법

이 프로젝트를 다른 환경이나 새로운 컴퓨터에서 구동할 때 아래의 순서대로 구동합니다.

### 1) 백엔드 장고 서버 구동 (포트 8000)
1. 백엔드 폴더로 이동합니다.
   ```bash
   cd backend
   ```
2. 가상환경을 활성화하고 필요한 종속성 패키지들을 설치합니다.
   ```powershell
   # Windows PowerShell
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. 데이터베이스 마이그레이션을 실행하고, 실제 국회 API 데이터 및 AI 요약본을 동기화합니다.
   ```powershell
   python manage.py migrate
   # 국회 법안 데이터 1페이지(10건)를 로컬 Ollama AI를 통해 3줄 요약 및 동기화 처리
   python manage.py sync_bills --pages 1
   ```
4. 백엔드 개발 서버를 구동합니다.
   ```powershell
   python manage.py runserver 8000
   ```

### 2) 프론트엔드 정적 웹 서버 구동 (포트 5173)
프론트엔드는 단순 HTML/JS로 이루어져 있어 Node.js 빌드가 필요하지 않습니다. Python 내장 간이 웹 서버를 통해 실행합니다.
1. 프론트엔드 폴더로 이동합니다.
   ```bash
   cd frontend
   ```
2. 파이썬 간이 서버를 5173 포트로 실행합니다.
   ```powershell
   python -m http.server 5173
   ```
3. 웹 브라우저에서 `http://localhost:5173`으로 접속하여 테스트를 진행합니다.

### 3) 로컬 Ollama AI 서비스 구동 (포트 11434)
- 로컬 시스템에 [Ollama](https://ollama.com)가 실행 중이어야 하며, 백엔드가 바라보는 모델(`gemma4:e4b`)이 다운로드되어 있어야 합니다.
- Ollama가 작동 중인지 `http://localhost:11434`를 통해 확인합니다.

---

## 3. 통합 테스트 실행 및 결과

백엔드와 프론트엔드 간의 모든 API 통신 스펙을 점검하기 위해 작성된 통합 테스트 스크립트를 다음과 같이 구동할 수 있습니다.

```powershell
cd backend
$env:PYTHONUTF8=1  # Windows 콘솔 한글/이모지 인코딩 오류 방지
.\venv\Scripts\python.exe test_api_integration.py
```

### 테스트 성공 출력 예시
모든 엔드포인트가 정상적으로 통과하면 아래와 같이 표시됩니다:

```text
=================== SSK-LAW API INTEGRATION TEST ===================
Testing GET /api/categories...
  Success: Found 10 categories.
    - 전체 (all): 21 bills
    - 노동 (labor): 1 bills
    - 복지 (welfare): 6 bills
    ...
Testing GET /api/home/picks...
  Success: Found 5 picks.
    - Top Pick: 플랫폼 노동자에게도 유급 휴가와 산재보험을.
Testing GET /api/bills...
  Success: Found 20 bills (Total: 21).
Testing GET /api/bills?category=labor...
  Success: Found 1 labor bills.
Testing GET /api/bills?sort=-view_count&page_size=3...
  Success: Top 3 viewed bills:
    1. 플랫폼 노동자에게도 유급 휴가와 산재보험을. (Views: 128404)
Testing GET /api/bills/PRC_P1...
  Success: Detailed bill '플랫폼 노동자에게도 유급 휴가와 산재보험을.' loaded.
Testing POST /api/search (AI Search)...
  Success: AI Search Response received.
Testing POST /api/chat (AI Chatbot)...
  Success: Chat reply received.
Testing GET /api/chat/history...
  Success: Chat history loaded. Messages in session: 2

=================== ALL TESTS PASSED SUCCESSFULLY! ===================
```
