"""메시지 데이터 조회 Repository."""

from sqlalchemy import select

from backend.database.rdb.rdb import SessionLocal
from backend.models.message import Message


def find_messages_by_conversation_id(
    conversation_id: int,
) -> list[Message]:
    """대화 ID로 메시지 목록을 오래된 순서대로 조회한다."""
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id.asc())
            ).all()
        )


def find_message_by_id(message_id: int) -> Message | None:
    """메시지 ID로 메시지를 조회한다."""
    with SessionLocal() as db:
        return db.get(Message, message_id)


def find_recent_by_conversation(
    conversation_id: int,
    limit: int = 10,
) -> list[Message]:
    """대화의 최근 메시지를 조회해 오래된 순서대로 반환한다."""
    if limit < 1:
        raise ValueError("limit은 1 이상이어야 한다.")

    with SessionLocal() as db:
        messages = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id.desc())
                .limit(limit)
            ).all()
        )

        return list(reversed(messages))


def create_message(
    conversation_id: int,
    content: str,
    role: str,
) -> Message:
    """대화에 메시지를 생성한다."""
    with SessionLocal() as db:
        message = Message(
            conversation_id=conversation_id,
            content=content,
            role=role,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message


def delete_message(message_id: int) -> None:
    """메시지를 삭제한다."""
    with SessionLocal() as db:
        message = db.get(Message, message_id)
        if message is not None:
            db.delete(message)
            db.commit()