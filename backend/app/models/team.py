from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cfbd_id: Mapped[int | None] = mapped_column(Integer, index=True)
    school: Mapped[str] = mapped_column(String(100), index=True)
    mascot: Mapped[str | None] = mapped_column(String(100))
    conference: Mapped[str | None] = mapped_column(String(100), index=True)
    division: Mapped[str | None] = mapped_column(String(100))
    classification: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str | None] = mapped_column(String(10))
    alt_color: Mapped[str | None] = mapped_column(String(10))
    logo: Mapped[str | None] = mapped_column(String(500))

    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    conference_wins: Mapped[int | None] = mapped_column(Integer)
    conference_losses: Mapped[int | None] = mapped_column(Integer)
    ap_rank: Mapped[int | None] = mapped_column(Integer)
    sp_rating: Mapped[float | None] = mapped_column(Float)
    season: Mapped[int] = mapped_column(Integer, index=True)
