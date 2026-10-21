import "./LoadingDots.css";

export default function LoadingDots({ children = "" }) {
  return (
    <span>
      {children.replace(/\s*(?:\.{3}|…)$/, "")}
      <span className="loading-dots" aria-hidden="true">
        <span>.</span>
        <span>.</span>
        <span>.</span>
      </span>
    </span>
  );
}
