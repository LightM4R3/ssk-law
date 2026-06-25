export const CATEGORY_META = {
  labor: { glyph: "勞", sub: "Labor", hue: 22, blurb: "일하는 사람의 권리·안전망" },
  welfare: { glyph: "福", sub: "Welfare", hue: 145, blurb: "돌봄·소득·복지 안전망" },
  housing: { glyph: "宅", sub: "Housing", hue: 285, blurb: "월세·전세·청년 주거 안정" },
  economy: { glyph: "經", sub: "Economy", hue: 60, blurb: "소상공인·금융·세제" },
  education: { glyph: "敎", sub: "Education", hue: 200, blurb: "학교·청소년·평생교육" },
  env: { glyph: "綠", sub: "Climate", hue: 165, blurb: "기후·자원순환·도시 적응" },
  digital: { glyph: "디", sub: "Digital", hue: 245, blurb: "플랫폼·AI·개인정보" },
  health: { glyph: "醫", sub: "Health", hue: 0, blurb: "의료·공공보건·돌봄" },
  safety: { glyph: "安", sub: "Safety", hue: 35, blurb: "교통·재난·생활안전" },
};

export const STAGES = {
  proposed: { label: "발의", cls: "s1", idx: 0 },
  committee: { label: "위원회 심사", cls: "s2", idx: 1 },
  plenary: { label: "본회의 상정", cls: "s3", idx: 2 },
  passed: { label: "통과 · 공포", cls: "s4", idx: 3 },
};
