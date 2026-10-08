"""
비밀번호를 해싱하고 검증한다.
알고리즘: argon2id
"""
import threading

from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError

MAX_PASSWORD_LENGTH = 128                    # 아주 긴 입력으로 연산을 잡아먹는 요청을 막는다
MAX_CONCURRENT = 4                           # 동시에 돌리는 해싱 수

_hasher = PasswordHash.recommended()
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)


class PasswordTooLongError(ValueError):
    """비밀번호가 최대 길이를 넘었다."""


def hash_password(password: str) -> str:
    """비밀번호의 해시 문자열을 만든다. DB에는 이 값만 저장한다."""
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordTooLongError(f"비밀번호는 {MAX_PASSWORD_LENGTH}자 이하여야 합니다.")

    with _slots:
        return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호가 저장된 해시와 맞는지 확인한다."""
    if len(password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        with _slots:
            return _hasher.verify(password, password_hash)
    except PwdlibError:
        return False
