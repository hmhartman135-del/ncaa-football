from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class NflDraftPick(Base):
    """Real historical NFL draft picks (from CFBD `/draft/picks`) — used to
    exclude players who've left college for the NFL from current-roster views.
    Distinct from `DraftProspect`, which is AI-graded speculation on still-in-college players."""

    __tablename__ = "nfl_draft_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cfbd_athlete_id: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    college_team: Mapped[str | None] = mapped_column(String(100))
    position: Mapped[str | None] = mapped_column(String(30))
    draft_year: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[int | None] = mapped_column(Integer)
    pick: Mapped[int | None] = mapped_column(Integer)
    nfl_team: Mapped[str | None] = mapped_column(String(100))
