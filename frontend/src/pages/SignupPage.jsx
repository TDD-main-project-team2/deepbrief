import "./SignupPage.css";

import AuthLayout from "../components/auth/AuthLayout.jsx";
import AuthInput from "../components/auth/AuthInput.jsx";
import PasswordInput from "../components/auth/PasswordInput.jsx";

import useAuthValidation, {
  validateEmail,
  validateNickname,
  validateSignupPassword,
  validateConfirmation,
} from "../hooks/useAuthValidation.js";

const validators = {
  nickname: validateNickname,
  email: validateEmail,
  password: validateSignupPassword,
  confirmPassword: validateConfirmation,
};

export default function SignupPage() {
  const { field, canSubmit } = useAuthValidation(validators, {
    nickname: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  function submit(event) {
    event.preventDefault();

    if (!canSubmit) return;
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

        <button
          className="primary signup-submit"
          type="submit"
          disabled={!canSubmit}
        >
          회원가입
        </button>
      </form>
    </AuthLayout>
  );
}
