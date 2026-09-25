from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="customer",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer"
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer"
    )

    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="customer"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    warranty_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="product"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="processing",
    )

    order_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    expected_delivery: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    customer: Mapped["User"] = relationship(
        back_populates="orders"
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    order: Mapped["Order"] = relationship(
        back_populates="items"
    )

    product: Mapped["Product"] = relationship(
        back_populates="order_items"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    customer: Mapped["User"] = relationship(
        back_populates="conversations"
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    agent_logs: Mapped[list["AgentLog"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )

    sender: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    subject: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="medium",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
    )

    assigned_to: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Time when a support agent takes ownership of the case.
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Time when the case was escalated from AI support
    # to human support.
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Time of the most recent customer/agent message.
    # This will be useful for live support activity.
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    customer: Mapped["User"] = relationship(
        back_populates="support_tickets"
    )


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )

    iteration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    intent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tool_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tool_input: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    tool_output: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    latency_ms: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="success",
    )

    escalated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="agent_logs"
    )