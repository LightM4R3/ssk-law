"""Seed the database with sample data from the frontend data.js for testing."""

from datetime import date
from django.core.management.base import BaseCommand
from bills.models import Bill, BillCategory, BillSummary, Category, SimilarBill


CATEGORIES_SEED = [
    ("labor", "노동", 1),
    ("welfare", "복지", 2),
    ("housing", "주거", 3),
    ("economy", "경제", 4),
    ("education", "교육", 5),
    ("env", "환경 · 기후", 6),
    ("digital", "디지털", 7),
    ("health", "보건", 8),
    ("safety", "생활안전", 9),
]

BILLS_SEED = [
    {
        "bill_id": "PRC_P1",
        "bill_no": "2126001",
        "title": "플랫폼 노동자에게도 유급 휴가와 산재보험을.",
        "proposer": "김○○ 의원 외 12인",
        "committee": "환경노동위원회",
        "stage": "committee",
        "proposed_at": "2026-04-28",
        "categories": [("labor", True), ("welfare", False)],
        "summary": [
            "배달·대리·가사 등 플랫폼을 통해 일하는 노동자에게도 4대 보험과 유급 휴가를 단계적으로 보장합니다.",
            "주 15시간 이상 일한 경우 연 5일의 유급 휴가를 도입합니다.",
            "플랫폼 기업은 노동자 보호 알고리즘 운영 지침을 매년 공시합니다.",
        ],
        "impact": "약 80만 명의 플랫폼 노동자에게 직접 영향. 휴식권·의료 안전망 확대.",
        "sentiment": 68,
        "view_count": 128400,
        "similar": [
            {"title": "특수형태근로종사자 권익 보호법 일부개정안", "date": "2026.03.11", "stage_label": "위원회"},
            {"title": "프리랜서 표준계약 의무화법", "date": "2026.02.04", "stage_label": "본회의"},
        ],
    },
    {
        "bill_id": "PRC_P2",
        "bill_no": "2126002",
        "title": "청년 월세 지원 한도를 30만 원으로.",
        "proposer": "박○○ 의원 외 9인",
        "committee": "국토교통위원회",
        "stage": "proposed",
        "proposed_at": "2026-05-07",
        "categories": [("housing", True), ("welfare", False)],
        "summary": [
            "만 19–34세 청년에게 월세 지원 한도를 월 20만 원에서 30만 원으로 인상합니다.",
            "지원 기간을 12개월에서 24개월로 늘리고 보증금 대출 이자도 지원합니다.",
            "수도권 외 지역에는 추가 가점을 부여합니다.",
        ],
        "impact": "지원 대상 약 13만 명 확대 예상.",
        "sentiment": 74,
        "view_count": 96200,
        "similar": [
            {"title": "신혼부부 전세자금 대출 한도 확대법", "date": "2026.04.20", "stage_label": "위원회"},
            {"title": "1인 가구 주거 안정 지원법", "date": "2026.03.30", "stage_label": "위원회"},
        ],
    },
    {
        "bill_id": "PRC_P3",
        "bill_no": "2126003",
        "title": "중·고등학교 무상급식, 전국으로.",
        "proposer": "이○○ 의원 외 8인",
        "committee": "교육위원회",
        "stage": "committee",
        "proposed_at": "2026-05-05",
        "categories": [("education", True), ("welfare", False)],
        "summary": [
            "지자체별로 다른 무상급식을 전국 중·고등학교로 확대합니다.",
            "급식 재료의 30% 이상은 지역 농산물로 의무 조달합니다.",
            "알레르기·종교적 식단을 위한 대체 메뉴 제공을 의무화합니다.",
        ],
        "impact": "전국 중·고생 약 270만 명. 학부모 부담 평균 월 8만 원 절감.",
        "sentiment": 81,
        "view_count": 71800,
        "similar": [
            {"title": "친환경 학교급식 의무 비율 상향법", "date": "2026.02.18", "stage_label": "본회의"},
        ],
    },
    {
        "bill_id": "PRC_P4",
        "bill_no": "2126004",
        "title": "소상공인 카드 수수료, 0.5%로.",
        "proposer": "오○○ 의원 외 7인",
        "committee": "정무위원회",
        "stage": "plenary",
        "proposed_at": "2026-04-27",
        "categories": [("economy", True)],
        "summary": [
            "연 매출 3억 원 이하 소상공인의 카드 수수료를 0.5%로 인하합니다.",
            "결제대행사(PG)의 추가 수수료를 명확히 공시하도록 합니다.",
            "정기적인 수수료 적정성 검증을 도입합니다.",
        ],
        "impact": "전국 소상공인 약 290만 명 대상. 연간 평균 약 64만 원 절감 추정.",
        "sentiment": 77,
        "view_count": 42600,
        "similar": [
            {"title": "전통시장 카드결제 인프라 지원법", "date": "2026.03.15", "stage_label": "위원회"},
        ],
    },
    {
        "bill_id": "PRC_P5",
        "bill_no": "2126005",
        "title": "기후 적응 도시계획, 의무가 됩니다.",
        "proposer": "한○○ 의원 외 14인",
        "committee": "환경노동위원회",
        "stage": "committee",
        "proposed_at": "2026-04-30",
        "categories": [("env", True)],
        "summary": [
            "인구 30만 명 이상 도시는 기후 적응 계획 수립을 의무화합니다.",
            "폭염·침수 취약 지역에 그늘막·녹지 확보 기준을 신설합니다.",
            "5년마다 적응 성과를 의무 공시합니다.",
        ],
        "impact": "전국 약 30개 광역·기초 지자체에 적용.",
        "sentiment": 63,
        "view_count": 28400,
        "similar": [
            {"title": "도시공원 최저 면적 기준 상향법", "date": "2026.02.10", "stage_label": "위원회"},
        ],
    },
    {
        "bill_id": "PRC_B3",
        "bill_no": "2126006",
        "title": "어린이 보행자 보호구역 확대·처벌 강화법",
        "proposer": "최○○ 의원 외 6인",
        "committee": "행정안전위원회",
        "stage": "committee",
        "proposed_at": "2026-05-03",
        "categories": [("safety", True)],
        "summary": [
            "어린이집·유치원 반경 300m까지 보호구역을 확대합니다.",
            "보호구역 내 신호 위반·과속 시 과태료를 2배로 상향합니다.",
            "",
        ],
        "impact": "전국 약 1.2만 개 어린이 시설 인근 도로에 적용.",
        "sentiment": 72,
        "view_count": 54300,
        "similar": [
            {"title": "스쿨존 카메라 의무 설치법", "date": "2026.01.21", "stage_label": "통과"},
        ],
    },
    {
        "bill_id": "PRC_B4",
        "bill_no": "2126007",
        "title": "반려동물 진료비 표준화·보험 도입법",
        "proposer": "정○○ 의원 외 11인",
        "committee": "농림축산식품해양수산위원회",
        "stage": "proposed",
        "proposed_at": "2026-05-02",
        "categories": [("welfare", True), ("health", False)],
        "summary": [
            "동물병원의 주요 진료 항목 가격을 표준 고시합니다.",
            "민간 반려동물 보험에 정부가 일부 보조금을 지원합니다.",
            "",
        ],
        "impact": "반려가구 약 600만 가구의 진료비 예측 가능성 향상.",
        "sentiment": 70,
        "view_count": 49100,
        "similar": [
            {"title": "동물병원 진료비 사전 공시제 법안", "date": "2026.03.02", "stage_label": "위원회"},
        ],
    },
    {
        "bill_id": "PRC_B7",
        "bill_no": "2126008",
        "title": "노인 대중교통 무료 이용 연령 단계적 조정법",
        "proposer": "윤○○ 의원 외 10인",
        "committee": "국토교통위원회",
        "stage": "committee",
        "proposed_at": "2026-04-25",
        "categories": [("welfare", True), ("safety", False)],
        "summary": [
            "지하철·버스 무료 이용 연령을 65세에서 점진적으로 70세로 조정합니다.",
            "조정 시기에는 저소득 노인에게 교통비 바우처를 별도 지원합니다.",
            "광역철도까지 무료 이용 범위를 확대합니다.",
        ],
        "impact": "단기 재정 부담 완화와 함께 저소득 노인 보호 병행.",
        "sentiment": 55,
        "view_count": 38100,
        "similar": [
            {"title": "노인 교통비 바우처 지원법", "date": "2026.03.06", "stage_label": "위원회"},
        ],
    },
    {
        "bill_id": "PRC_B8",
        "bill_no": "2126009",
        "title": "청소년 디지털 권리·알고리즘 투명성법",
        "proposer": "장○○ 의원 외 9인",
        "committee": "과학기술정보방송통신위원회",
        "stage": "committee",
        "proposed_at": "2026-04-22",
        "categories": [("digital", True), ("education", False)],
        "summary": [
            "만 18세 미만 사용자에게는 추천 알고리즘을 끌 수 있는 기본값을 의무화합니다.",
            "교육 기관에서의 생성형 AI 활용 가이드라인을 마련합니다.",
            "",
        ],
        "impact": "주요 SNS·동영상 플랫폼 청소년 이용자 약 540만 명.",
        "sentiment": 66,
        "view_count": 31900,
        "similar": [
            {"title": "디지털 잊혀질 권리법", "date": "2026.02.27", "stage_label": "위원회"},
        ],
    },
    {
        "bill_id": "PRC_B9",
        "bill_no": "2126010",
        "title": "공공장소 무료 와이파이 의무 설치법",
        "proposer": "송○○ 의원 외 6인",
        "committee": "과학기술정보방송통신위원회",
        "stage": "proposed",
        "proposed_at": "2026-04-20",
        "categories": [("digital", True)],
        "summary": [
            "도서관·복지관·공원 등 공공시설에 무료 와이파이 설치를 의무화합니다.",
            "보안 기준과 개인정보 처리 원칙을 함께 규정합니다.",
            "",
        ],
        "impact": "전국 약 4.2만 개 공공시설 대상.",
        "sentiment": 60,
        "view_count": 22000,
        "similar": [],
    },
    {
        "bill_id": "PRC_B10",
        "bill_no": "2126011",
        "title": "1인 가구 응급 의료 안전망법",
        "proposer": "신○○ 의원 외 8인",
        "committee": "보건복지위원회",
        "stage": "committee",
        "proposed_at": "2026-04-18",
        "categories": [("health", True), ("welfare", False)],
        "summary": [
            "독거 1인 가구에 응급 호출 단말기와 정기 안부 점검을 제공합니다.",
            "응급 시 가까운 의료기관과 자동 연계되도록 합니다.",
            "",
        ],
        "impact": "전국 1인 가구 중 취약계층 약 110만 명.",
        "sentiment": 73,
        "view_count": 24800,
        "similar": [],
    },
]


class Command(BaseCommand):
    help = "Seed the database with sample data from frontend data.js"

    def handle(self, *args, **options):
        # Categories
        cat_map = {}
        for slug, label, order in CATEGORIES_SEED:
            cat, created = Category.objects.update_or_create(
                slug=slug, defaults={"label": label, "sort_order": order}
            )
            cat_map[slug] = cat
            status_label = "Created" if created else "Updated"
            self.stdout.write(f"  {status_label} category: {label}")

        # Bills
        for data in BILLS_SEED:
            bill, created = Bill.objects.update_or_create(
                bill_id=data["bill_id"],
                defaults={
                    "bill_no": data["bill_no"],
                    "title": data["title"],
                    "proposer": data["proposer"],
                    "committee": data.get("committee", ""),
                    "stage": data["stage"],
                    "proposed_at": date.fromisoformat(data["proposed_at"]),
                    "view_count": data.get("view_count", 0),
                    "age": 22,
                },
            )
            status_label = "Created" if created else "Updated"
            self.stdout.write(f"  {status_label} bill: {data['title'][:40]}")

            # Categories
            BillCategory.objects.filter(bill=bill).delete()
            for slug, is_primary in data.get("categories", []):
                if slug in cat_map:
                    BillCategory.objects.create(
                        bill=bill, category=cat_map[slug], is_primary=is_primary
                    )

            # Summary
            summaries = data.get("summary", [])
            BillSummary.objects.update_or_create(
                bill=bill,
                defaults={
                    "summary_1": summaries[0] if len(summaries) > 0 else "",
                    "summary_2": summaries[1] if len(summaries) > 1 else "",
                    "summary_3": summaries[2] if len(summaries) > 2 else "",
                    "impact": data.get("impact", ""),
                    "sentiment": data.get("sentiment", 0),
                    "model_name": "seed-data",
                },
            )

            # Similar bills
            SimilarBill.objects.filter(source_bill=bill).delete()
            for sim in data.get("similar", []):
                SimilarBill.objects.create(
                    source_bill=bill,
                    title=sim["title"],
                    date=sim.get("date", ""),
                    stage_label=sim.get("stage_label", ""),
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Seeded {len(CATEGORIES_SEED)} categories and {len(BILLS_SEED)} bills."
        ))
