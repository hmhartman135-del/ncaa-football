from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class DraftProspect(Base):
    __tablename__ = "draft_prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    position: Mapped[str | None] = mapped_column(String(10))
    college: Mapped[str | None] = mapped_column(String(100))
    class_year: Mapped[str | None] = mapped_column(String(10))  # Junior/Senior/Grad
    draft_year: Mapped[int] = mapped_column(Integer, index=True, default=2027)

    projected_round: Mapped[int | None] = mapped_column(Integer)
    grade: Mapped[str | None] = mapped_column(String(5))  # letter grade
    nfl_comparison: Mapped[str | None] = mapped_column(String(150))
    ai_analysis: Mapped[str | None] = mapped_column(String(4000))
