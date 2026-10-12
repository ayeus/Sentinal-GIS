import { getRiskColor, RISK_COLORS, NO_DATA_COLOR, SPREAD_COLORS, formatPercent, formatDate } from "./config";

test("each risk level has its own color", () => {
  expect(getRiskColor("High")).toBe(RISK_COLORS.High);
  expect(getRiskColor("Medium")).toBe(RISK_COLORS.Medium);
  expect(getRiskColor("Low")).toBe(RISK_COLORS.Low);
  expect(new Set(Object.values(RISK_COLORS)).size).toBe(Object.keys(RISK_COLORS).length);
});

test("unknown or missing risk falls back to the no-data color", () => {
  expect(getRiskColor(undefined)).toBe(NO_DATA_COLOR);
  expect(getRiskColor("None")).toBe(NO_DATA_COLOR);
});

test("spread colors come from the shared risk palette", () => {
  Object.entries(SPREAD_COLORS).forEach(([risk, color]) => {
    expect(RISK_COLORS[risk]).toBe(color);
  });
});

test("formatters handle missing values", () => {
  expect(formatPercent(0.342)).toBe("34%");
  expect(formatPercent(0.0142, 1)).toBe("1.4%");
  expect(formatPercent(null)).toBe("–");
  expect(formatDate("")).toBe("");
  expect(formatDate("2026-02-22")).toMatch(/2026/);
});
