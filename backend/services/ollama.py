"""Ollama AI client for summarization and chat."""

import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = 60  # seconds


def _call_ollama(prompt: str, system: str = "") -> str | None:
    """Send a prompt to Ollama and return the response text, or None on failure."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        logger.warning("Ollama call failed: %s", e)
        return None


def summarize_bill(title: str, proposer: str, committee: str = "", content: str = "") -> dict | None:
    """Generate a 3-line summary + impact + categories for a bill.

    Returns dict with keys: summary_1, summary_2, summary_3, impact, categories
    or None on failure.
    """
    system = (
        "당신은 시민에게 한국 법안을 친근하게 설명하고 분류하는 '슥법'의 AI 어시스턴트입니다. "
        "반드시 JSON으로만 응답하세요."
    )
    bill_info = f"법안명: {title}\n발의자: {proposer}\n소관위원회: {committee or '미정'}"
    if content:
        bill_info += f"\n상세 제안이유 및 주요 내용:\n{content}"

    prompt = f"""아래 법안을 시민이 쉽게 이해할 수 있도록 요약하고 어울리는 카테고리로 분류해주세요.

{bill_info}

분류 가능한 카테고리는 프론트엔드의 10대 분류 태그 중 '전체'를 제외한 아래 9개 후보군이며, 이들 중 가장 부합하는 것을 선택해야 합니다:
- labor (노동): 근로자 권리, 노동환경, 일자리, 고용 등과 관련된 법안
- welfare (복지): 기초생활보장, 아동/청소년/가족/노인 복지, 사회보장 등과 관련된 법안
- housing (주거): 주택 건설, 부동산, 월세/전세 지원, 도시 재생 등과 관련된 법안
- economy (경제): 금융, 기업 규제, 소상공인 지원, 세금, 산업 정책 등과 관련된 법안
- education (교육): 학교, 보육, 평생교육, 교원 권리 등과 관련된 법안
- env (환경 · 기후): 기후변화, 탄소배출, 폐기물, 자연보호 등과 관련된 법안
- digital (디지털): IT, 인공지능, 통신, 개인정보보호, 온라인 플랫폼 등과 관련된 법안
- health (보건): 의료, 약학, 공공보건, 감염병 예방 등과 관련된 법안
- safety (생활안전): 소방, 재난안전, 범죄예방, 교통안전 등과 관련된 법안

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 절대 금지):
{{
  "summary_1": "첫 번째 요약 문장",
  "summary_2": "두 번째 요약 문장",
  "summary_3": "세 번째 요약 문장",
  "impact": "예상 영향",
  "categories": ["카테고리슬러그1", "카테고리슬러그2"]
}}

- categories는 위 후보군(labor, welfare, housing, economy, education, env, digital, health, safety) 중 가장 깊이 연관된 1~2개 슬러그를 선택하여 JSON 배열로 리턴하세요. 없는 경우 빈 배열을 리턴하세요."""

    text = _call_ollama(prompt, system)
    if not text:
        return None

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            match = text[start:end]
            return json.loads(match)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse Ollama summary JSON: %s", e)

    return None


def search_bills(query: str, bill_list_text: str) -> dict | None:
    """Ask AI to select relevant bills and generate an intro.

    Returns dict with keys: intro, ids  — or None on failure.
    """
    system = (
        "당신은 시민에게 한국 법안을 친근하게 큐레이션하는 '슥법'의 AI 어시스턴트입니다."
    )
    prompt = f"""사용자 질문: "{query}"

아래 법안 목록에서 질문과 가장 관련있는 3-5개를 골라 id를 나열하고, 친근한 반말로 2-3문장 요약해주세요.
{bill_list_text}

반드시 이 JSON 형식으로만 응답하세요 (다른 텍스트 절대 금지):
{{"intro":"친근한 2-3문장 한국어 답변","ids":["id1","id2","id3"]}}"""

    text = _call_ollama(prompt, system)
    if not text:
        return None

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            obj = json.loads(text[start:end])
            if "intro" in obj and "ids" in obj:
                return obj
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def chat_reply(message: str, context: str, history: str = "") -> str | None:
    """Generate a chat reply given user message and bill context.

    Returns the reply text or None on failure.
    """
    system = (
        "당신은 시민에게 한국 법안을 친근하게 설명하는 '슥법'의 AI 법률 어시스턴트입니다. "
        "친근한 반말로 답변하세요. 정확한 법률 정보를 바탕으로 답변하되, "
        "전문 용어는 쉬운 말로 풀어 설명하세요."
    )
    prompt_parts = []
    if context:
        prompt_parts.append(f"[참고할 법안 데이터]\n{context}\n")
    if history:
        prompt_parts.append(f"[이전 대화]\n{history}\n")
    prompt_parts.append(f"사용자: {message}\n어시스턴트:")

    text = _call_ollama("\n".join(prompt_parts), system)
    return text
