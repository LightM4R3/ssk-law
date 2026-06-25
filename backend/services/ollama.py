"""Ollama AI client for summarization and chat."""

import json
import logging
import re
import unicodedata

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def _call_ollama(
    prompt: str,
    system: str = "",
    *,
    model: str | None = None,
    options: dict | None = None,
    response_format: str | dict | None = None,
    timeout_seconds: float | None = None,
) -> str | None:
    """Send a prompt to Ollama and return the response text, or None on failure."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model or settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }
    if system:
        payload["system"] = system
    if options:
        payload["options"] = options
    if response_format:
        payload["format"] = response_format

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=timeout_seconds or settings.OLLAMA_TIMEOUT,
        )
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

    text = _call_ollama(
        prompt,
        system,
        options={"temperature": 0.1, "num_predict": 500},
        response_format="json",
    )
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

    text = _call_ollama(
        prompt,
        system,
        model=settings.OLLAMA_REALTIME_MODEL,
        options={"temperature": 0.2, "num_predict": 220},
        response_format="json",
    )
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
        "전문 용어는 쉬운 말로 풀어 설명하세요.\n\n"
        "[서술 지침 - 단정적 표현 금지]\n"
        "법적 해석에 대해 단정적인 표현('~야', '~입니다', '~가 확실해', '~가 맞아' 등)을 절대로 사용하지 마세요. "
        "대신 '~로 예상돼', '~할 가능성이 있어', '~라고 해석될 수 있어', '~라는 전례가 있지만 구체적인 상황에 따라 달라질 수 있어' 등 "
        "중립적이고 신중한 표현을 사용해야 합니다.\n"
        "Markdown, 제목, 목록, 강조 표시, 이모지, 인사말을 사용하지 마세요. "
        "질문을 반복하지 말고 핵심 설명만 일반 텍스트 4문장 이내로 작성하세요. "
        "면책 문구는 시스템이 별도로 붙이므로 생성하지 마세요."
    )
    prompt_parts = []
    if context:
        prompt_parts.append(f"[참고할 법안 데이터]\n{context}\n")
    if history:
        prompt_parts.append(f"[이전 대화]\n{history}\n")
    prompt_parts.append(f"사용자: {message}\n어시스턴트:")

    text = _call_ollama(
        "\n".join(prompt_parts),
        system,
        model=settings.OLLAMA_REALTIME_MODEL,
        options={"temperature": 0.2, "num_predict": 260},
    )
    return clean_plain_text(text, max_chars=600) if text else None


def explain_search(query: str, context: str) -> str | None:
    """Generate a short plain-text explanation after DB search results are ready."""
    system = (
        "너는 국회 법안 DB 검색 결과를 시민에게 간결하게 설명하는 안내자다. "
        "반드시 제공된 법안 데이터만 근거로 답변하고, 데이터에 없는 내용은 추측하지 않는다. "
        "법안 제목을 단순 나열하지 말고, 사용자가 알면 좋은 공통 쟁점과 차이를 설명한다. "
        "'현재 DB 기준', '검색 결과', '아래 법안', '참고용', '법률 자문' 같은 표현은 쓰지 않는다. "
        "질문에 직접 답한 뒤, 관련 법안들이 어떤 정책 방향으로 묶이는지 설명하고, 마지막에는 사용자가 어떤 관점으로 목록을 보면 좋은지 말한다. "
        "마크다운, 목록, 이모지, 인사말을 사용하지 않는다. "
        "2~3개의 짧은 문장으로 작성하고, 각 문장은 줄바꿈으로 구분한다. "
        "최대 420자 이내의 일반 텍스트로 작성한다."
    )
    prompt = f"""사용자 질문: {query}

관련 법안 데이터:
{context}

작성 지침:
- 하단에 법안 카드가 따로 표시되므로 법안 제목을 반복 나열하지 마세요.
- 질문자가 궁금해할 왜 관련 있는지, 어떤 생활/정책 쟁점인지, 어디를 비교해 보면 좋은지를 설명하세요.
- 관련성이 약하면 약하다고 말하고, 어떤 키워드 때문에 연결되었는지 짧게 밝히세요.
"""
    text = _call_ollama(
        prompt,
        system,
        model=settings.OLLAMA_REALTIME_MODEL,
        options={"temperature": 0.15, "num_predict": 320},
    )
    return format_search_explanation(clean_plain_text(text, max_chars=520)) if text else None


def format_search_explanation(text: str) -> str:
    """Make search explanations readable without relying on markdown."""
    value = str(text or "").strip()
    if not value:
        return value
    value = re.sub(r"\s+", " ", value)
    for phrase in (
        "현재 DB 기준입니다.",
        "현재 DB 기준입니다",
        "현재 DB 기준으로는",
        "현재 DB 기준으로",
        "현재 DB에 저장된 법안 기준으로는",
        "현재 DB에 저장된 법안 중",
    ):
        value = value.replace(phrase, "")
    value = re.sub(r"^\s*[,.·-]\s*", "", value).strip()
    value = re.sub(r"(다\.|요\.)\s+", r"\1\n", value)
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return "\n".join(lines[:3])


def clean_plain_text(text: str, max_chars: int = 600) -> str:
    """Normalize model output for safe plain-text rendering."""
    value = str(text or "").strip()
    value = re.sub(r"```(?:\w+)?", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", value)
    value = re.sub(r"(?m)^\s{0,3}(?:#{1,6}|[-*+]\s+|\d+[.)]\s+)", "", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    value = re.sub(r"(?m)^\s*---+\s*$", "", value)
    value = re.split(
        r"(?:면책\s*조항|본 답변은 참고용|이\s*설명은\s*참고용|법률\s*자문을\s*대신)",
        value,
        maxsplit=1,
    )[0]
    value = "".join(
        char
        for char in value
        if unicodedata.category(char) not in {"So", "Sk"}
    )
    value = re.sub(r"\s+", " ", value).strip(" -*_\n\t")
    if len(value) > max_chars:
        shortened = value[:max_chars]
        sentence_end = max(shortened.rfind("."), shortened.rfind("다."), shortened.rfind("요."))
        value = shortened[: sentence_end + 1] if sentence_end >= max_chars // 2 else shortened.rstrip() + "…"
    return value


def analyze_user_query(message: str) -> dict | None:
    """Convert a natural-language input into a bill-search strategy."""
    system = (
        "너는 사용자의 자연어 입력을 국회 법안 검색 전략으로 바꾸는 분석기다. "
        "답변을 생성하지 말고 JSON만 반환한다. "
        "입력이 잡담, 의미 불명, 너무 넓은 질문, 여러 주제 혼합인지 판단한다. "
        "검색이 가능하면 필수 조건, 보조 조건, 제외 조건을 분리한다. "
        "직접 검색하기 어렵다면 clarification_needed를 true로 하고 사용자가 고를 수 있는 짧은 질문을 만든다."
    )
    
    prompt = f"""사용자 입력을 법안 검색 전략 JSON으로 변환하세요.

[사용자 입력]
"{message}"

반드시 아래 JSON 형식으로만 응답하세요. 없는 값은 빈 배열이나 빈 문자열로 둡니다.
{{
  "intent": "bill_search | legal_question | chitchat | nonsense | unsafe | too_broad | mixed",
  "summary": "사용자 입력을 검색 관점에서 1문장으로 정리",
  "search_query": "DB 검색에 사용할 짧은 한국어 검색문",
  "must_have": ["검색 결과가 반드시 만족해야 할 핵심 축 1~4개"],
  "nice_to_have": ["있으면 좋은 보조 축 0~5개"],
  "exclude": ["질문과 무관해 제외할 주제 0~5개"],
  "keywords": ["검색용 핵심 명사 3~8개"],
  "risk_level": "High | Medium | Low",
  "confidence": 0.0,
  "clarification_needed": false,
  "clarification_question": ""
}}

[판단 지침]
- confidence는 검색 전략이 명확하면 0.75 이상, 여러 주제가 섞였지만 검색 축을 잡을 수 있으면 0.45~0.74, 의미가 불명확하면 0.44 이하로 둡니다.
- must_have에는 질문의 중심 축만 넣습니다. 예: "기후 피해", "농수산업", "기업 지원".
- nice_to_have에는 부가 맥락을 넣습니다. 예: "청년", "일자리", "벤처".
- exclude에는 질문과 무관한 큰 분야를 넣습니다. 예: "도로교통", "선거", "양성평등".
- 사용자가 법안 검색을 한 것이 아니라면 clarification_needed를 true로 둡니다.
- unsafe는 범죄 모의, 증거 인멸, 법 회피, 불법 행위 조력입니다.
"""

    text = _call_ollama(
        prompt,
        system,
        model=settings.OLLAMA_REALTIME_MODEL,
        options={"temperature": 0.0, "num_predict": 220},
        response_format="json",
        timeout_seconds=float(getattr(settings, "OLLAMA_ANALYSIS_TIMEOUT", 3)),
    )
    if not text:
        return None

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            match = text[start:end]
            return json.loads(match)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse query analysis JSON: %s", e)

    return None
