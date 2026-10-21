export default function Icons({ type = "file" }) {
  const paths = {
    users:
      "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M16 3a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
    clipboardCheck: "M9 5H5v16h14V5h-4 M9 3h6v4H9z M8 14l3 3 5-6",
    newspaper: "M4 3h16v18H4z M8 7h8 M8 11h3v4H8z M14 11h2 M14 15h2 M8 18h8",
    settings:
      "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M9 2h6l.5 3 2 1 2.5-1 3 5-2.5 2v2L23 16l-3 5-2.5-1-2 1-.5 2H9l-.5-2-2-1L4 21l-3-5 2.5-2v-2L1 10l3-5 2.5 1 2-1z",
    close: "M6 6l12 12 M6 18L18 6",
    minus: "M5 12h14",
    trash: "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7",
    chevronDown: "M6 9l6 6 6-6",
    chevronRight: "M9 6l6 6-6 6",
    file: "M14 3H5v18h14V8z M14 3v5h5 M8 12h8 M8 16h6",
    upload: "M12 16V3 M7 8l5-5 5 5 M4 16v5h16v-5",
    plus: "M12 5v14 M5 12h14",
    chat: "M21 11a9 9 0 0 1-9 9H4l-2 2v-10a9 9 0 1 1 19-1z",
    arrow: "M12 20V4 M6 10l6-6 6 6",
    spark: "M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z",
  };

  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[type] || paths.file} />
    </svg>
  );
}
