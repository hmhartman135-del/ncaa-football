from sqlalchemy import Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class TransferPortalEntry(Base):
    __tablename__ = "transfer_portal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cfbd_id: Mapped[int | None] = mapped_column(Integer, index=True)
    player_name: Mapped[str] = mapped_column(String(150), index=True)
    position: Mapped[str | None] = mapped_column(String(10))
    from_school: Mapped[str | None] = mapped_column(String(100))
    to_school: Mapped[str | None] = mapped_column(String(100))
    season: Mapped[int] = mapped_column(Integer, index=True)  # portal cycle year, e.g. 2027
    year_in_school: Mapped[str | None] = mapped_column(String(30))  # Freshman/Sophomore/Junior/Senior, derived from our roster data — CFBD's portal endpoint doesn't expose class year directly
    eligibility_status: Mapped[str | None] = mapped_column(String(30))  # CFBD's own field: Immediate/Withdrawn/TBD/PendingAppeal — whether they can play right away, NOT a class year
    stars: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[float | None] = mapped_column(Float)
    committed: Mapped[bool] = mapped_column(Boolean, default=False)
    entered_date: Mapped[DateTime | None] = mapped_column(DateTime)
    committed_date: Mapped[DateTime | None] = mapped_column(DateTime)

    player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("players.id"), nullable=True)

    # AI analysis
    overall_grade: Mapped[int | None] = mapped_column(Integer)  # 0-100
    ai_analysis: Mapped[str | None] = mapped_column(String(4000))
