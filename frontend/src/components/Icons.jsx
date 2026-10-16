export default function Icons({ type = "file" }) {
  const paths = {
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

