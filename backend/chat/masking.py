import re

def mask_personal_info(text: str) -> str:
    """사용자 입력 텍스트에서 이름, 전화번호, 주소를 안전하게 마스킹 처리합니다.

    1. 주소 마스킹 선행: 상세 정보를 ****로 가려 이름 오탐의 소지를 줄임
    2. 전화번호 마스킹
    3. 이름 마스킹 후행: 주소 관련 접미사 제외 규칙 및 다양한 한국어 조사 분리 적용
    """
    if not text:
        return text

    masked = text

    # 1. 주소 마스킹
    # 주요 광역시/도 축약 명칭 포함하여 매칭
    address_pattern = re.compile(
        r'\b(서울특별시|울산광역시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|세종특별자치시|경기도|강원특별자치도|강원도|충청북도|충북|충청남도|충남|전라북도|전북|전라남도|전남|경상북도|경북|경상남도|경남|제주특별자치도|제주도|서울시|부산시|대구시|인천시|광주시|대전시|울산시|세종시|서울|울산|부산|대구|인천|광주|대전|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s+([가-힣\d\(\)]+(?:시|군|구))(?:\s+([가-힣\d\(\)]+(?:동|읍|면|리|로|길)))?(?:\s+(\d+([-~\d\s]*[가-힣]*)*))?\b'
    )

    def replace_address(match):
        region = match.group(1)
        parts = []
        if match.group(2):
            parts.append("****")
        if match.group(3):
            parts.append("****")
        if match.group(4):
            parts.append("****")
        return f"{region} " + " ".join(parts)

    masked = address_pattern.sub(replace_address, masked)

    # 2. 전화번호 마스킹 (010-1234-5678, 02-123-4567, 031-1234-5678 등)
    # 숫자 및 하이픈 패턴 매칭 (앞뒤에 숫자가 없을 때만 매칭하여 오탐 방지)
    phone_pattern = re.compile(
        r'(?<!\d)(0\d{1,2})[-.\s]?(\d{3,4})[-.\s]?(\d{4})(?!\d)'
    )
    masked = phone_pattern.sub(r'\1-****-****', masked)

    # 3. 이름 마스킹
    # 한국의 흔한 성씨 (20대 성씨 + 복성 일부)
    surnames = set([
        "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
        "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍", "유"
    ])
    double_surnames = set(["남궁", "황보", "제갈", "사공", "독고"])

    # 조사 목록 (긴 조사부터 탐색하여 탐지)
    josa_list = [
        "입니다", "이라고", "으로서", "으로써", "에게서", "한테서", "에게", "한테",
        "에서", "이다", "이가", "은", "는", "이", "가", "을", "를", "와", "과",
        "의", "로", "으로", "고", "하고", "하며", "랑", "이랑", "이고", "이며", "처럼", "보다"
    ]

    # 제외할 흔한 일반 명사 및 용언 형태 (오탐 방지)
    exclude_words = {
        "이름", "주소", "소음", "민원", "사건", "사실", "이유", "이용", "이전", "전화", 
        "전세", "전체", "강요", "강력", "서류", "서면", "신청", "신고", "안내", "안건",
        "이하", "이상", "이내", "전후", "오후", "오전", "서로", "조사", "결과", "정보",
        "조세", "조례", "조항", "조문", "조치"
    }

    def replace_name(match):
        word = match.group(0)
        
        # 조사가 붙어있는지 확인하고 stem 분리
        matched_josa = ""
        stem = word
        for josa in sorted(josa_list, key=len, reverse=True):
            if word.endswith(josa):
                stem = word[:-len(josa)]
                matched_josa = josa
                break

        # 제외 단어 리스트에 포함되어 있으면 패스
        if stem in exclude_words:
            return word

        # 주소 접미사(시, 군, 구, 읍, 면, 리, 로, 길)로 끝나는 단어는 주소이므로 제외
        if stem.endswith(('시', '군', '구', '읍', '면', 'ri', '리', '로', '길')):
            return word

        # 복성(2글자 성씨) 매칭
        if len(stem) >= 3 and stem[:2] in double_surnames:
            # 예: 남궁민수 -> 남궁**
            first_name = stem[2:]
            masked_stem = stem[:2] + "*" * len(first_name)
            return masked_stem + matched_josa

        # 단성(1글자 성씨) 매칭
        if len(stem) in [2, 3] and stem[0] in surnames:
            if len(stem) == 2:
                # 2글자 이름 (예: 김철 -> 김*)
                masked_stem = stem[0] + "*"
            else:
                # 3글자 이름 (예: 홍길동 -> 홍*동)
                masked_stem = stem[0] + "*" + stem[2]
            return masked_stem + matched_josa

        return word

    # 한글 문자열(가-힣) 매칭
    masked = re.sub(r'[가-힣]+', replace_name, masked)

    return masked
