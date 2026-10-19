import { useState } from "react";
import { useNavigate } from "react-router";

import "./LoginPage.css";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import AuthInput from "../components/auth/AuthInput.jsx";
import PasswordInput from "../components/auth/PasswordInput.jsx";
import AuthError from "../components/auth/AuthError.jsx";

import useAuthValidation, {
  validateEmail,
  validateLoginPassword,
} from "../hooks/useAuthValidation.js";
import { loginUser } from "../api/auth.js";

const validators = { email: validateEmail, password: validateLoginPassword };

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { values, field, canSubmit } = useAuthValidation(validators, {
    email: import.meta.env.DEV ? "example@test.com" : "",
    password: import.meta.env.DEV ? "12345678" : "",
  });

  async function submit(event) {
    event.preventDefault();
    if (!canSubmit || submitting) return;

    setSubmitting(true);
    setError("");

    try {
      const session = await loginUser({
        email: values.email.trim(),
        password: values.password,
      });
      onLogin(session);
      navigate("/", { replace: true });
    } catch (error) {
      const detail = error.response?.data?.detail;
      setError(
        typeof detail === "string" ? detail : "로그인에 실패했습니다. 잠시 후 다시 시도해주세요.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="로그인"
      headingCaption="WELCOME BACK"
      authLinkText="처음 이용하시나요?"
      authLinkLabel="회원가입"
      authLinkPath="/signup"
    >
      <form className="login-form" onSubmit={submit} onChange={() => setError("")} noValidate>
        <AuthInput
          label="이메일"
          {...field("email")}
          type="email"
          autoComplete="email"
          placeholder="example@example.com"
          required
        />

        <PasswordInput
          {...field("password")}
          autoComplete="current-password"
          placeholder="비밀번호를 입력하세요"
          required
        />
        <AuthError variant="form">{error}</AuthError>

        <button className="primary login-submit" type="submit" disabled={!canSubmit || submitting}>
          {submitting ? "로그인 중..." : "로그인"}
        </button>
      </form>
    </AuthLayout>
  );
}
