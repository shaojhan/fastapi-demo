from app.db import Base

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Uuid,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
    func,
    Enum as SqlEnum,
)
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)

from enum import Enum

if TYPE_CHECKING:
    from .user import User


class SSOProtocol(str, Enum):
    SAML = "SAML"
    OIDC = "OIDC"


class SSOProvider(Base):
    """
    SSO Provider ORM 模型
    儲存 SAML / OIDC IdP 設定
    """
    __tablename__ = "sso_providers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    # 基本資訊
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    protocol: Mapped[SSOProtocol] = mapped_column(SqlEnum(SSOProtocol), nullable=False)

    # SAML 欄位
    idp_entity_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    idp_sso_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    idp_slo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    idp_x509_cert: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sp_entity_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sp_acs_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # OIDC 欄位
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authorization_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    token_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    userinfo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    jwks_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, default="openid email profile")

    # 共用設定
    attribute_mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default='0')

    # 關聯
    user_links: Mapped[list["SSOUserLink"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_sso_providers_slug", "slug"),
        Index("ix_sso_providers_is_active", "is_active"),
    )


class SSOConfig(Base):
    """
    SSO 全域設定（Singleton, id=1）
    控制是否強制 SSO、是否自動建帳號等
    """
    __tablename__ = "sso_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    auto_create_users: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    enforce_sso: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    default_role: Mapped[str] = mapped_column(String(32), default="NORMAL", server_default="NORMAL")


class SSOUserLink(Base):
    """
    SSO 使用者連結
    記錄使用者與 SSO Provider 的對應關係
    """
    __tablename__ = "sso_user_links"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("sso_providers.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)

    # 關聯
    user: Mapped["User"] = relationship("User", lazy="selectin")
    provider: Mapped["SSOProvider"] = relationship(back_populates="user_links")

    __table_args__ = (
        UniqueConstraint("provider_id", "external_id", name="uq_provider_external_id"),
        Index("ix_sso_user_links_user_id", "user_id"),
        Index("ix_sso_user_links_provider_id", "provider_id"),
    )
