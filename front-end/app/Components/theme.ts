// ── GenResearch Design Tokens ─────────────────────────────────
// Shared color palette used across all dashboard sub-pages.

export const C = {
  cream: "#f5f0e8",
  creamLight: "#faf8f2",
  creamDark: "#efe8d8",
  parchment: "#e8dfc8",
  inkDark: "#2c1f0e",
  inkMid: "#5a3e20",
  inkLight: "#7a6040",
  inkFaint: "rgba(80,60,30,0.45)",
  gold: "#8b6914",
  goldLight: "#c8971e",
  goldFaint: "rgba(139,105,20,0.10)",
  sienna: "#a0522d",
  siennaFaint: "rgba(160,82,45,0.10)",
  umber: "#6b5c38",
  white: "#fffef9",
  border: "rgba(180,160,120,0.22)",
  borderGold: "rgba(139,105,20,0.30)",
  shadow: "rgba(120,100,60,0.10)",
  shadowMd: "rgba(120,100,60,0.18)",
  green: "#5a8a3c",
  greenFaint: "rgba(90,138,60,0.10)",
  red: "#a0352d",
  redFaint: "rgba(160,53,45,0.10)",
  blue: "#2c5f8a",
  blueFaint: "rgba(44,95,138,0.10)",
} as const;

// ── Shared inline-style helpers ──────────────────────────────
export const sectionLabel: React.CSSProperties = {
  fontFamily: "'Crimson Pro', Georgia, serif",
  fontSize: 11,
  fontWeight: 600,
  color: C.gold,
  letterSpacing: "0.15em",
  textTransform: "uppercase",
};

export const headingStyle: React.CSSProperties = {
  fontFamily: "'Playfair Display', serif",
  fontWeight: 900,
  color: C.inkDark,
  letterSpacing: "-0.02em",
  lineHeight: 1.1,
};

export const bodyText: React.CSSProperties = {
  fontFamily: "'Crimson Pro', Georgia, serif",
  color: C.inkLight,
  lineHeight: 1.65,
};

export const cardBase: React.CSSProperties = {
  background: C.creamLight,
  border: `1px solid ${C.border}`,
  borderRadius: 4,
  transition: "all .3s",
};
