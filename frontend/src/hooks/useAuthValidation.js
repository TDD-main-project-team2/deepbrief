import { useState } from "react";

export const validateEmail = (value) =>
  !value.trim()
    ? "이메일을 입력해주세요."
    : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
      ? ""
      : "올바른 이메일 형식을 입력해주세요.";

export const validateLoginPassword = (value) =>
  value.trim() ? "" : "비밀번호를 입력해주세요.";

export const validateSignupPassword = (value) =>
  !value.trim()
    ? "비밀번호를 입력해주세요."
    : value.length < 8
      ? "비밀번호는 8자 이상 입력해주세요."
      : "";

export const validateNickname = (value) =>
  !value.trim()
    ? "닉네임을 입력해주세요."
    : value.trim().length < 2 || value.length > 30
      ? "닉네임은 2~30자로 입력해주세요."
      : "";

export const validateConfirmation = (value, values) =>
  !value.trim()
    ? "비밀번호 확인을 입력해주세요."
    : value !== values.password
      ? "비밀번호가 일치하지 않습니다."
      : "";

export const validateOrganizationCode = (value) =>
  !value.trim()
    ? "조직 코드를 입력해주세요."
    : value.length > 50
      ? "조직 코드는 50자 이하로 입력해주세요."
      : "";

export default function useAuthValidation(validators, initialValues) {
  const [values, setValues] = useState(initialValues);
  const [touched, setTouched] = useState({});

  const errors = Object.fromEntries(
    Object.keys(validators).map((name) => [
      name,
      validators[name](values[name], values),
    ]),
  );

  const canSubmit = Object.values(errors).every((error) => !error);

  function field(name) {
    return {
      name,
      value: values[name],
      onChange: (event) =>
        setValues((current) => ({ ...current, [name]: event.target.value })),
      onBlur: () => setTouched((current) => ({ ...current, [name]: true })),
      error: touched[name] ? errors[name] : "",
    };
  }

  return { values, field, canSubmit };
}
