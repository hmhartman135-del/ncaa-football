from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cfbd_id: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    position: Mapped[str | None] = mapped_column(String(10), index=True)
    team: Mapped[str | None] = mapped_column(String(100), index=True)
    jersey: Mapped[int | None] = mapped_column(Integer)
    year: Mapped[str | None] = mapped_column(String(10))  # FR/SO/JR/SR/GR
    height: Mapped[int | None] = mapped_column(Integer)  # inches
    weight: Mapped[int | None] = mapped_column(Integer)  # lbs
    home_city: Mapped[str | None] = mapped_column(String(100))
    home_state: Mapped[str | None] = mapped_column(String(10))
    season: Mapped[int] = mapped_column(Integer, index=True)

    draft_eligible: Mapped[bool] = mapped_column(default=False)


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    games: Mapped[int | None] = mapped_column(Integer)

    completions: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int | None] = mapped_column(Integer)
    passing_yards: Mapped[int | None] = mapped_column(Integer)
    passing_tds: Mapped[int | None] = mapped_column(Integer)
    interceptions: Mapped[int | None] = mapped_column(Integer)

    carries: Mapped[int | None] = mapped_column(Integer)
    rushing_yards: Mapped[int | None] = mapped_column(Integer)
    rushing_tds: Mapped[int | None] = mapped_column(Integer)

    targets: Mapped[int | None] = mapped_column(Integer)
    receptions: Mapped[int | None] = mapped_column(Integer)
    receiving_yards: Mapped[int | None] = mapped_column(Integer)
    receiving_tds: Mapped[int | None] = mapped_column(Integer)

    tackles: Mapped[float | None] = mapped_column(Float)
    sacks: Mapped[float | None] = mapped_column(Float)
    tackles_for_loss: Mapped[float | None] = mapped_column(Float)
    interceptions_def: Mapped[int | None] = mapped_column(Integer)
    passes_defended: Mapped[int | None] = mapped_column(Integer)

    # CFBD advanced metrics
    ppa_total: Mapped[float | None] = mapped_column(Float)
    ppa_avg: Mapped[float | None] = mapped_column(Float)
