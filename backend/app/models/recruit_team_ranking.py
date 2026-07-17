from sqlalchemy import Integer, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Recruit247TeamRanking(Base):
    """Team recruiting-class rankings sourced directly from 247Sports.com —
    a manual snapshot (247 has no public API), pasted in by the user and
    fetched via WebFetch on request. Not auto-refreshed; `fetched_at` marks
    when it was last pulled, and it needs to be redone against fresh links
    to stay current."""

    __tablename__ = "recruit_247_team_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_year: Mapped[int] = mapped_column(Integer, index=True)
    rank: Mapped[int] = mapped_column(Integer)
    school: Mapped[str] = mapped_column(String(100), index=True)
    commits: Mapped[int | None] = mapped_column(Integer)
    avg_rating: Mapped[float | None] = mapped_column(Float)
    points: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[DateTime] = mapped_column(DateTime)
