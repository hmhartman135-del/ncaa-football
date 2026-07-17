from sqlalchemy import Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Recruit(Base):
    __tablename__ = "recruits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cfbd_id: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    position: Mapped[str | None] = mapped_column(String(10), index=True)
    class_year: Mapped[int] = mapped_column(Integer, index=True)  # signing class, e.g. 2027
    stars: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[float | None] = mapped_column(Float)
    national_rank: Mapped[int | None] = mapped_column(Integer)
    position_rank: Mapped[int | None] = mapped_column(Integer)
    state_rank: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    weight: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(100))
    state_province: Mapped[str | None] = mapped_column(String(10))
    committed_to: Mapped[str | None] = mapped_column(String(100))
    committed: Mapped[bool] = mapped_column(Boolean, default=False)

    # provenance — CFBD-sourced rows are auto-ingested and "source" defaults
    # to that; rows manually loaded from a 247Sports link the user pasted are
    # tagged "247sports" with fetched_at set, so the UI can show freshness
    source: Mapped[str] = mapped_column(String(20), default="cfbd")
    fetched_at: Mapped[DateTime | None] = mapped_column(DateTime)
