// All static data: categories, stages, bills, picks, weekly ranking, example queries
export const CATEGORIES = [
  { id: "all", label: "전체", count: 142 },
  { id: "labor", label: "노동", count: 18 },
  { id: "welfare", label: "복지", count: 24 },
  { id: "housing", label: "주거", count: 12 },
  { id: "economy", label: "경제", count: 21 },
  { id: "education", label: "교육", count: 11 },
  { id: "env", label: "환경 · 기후", count: 9 },
  { id: "digital", label: "디지털", count: 14 },
  { id: "health", label: "보건", count: 13 },
  { id: "safety", label: "생활안전", count: 8 },
];

/* Per-category aesthetic + editorial meta.
   Each gets a unique hue (oklch) but shares chroma/lightness — same family as the
   global --accent (oklch 0.42 0.08 245), only the hue rotates. */
export const CATEGORY_META = {
  labor:     { glyph: "勞", sub: "Labor",        hue: 22,  blurb: "일하는 사람의 권리·안전망",    new: 4, hot: true  },
  welfare:   { glyph: "福", sub: "Welfare",      hue: 145, blurb: "돌봄·소득·복지 안전망",        new: 6, hot: true  },
  housing:   { glyph: "宅", sub: "Housing",      hue: 285, blurb: "월세·전세·청년 주거 안정",     new: 3, hot: false },
  economy:   { glyph: "經", sub: "Economy",      hue: 60,  blurb: "소상공인·금융·세제",            new: 5, hot: false },
  education: { glyph: "敎", sub: "Education",    hue: 200, blurb: "학교·청소년·평생교육",          new: 2, hot: false },
  env:       { glyph: "綠", sub: "Climate",      hue: 165, blurb: "기후·자원순환·도시 적응",       new: 3, hot: true  },
  digital:   { glyph: "디", sub: "Digital",      hue: 245, blurb: "플랫폼·AI·개인정보",            new: 4, hot: false },
  health:    { glyph: "醫", sub: "Health",       hue: 0,   blurb: "의료·공공보건·돌봄",            new: 3, hot: false },
  safety:    { glyph: "安", sub: "Safety",       hue: 35,  blurb: "교통·재난·생활안전",            new: 2, hot: false },
};

export const STAGES = {
  proposed:  { label: "발의",        cls: "s1", idx: 0 },
  committee: { label: "위원회 심사",  cls: "s2", idx: 1 },
  plenary:   { label: "본회의 상정",  cls: "s3", idx: 2 },
  passed:    { label: "통과 · 공포",  cls: "s4", idx: 3 },
};

/* TODAY's PICKS — 5 (home carousel) */
export const PICKS = [
  {
    id: "p1",
    title: "플랫폼 노동자에게도 유급 휴가와 산재보험을.",
    cats: [{label:"노동", k:"labor", accent:true}, {label:"복지", k:"welfare"}],
    proposedAt: "2026.04.28", proposer: "김○○ 의원 외 12인",
    stage: "committee",
    summary: [
      "배달·대리·가사 등 플랫폼을 통해 일하는 노동자에게도 4대 보험과 유급 휴가를 단계적으로 보장합니다.",
      "주 15시간 이상 일한 경우 연 5일의 유급 휴가를 도입합니다.",
      "플랫폼 기업은 노동자 보호 알고리즘 운영 지침을 매년 공시합니다.",
    ],
    impact: "약 80만 명의 플랫폼 노동자에게 직접 영향. 휴식권·의료 안전망 확대.",
    similar: [
      { title: "특수형태근로종사자 권익 보호법 일부개정안", date: "2026.03.11", stage: "위원회" },
      { title: "프리랜서 표준계약 의무화법", date: "2026.02.04", stage: "본회의" },
    ]
  },
  {
    id: "p2",
    title: "청년 월세 지원 한도를 30만 원으로.",
    cats: [{label:"주거", k:"housing", accent:true}, {label:"복지", k:"welfare"}],
    proposedAt: "2026.05.07", proposer: "박○○ 의원 외 9인",
    stage: "proposed",
    summary: [
      "만 19–34세 청년에게 월세 지원 한도를 월 20만 원에서 30만 원으로 인상합니다.",
      "지원 기간을 12개월에서 24개월로 늘리고 보증금 대출 이자도 지원합니다.",
      "수도권 외 지역에는 추가 가점을 부여합니다.",
    ],
    impact: "지원 대상 약 13만 명 확대 예상.",
    similar: [
      { title: "신혼부부 전세자금 대출 한도 확대법", date: "2026.04.20", stage: "위원회" },
      { title: "1인 가구 주거 안정 지원법", date: "2026.03.30", stage: "위원회" },
    ]
  },
  {
    id: "p3",
    title: "중·고등학교 무상급식, 전국으로.",
    cats: [{label:"교육", k:"education", accent:true}, {label:"복지", k:"welfare"}],
    proposedAt: "2026.05.05", proposer: "이○○ 의원 외 8인",
    stage: "committee",
    summary: [
      "지자체별로 다른 무상급식을 전국 중·고등학교로 확대합니다.",
      "급식 재료의 30% 이상은 지역 농산물로 의무 조달합니다.",
      "알레르기·종교적 식단을 위한 대체 메뉴 제공을 의무화합니다.",
    ],
    impact: "전국 중·고생 약 270만 명. 학부모 부담 평균 월 8만 원 절감.",
    similar: [
      { title: "친환경 학교급식 의무 비율 상향법", date: "2026.02.18", stage: "본회의" },
    ]
  },
  {
    id: "p4",
    title: "소상공인 카드 수수료, 0.5%로.",
    cats: [{label:"경제", k:"economy", accent:true}],
    proposedAt: "2026.04.27", proposer: "오○○ 의원 외 7인",
    stage: "plenary",
    summary: [
      "연 매출 3억 원 이하 소상공인의 카드 수수료를 0.5%로 인하합니다.",
      "결제대행사(PG)의 추가 수수료를 명확히 공시하도록 합니다.",
      "정기적인 수수료 적정성 검증을 도입합니다.",
    ],
    impact: "전국 소상공인 약 290만 명 대상. 연간 평균 약 64만 원 절감 추정.",
    similar: [
      { title: "전통시장 카드결제 인프라 지원법", date: "2026.03.15", stage: "위원회" },
    ]
  },
  {
    id: "p5",
    title: "기후 적응 도시계획, 의무가 됩니다.",
    cats: [{label:"환경 · 기후", k:"env", accent:true}],
    proposedAt: "2026.04.30", proposer: "한○○ 의원 외 14인",
    stage: "committee",
    summary: [
      "인구 30만 명 이상 도시는 기후 적응 계획 수립을 의무화합니다.",
      "폭염·침수 취약 지역에 그늘막·녹지 확보 기준을 신설합니다.",
      "5년마다 적응 성과를 의무 공시합니다.",
    ],
    impact: "전국 약 30개 광역·기초 지자체에 적용.",
    similar: [
      { title: "도시공원 최저 면적 기준 상향법", date: "2026.02.10", stage: "위원회" },
    ]
  },
];

/* LATEST GRID — 12 cards */
export const BILLS = [
  { id: "b0", span: "span-6", featured: true, ...PICKS[0] },
  { id: "b1", span: "span-3", ...PICKS[1] },
  { id: "b2", span: "span-3", ...PICKS[2] },
  { id: "b3", span: "span-2", compact: true,
    title: "어린이 보행자 보호구역 확대·처벌 강화법",
    cats: [{label:"생활안전", k:"safety", accent:true}],
    proposedAt: "2026.05.03", proposer: "최○○ 의원 외 6인", stage: "committee",
    summary: ["어린이집·유치원 반경 300m까지 보호구역을 확대합니다.","보호구역 내 신호 위반·과속 시 과태료를 2배로 상향합니다."],
    impact: "전국 약 1.2만 개 어린이 시설 인근 도로에 적용.",
    similar: [{title:"스쿨존 카메라 의무 설치법", date:"2026.01.21", stage:"통과"}]
  },
  { id: "b4", span: "span-2", compact: true,
    title: "반려동물 진료비 표준화·보험 도입법",
    cats: [{label:"생활", k:"welfare", accent:true}, {label:"보건", k:"health"}],
    proposedAt: "2026.05.02", proposer: "정○○ 의원 외 11인", stage: "proposed",
    summary: ["동물병원의 주요 진료 항목 가격을 표준 고시합니다.","민간 반려동물 보험에 정부가 일부 보조금을 지원합니다."],
    impact: "반려가구 약 600만 가구의 진료비 예측 가능성 향상.",
    similar: [{title:"동물병원 진료비 사전 공시제 법안", date:"2026.03.02", stage:"위원회"}]
  },
  { id: "b5", span: "span-2", compact: true, ...PICKS[4],
    title: "기후 적응 도시계획 의무화법",
  },
  { id: "b6", span: "span-3", ...PICKS[3],
    title: "소상공인 카드 수수료 인하·단계 조정법",
  },
  { id: "b7", span: "span-3",
    title: "노인 대중교통 무료 이용 연령 단계적 조정법",
    cats: [{label:"복지", k:"welfare", accent:true}, {label:"교통", k:"safety"}],
    proposedAt: "2026.04.25", proposer: "윤○○ 의원 외 10인", stage: "committee",
    summary: ["지하철·버스 무료 이용 연령을 65세에서 점진적으로 70세로 조정합니다.","조정 시기에는 저소득 노인에게 교통비 바우처를 별도 지원합니다.","광역철도까지 무료 이용 범위를 확대합니다."],
    impact: "단기 재정 부담 완화와 함께 저소득 노인 보호 병행.",
    similar: [{title:"노인 교통비 바우처 지원법", date:"2026.03.06", stage:"위원회"}]
  },
  { id: "b8", span: "span-2", compact: true,
    title: "청소년 디지털 권리·알고리즘 투명성법",
    cats: [{label:"디지털", k:"digital", accent:true}, {label:"교육", k:"education"}],
    proposedAt: "2026.04.22", proposer: "장○○ 의원 외 9인", stage: "committee",
    summary: ["만 18세 미만 사용자에게는 추천 알고리즘을 끌 수 있는 기본값을 의무화합니다.","교육 기관에서의 생성형 AI 활용 가이드라인을 마련합니다."],
    impact: "주요 SNS·동영상 플랫폼 청소년 이용자 약 540만 명.",
    similar: [{title:"디지털 잊혀질 권리법", date:"2026.02.27", stage:"위원회"}]
  },
  { id: "b9", span: "span-2", compact: true,
    title: "공공장소 무료 와이파이 의무 설치법",
    cats: [{label:"디지털", k:"digital", accent:true}],
    proposedAt: "2026.04.20", proposer: "송○○ 의원 외 6인", stage: "proposed",
    summary: ["도서관·복지관·공원 등 공공시설에 무료 와이파이 설치를 의무화합니다.","보안 기준과 개인정보 처리 원칙을 함께 규정합니다."],
    impact: "전국 약 4.2만 개 공공시설 대상.", similar: []
  },
  { id: "b10", span: "span-2", compact: true,
    title: "1인 가구 응급 의료 안전망법",
    cats: [{label:"보건", k:"health", accent:true}, {label:"복지", k:"welfare"}],
    proposedAt: "2026.04.18", proposer: "신○○ 의원 외 8인", stage: "committee",
    summary: ["독거 1인 가구에 응급 호출 단말기와 정기 안부 점검을 제공합니다.","응급 시 가까운 의료기관과 자동 연계되도록 합니다."],
    impact: "전국 1인 가구 중 취약계층 약 110만 명.", similar: []
  },
];

export const WEEKLY = [
  { rank: 1, ref: "p1", title: "플랫폼 노동자 유급휴가·산재보험 보장법", cats: [{label:"노동", k:"labor", accent:true},{label:"복지", k:"welfare"}], snip: "4대 보험 의무화와 연 5일 유급 휴가를 단계 도입.", view: 128400, trend: "+42%" },
  { rank: 2, ref: "p2", title: "청년 월세 지원 확대 및 상한 인상법", cats: [{label:"주거", k:"housing", accent:true}], snip: "월 20만 원 → 30만 원, 지원 기간 24개월로 확대.", view: 96200, trend: "+18%" },
  { rank: 3, ref: "p3", title: "중·고등학교 무상급식 전면 확대법", cats: [{label:"교육", k:"education", accent:true}], snip: "전국 중·고생 270만 명 무상급식, 지역 농산물 30% 의무.", view: 71800, trend: "+11%" },
  { rank: 4, ref: "b3", title: "어린이 보행자 보호구역 확대법", cats: [{label:"생활안전", k:"safety", accent:true}], snip: "보호구역 300m 확대, 위반 과태료 2배 상향.", view: 54300, trend: "+7%" },
  { rank: 5, ref: "b4", title: "반려동물 진료비 표준화법", cats: [{label:"생활", k:"welfare", accent:true}], snip: "주요 진료비 표준 고시, 민간 보험 일부 보조.", view: 49100, trend: "-3%", down: true },
  { rank: 6, ref: "p4", title: "소상공인 카드 수수료 인하법", cats: [{label:"경제", k:"economy", accent:true}], snip: "연매출 3억 원 이하 소상공인 수수료 0.5%.", view: 42600, trend: "+22%" },
  { rank: 7, ref: "b7", title: "노인 대중교통 연령 조정법", cats: [{label:"복지", k:"welfare", accent:true}], snip: "65세 → 70세 점진 조정, 저소득 노인 바우처.", view: 38100, trend: "+5%" },
  { rank: 8, ref: "b8", title: "청소년 디지털 권리법", cats: [{label:"디지털", k:"digital", accent:true}], snip: "추천 알고리즘 OFF 기본값 의무화.", view: 31900, trend: "+14%" },
  { rank: 9, ref: "p5", title: "기후 적응 도시계획 의무화법", cats: [{label:"환경", k:"env", accent:true}], snip: "30만 명 이상 도시 적응 계획 의무 수립.", view: 28400, trend: "+9%" },
  { rank: 10, ref: "b10", title: "1인 가구 응급 의료 안전망법", cats: [{label:"보건", k:"health", accent:true}], snip: "독거 1인 가구 응급 호출·안부 점검 도입.", view: 24800, trend: "-1%", down: true },
];

