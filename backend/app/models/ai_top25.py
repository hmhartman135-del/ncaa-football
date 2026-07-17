from sqlalchemy import Integer, DateTime, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class AiTop25Ranking(Base):
    """A generated-on-request AI Top 25, independent of the real AP poll.
    Cached (not auto-regenerated) — a new row is only added when the user
    explicitly asks for a refresh, so `generated_at` marks when the
    snapshot's view of the season was taken."""

    __tablename__ = "ai_top25_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    generated_at: Mapped[DateTime] = mapped_column(DateTime)
    rankings: Mapped[list] = mapped_column(JSON)  # [{rank, school, blurb}, ...]
    methodology: Mapped[str | None] = mapped_column(String(300))
