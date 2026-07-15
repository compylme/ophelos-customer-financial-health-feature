import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Direction(enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    snapshots: Mapped[list["MonthlySnapshot"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class MonthlySnapshot(TimestampMixin, Base):
    __tablename__ = "monthly_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_monthly_snapshots_user_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    period: Mapped[date] = mapped_column(nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="snapshots")
    financial_items: Mapped[list["FinancialItem"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )
    assessment: Mapped["MonthlyAssessment | None"] = relationship(
        back_populates="snapshot",
        uselist=False,
        cascade="all, delete-orphan",
    )


class FinancialItem(TimestampMixin, Base):
    __tablename__ = "financial_items"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_financial_items_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monthly_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[Direction] = mapped_column(
        Enum(Direction, name="direction", create_type=True),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    snapshot: Mapped["MonthlySnapshot"] = relationship(back_populates="financial_items")


class MonthlyAssessment(TimestampMixin, Base):
    __tablename__ = "monthly_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monthly_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_expenditure: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    disposable_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    assessment: Mapped[str] = mapped_column(String, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    snapshot: Mapped["MonthlySnapshot"] = relationship(back_populates="assessment")
