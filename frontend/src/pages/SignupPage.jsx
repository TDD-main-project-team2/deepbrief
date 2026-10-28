import { useState } from "react";
import { useNavigate } from "react-router";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import AuthInput from "../components/auth/AuthInput.jsx";
import PasswordInput from "../components/auth/PasswordInput.jsx";
import AuthError from "../components/auth/AuthError.jsx";
import LoadingDots from "../components/common/feedback/LoadingDots.jsx";
import "./SignupPage.css";

import useAuthValidation, {
  validateEmail,
  validateOrganizationCode,
  validateNickname,
  validateSignupPassword,
  validateConfirmation,
} from "../hooks/useAuthValidation.js";
import { signupUser } from "../api/auth.js";

const validators = {
  organizationCode: validateOrganizationCode,
  nickname: validateNickname,
  email: validateEmail,
  password: validateSignupPassword,
  confirmPassword: validateConfirmation,
};

export default function SignupPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { values, field, canSubmit } = useAuthValidation(validators, {
    organizationCode: "",
    adminCode: "",
    nickname: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  async function submit(event) {
    event.preventDefault();
    if (!canSubmit || submitting) return;

    setSubmitting(true);
    setError("");

    try {
      await signupUser({
        organizationCode: values.organizationCode.trim(),
        adminCode: values.adminCode,
        email: values.email.trim(),
        password: values.password,
        nickname: values.nickname.trim(),
      });
      navigate("/login");
    } catch (error) {
      const detail = error.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "회원가입에 실패했습니다. 입력 내용을 확인하고 다시 시도해주세요.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="회원가입"
      headingCaption="JOIN DEEPBRIEF"
      authLinkText="이미 계정이 있나요?"
      authLinkLabel="로그인"
      authLinkPath="/login"
    >
      <form className="signup-form" onSubmit={submit} noValidate>
        <AuthInput
          label="닉네임"
          {...field("nickname")}
          autoComplete="nickname"
          placeholder="사용할 닉네임을 입력하세요"
          required
          minLength={2}
          maxLength={30}
        />

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
          autoComplete="new-password"
          placeholder="8자 이상 입력하세요"
          required
          minLength={8}
        />

        <PasswordInput
          label="비밀번호 확인"
          {...field("confirmPassword")}
          autoComplete="new-password"
          placeholder="비밀번호를 다시 입력하세요"
          required
        />

        <AuthInput
          label="조직 코드"
          {...field("organizationCode")}
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="소속 조직에서 받은 코드를 입력하세요"
          required
          maxLength={50}
        />

        <AuthInput
          label="관리자 코드 (선택)"
          {...field("adminCode")}
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="관리자라면 관리자 코드를 입력하세요"
          maxLength={50}
        />

        <AuthError variant="form">{error}</AuthError>

        <button className="primary signup-submit" type="submit" disabled={!canSubmit || submitting}>
          {submitting ? <LoadingDots>가입 중</LoadingDots> : "회원가입"}
        </button>
      </form>
    </AuthLayout>
  );
}
