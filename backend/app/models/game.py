from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cfbd_id: Mapped[int | None] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int | None] = mapped_column(Integer)
    season_type: Mapped[str | None] = mapped_column(String(20))
    start_date: Mapped[DateTime | None] = mapped_column(DateTime)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    neutral_site: Mapped[bool] = mapped_column(Boolean, default=False)
    venue: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(300))

    home_team: Mapped[str | None] = mapped_column(String(100), index=True)
    home_conference: Mapped[str | None] = mapped_column(String(100))
    home_points: Mapped[int | None] = mapped_column(Integer)

    away_team: Mapped[str | None] = mapped_column(String(100), index=True)
    away_conference: Mapped[str | None] = mapped_column(String(100))
    away_points: Mapped[int | None] = mapped_column(Integer)

    # AI prediction (generated + cached on request, not auto-computed for every game)
    predicted_winner: Mapped[str | None] = mapped_column(String(100))
    predicted_confidence: Mapped[int | None] = mapped_column(Integer)  # 0-100
    prediction_analysis: Mapped[str | None] = mapped_column(String(4000))
