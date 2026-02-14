"""
SQLAlchemy модели.
Используем async-friendly подход.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    GUEST = "guest"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.GUEST)
    inviter_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    referral_code = relationship("ReferralCode", back_populates="user", uselist=False)
    leads = relationship("Lead", back_populates="user")
    bookings = relationship("Booking", back_populates="user")


class Apartment(Base):
    __tablename__ = "apartments"
    __table_args__ = (
        Index("ix_apartments_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    district = Column(String(100), nullable=True)
    address_short = Column(String(255), nullable=True)
    guests_max = Column(Integer, nullable=False, default=2)
    beds_text = Column(String(100), nullable=True)
    features_json = Column(JSON, nullable=True)  # ["wifi", "ac", "kitchen", ...]
    rules_short = Column(Text, nullable=True)
    map_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    media = relationship("ApartmentMedia", back_populates="apartment", cascade="all, delete-orphan")
    tags = relationship("ApartmentTag", back_populates="apartment", cascade="all, delete-orphan")
    channel_posts = relationship("ChannelPost", back_populates="apartment", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="apartment")


class ApartmentMedia(Base):
    __tablename__ = "apartment_media"
    __table_args__ = (
        Index("ix_apartment_media_apartment_id", "apartment_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    type = Column(String(20), nullable=False)  # "photo" или "video"
    url = Column(String(500), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    apartment = relationship("Apartment", back_populates="media")


class ApartmentTag(Base):
    __tablename__ = "apartment_tags"
    __table_args__ = (
        Index("ix_apartment_tags_apartment_id", "apartment_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=False)
    tag = Column(String(50), nullable=False)  # "park", "center", "business", "family"

    apartment = relationship("Apartment", back_populates="tags")


class ChannelPostKind(str, enum.Enum):
    APARTMENT = "apartment"
    CATALOG = "catalog"
    MENU = "menu"
    FAQ = "faq"
    HOT = "hot"


class ChannelPost(Base):
    __tablename__ = "channel_posts"
    __table_args__ = (
        Index("ix_channel_posts_apartment_id", "apartment_id"),
        Index("ix_channel_posts_kind", "kind"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)
    kind = Column(SAEnum(ChannelPostKind, name="channel_post_kind"), nullable=False)
    channel_id = Column(String(50), nullable=False)  # @channel или -100...
    message_id = Column(Integer, nullable=True)
    last_published_at = Column(DateTime, nullable=True)
    content_hash = Column(String(64), nullable=True)  # sha256
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    apartment = relationship("Apartment", back_populates="channel_posts")


class LeadStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    SPAM = "spam"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_user_id", "user_id"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    contact = Column(String(255), nullable=True)  # phone/email/username
    date_from = Column(String(10), nullable=True)  # YYYY-MM-DD
    date_to = Column(String(10), nullable=True)
    guests = Column(Integer, nullable=True)
    district = Column(String(100), nullable=True)
    budget_min = Column(Integer, nullable=True)
    budget_max = Column(Integer, nullable=True)
    status = Column(SAEnum(LeadStatus, name="lead_status"), nullable=False, default=LeadStatus.NEW)
    source_tag = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="leads")


class BookingStatus(str, enum.Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    PAID = "paid"
    CANCELED = "canceled"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_bookings_external_id"),
        Index("ix_bookings_apartment_id", "apartment_id"),
        Index("ix_bookings_user_id", "user_id"),
        Index("ix_bookings_status", "status"),
        Index("ix_bookings_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=False)  # от модуля бронирования
    status = Column(SAEnum(BookingStatus, name="booking_status"), nullable=False, default=BookingStatus.CREATED)
    apartment_id = Column(Integer, ForeignKey("apartments.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    check_in = Column(String(10), nullable=True)  # YYYY-MM-DD
    check_out = Column(String(10), nullable=True)
    total_amount = Column(Integer, nullable=True)
    currency = Column(String(3), nullable=False, default="RUB")
    source_tag = Column(String(100), nullable=True)
    raw_payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    apartment = relationship("Apartment", back_populates="bookings")
    user = relationship("User", back_populates="bookings")


class ReferralCode(Base):
    __tablename__ = "referral_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_referral_codes_code"),
        Index("ix_referral_codes_user_id", "user_id"),
        Index("ix_referral_codes_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    code = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="referral_code")
    events = relationship("ReferralEvent", back_populates="referral_code", cascade="all, delete-orphan")


class ReferralEventType(str, enum.Enum):
    START = "start"
    CLICK = "click"
    BOOKING_CREATED = "booking_created"
    BOOKING_PAID = "booking_paid"


class ReferralEvent(Base):
    __tablename__ = "referral_events"
    __table_args__ = (
        Index("ix_referral_events_referral_code_id", "referral_code_id"),
        Index("ix_referral_events_type", "type"),
        Index("ix_referral_events_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    referral_code_id = Column(Integer, ForeignKey("referral_codes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(SAEnum(ReferralEventType, name="referral_event_type"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    meta_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    referral_code = relationship("ReferralCode", back_populates="events")


class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"


class Payout(Base):
    __tablename__ = "payouts"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_payouts_booking_id"),
        Index("ix_payouts_referral_code_id", "referral_code_id"),
        Index("ix_payouts_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    referral_code_id = Column(Integer, ForeignKey("referral_codes.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # в копейках
    status = Column(SAEnum(PayoutStatus, name="payout_status"), nullable=False, default=PayoutStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    referral_code = relationship("ReferralCode")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_provider", "provider"),
        Index("ix_webhook_events_event_id", "event_id"),
        Index("ix_webhook_events_received_at", "received_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)  # "homereserve", "booking.com", etc
    event_id = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)  # "booking.created", "payment.received", etc
    payload_hash = Column(String(64), nullable=False)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    raw_payload_json = Column(JSON, nullable=True)
