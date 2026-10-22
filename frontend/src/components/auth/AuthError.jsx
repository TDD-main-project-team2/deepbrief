import Icons from "../common/Icons.jsx";
import "./AuthError.css";

export default function AuthError({ children, id, variant = "field" }) {
  if (!children) return null;

  return (
    <span id={id} className={`auth-error auth-error--${variant}`} role="alert">
      <Icons type="alert" />
      <span>{children}</span>
    </span>
  );
}
