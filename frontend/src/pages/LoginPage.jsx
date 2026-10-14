import { useState } from "react";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import AuthInput from "../components/auth/AuthInput.jsx";
import PasswordInput from "../components/auth/PasswordInput.jsx";

import useAuthValidation, {
  validateEmail,
  validateLoginPassword,
} from "../hooks/useAuthValidation.js";

const validators = { email: validateEmail, password: validateLoginPassword };

export default function LoginPage() {
  const [feedback, setFeedback] = useState("");
  const { field, canSubmit } = useAuthValidation(validators, {
    email: "",
    password: "",
  });

  function submit(event) {
    event.preventDefault();

    if (!canSubmit) return;
  }

  return (
    <AuthLayout
      title="로그인"
      headingCaption="WELCOME BACK"
      authLinkText="처음 이용하시나요?"
      authLinkLabel="회원가입"
      authLinkPath="/signup"
    >
      <form onSubmit={submit} onChange={() => setFeedback("")} noValidate>
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
        {feedback && (
          <p className="auth-feedback" role="status">
            {feedback}
          </p>
        )}

        <button
          className="primary auth-submit"
          type="submit"
          disabled={!canSubmit}
        >
          로그인
        </button>
      </form>
    </AuthLayout>
  );
}
