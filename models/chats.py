# models/offline_messages.py
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, BigInteger, ForeignKey, Enum as SAEnum
from typing import Optional
from datetime import datetime, timezone

class E2EEPublicKey(SQLModel, table=True):
    __tablename__ = "e2ee_public_keys"

    user_id:              int      = Field(
                                        sa_column=Column(
                                            BigInteger,
                                            ForeignKey("users.user_id", ondelete="CASCADE"),
                                            primary_key=True,
                                            nullable=False,
                                        )
                                    )
    encrypted_public_key: str      = Field()
    key_version:          int      = Field()
    created_at:           datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:           datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class ChatInfo(SQLModel, table=True):
    __tablename__ = "chat_info"
 
    id:          Optional[int] = Field(primary_key=True)
    user_id:     int           = Field(
                                     sa_column=Column(
                                         BigInteger,
                                         ForeignKey("users.user_id", ondelete="CASCADE"),
                                         unique=True,
                                         nullable=False,
                                     )
                                 )
    socket_id:   Optional[str] = Field(default=None)
    online:      Optional[int] = Field(default=0)
    last_active: Optional[datetime] = Field(default=None)
    created_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

class OfflineMessage(SQLModel, table=True):
    __tablename__ = "offline_messages"

    id:             Optional[int] = Field(primary_key=True)
    sender_id:      int           = Field(sa_column=Column(BigInteger, nullable=False))
    chat_info_id:   int           = Field(sa_column=Column(BigInteger, ForeignKey("chat_info.user_id", ondelete="CASCADE"), nullable=False, index=True))
    type:           str           = Field(max_length=50)
    category:       str           = Field(max_length=50)
    message_id:     str           = Field(max_length=255)
    message_body:   str           = Field()
    media_metadata: Optional[str] = Field(default=None)
    reply_id:       str           = Field(max_length=255)
    status:         str           = Field(
                                        sa_column=Column(
                                            SAEnum("PENDING", "DELIVERED", name="offline_message_status"),
                                            nullable=False,
                                            default="PENDING"
                                        )
                                    )
    created_at:     datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:     datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))