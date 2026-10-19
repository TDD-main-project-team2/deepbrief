"""대화 데이터 조회 Repository."""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from backend.database.rdb.rdb import SessionLocal
from backend.models.conversation import Conversation
from backend.models.message import Message


def find_all_by_user(user_id: int) -> list[Conversation]:
    """사용자 ID로 대화 목록을 조회한다."""
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.id.asc())
            ).all()
        )


def find_conversation_by_id(
    conversation_id: int,
) -> Conversation | None:
    """대화 ID로 대화를 조회한다."""
    with SessionLocal() as db:
        return db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id
            )
        )


def delete_conversation(conversation_id: int) -> None:
    """대화와 해당 대화의 메시지를 함께 삭제한다."""
    with SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)

        if conversation is None:
            return

        db.execute(
            delete(Message).where(
                Message.conversation_id == conversation_id
            )
        )

        db.delete(conversation)
        db.commit()


def create_conversation(
    title: str,
    user_id: int,
    article_id: int,
) -> Conversation:
    """새 대화를 생성하거나 같은 사용자·기사의 기존 대화를 반환한다."""
    with SessionLocal() as db:
        conversation = Conversation(
            title=title,
            user_id=user_id,
            article_id=article_id,
        )
        db.add(conversation)
        
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()

            diagnostic = getattr(exc.orig, "diag", None)
            if getattr(diagnostic, "constraint_name", None) != "uq_conversations_user_article":
                raise
            
            return db.scalars(
                select(Conversation).where(
                    Conversation.user_id == user_id,
                    Conversation.article_id == article_id,
                )
            ).one()
        
        db.refresh(conversation)

        return conversation
