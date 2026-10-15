export default function formatDateTime(value) {
  if (
    value == null ||
    (typeof value === "string" && /^(none|null)?$/i.test(value.trim()))
  ) {
    return "정보 없음";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "정보 없음"
    : date.toLocaleString("ko-KR");
}
