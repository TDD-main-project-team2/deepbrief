import { useEffect, useId, useRef, useState } from "react";
import Icons from "./Icons.jsx";
import "./Select.css";

export default function Select({ label, value, onChange, options }) {
  const id = useId();
  const root = useRef(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const selectedIndex = Math.max(0, options.findIndex((option) => option.value === value));

  useEffect(() => {
    if (!open) return;
    function closeOutside(event) {
      if (!root.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [open]);

  function choose(index) {
    onChange(options[index].value);
    setOpen(false);
  }

  function handleKeyDown(event) {
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => {
        if (event.key === "Home") return 0;
        if (event.key === "End") return options.length - 1;
        if (!open) return selectedIndex;
        return (current + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length;
      });
    } else if (open && ["Enter", " "].includes(event.key)) {
      event.preventDefault();
      choose(activeIndex);
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      setOpen(false);
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  return (
    <div className="select-field" ref={root} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
      <span id={`${id}-label`} className="select-label">{label}</span>
      <button
        type="button"
        className="select-trigger"
        role="combobox"
        aria-labelledby={`${id}-label ${id}-value`}
        aria-expanded={open}
        aria-controls={`${id}-options`}
        aria-haspopup="listbox"
        aria-activedescendant={open ? `${id}-option-${activeIndex}` : undefined}
        onKeyDown={handleKeyDown}
        onClick={() => {
          setActiveIndex(selectedIndex);
          setOpen((current) => !current);
        }}
      >
        <span id={`${id}-value`}>{options[selectedIndex].label}</span>
        <Icons type="chevronDown" />
      </button>
      {open && (
        <div className="select-options" id={`${id}-options`} role="listbox" aria-labelledby={`${id}-label`}>
          {options.map((option, index) => (
            <div
              key={option.value}
              id={`${id}-option-${index}`}
              role="option"
              aria-selected={option.value === value}
              className={`select-option ${index === activeIndex ? "is-active" : ""}`}
              onPointerMove={() => setActiveIndex(index)}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(index)}
            >
              {option.label}
              {option.value === value && <Icons type="check" />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
