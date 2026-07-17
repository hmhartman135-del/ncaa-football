import asyncio
import re
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from ..database import AsyncSessionLocal
from ..models.game import Game
from ..config import settings
from .team_service import get_team_analysis, _context_text

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _game_dict(g: Game) -> dict:
    return {
        "id": g.id,
        "week": g.week,
        "start_date": g.start_date.isoformat() if g.start_date else None,
        "venue": g.venue,
        "neutral_site": g.neutral_site,
        "notes": g.notes,
        "completed": g.completed,
        "home_team": g.home_team,
        "home_conference": g.home_conference,
        "home_points": g.home_points,
        "away_team": g.away_team,
        "away_conference": g.away_conference,
        "away_points": g.away_points,
        "predicted_winner": g.predicted_winner,
        "predicted_confidence": g.predicted_confidence,
        "prediction_analysis": g.prediction_analysis,
    }


async def _resolve_season(db: AsyncSession) -> int | None:
    return (await db.execute(select(func.max(Game.season)))).scalar()


async def list_weeks(db: AsyncSession, season: int | None = None) -> dict:
    if season is None:
        season = await _resolve_season(db)
        if season is None:
            return {"season": None, "weeks": []}

    result = await db.execute(
        select(Game.week).where(Game.season == season).distinct().order_by(Game.week)
    )
    weeks = [w for (w,) in result.all() if w is not None]
    return {"season": season, "weeks": weeks}


async def get_games_for_week(db: AsyncSession, week: int, season: int | None = None) -> dict:
    if season is None:
        season = await _resolve_season(db)
        if season is None:
            return {"season": None, "week": week, "games": []}

    result = await db.execute(
        select(Game)
        .where(Game.season == season, Game.week == week)
        .order_by(Game.start_date.asc().nulls_last())
    )
    games = result.scalars().all()
    return {"season": season, "week": week, "games": [_game_dict(g) for g in games]}


async def predict_game(db: AsyncSession, game_id: int, force: bool = False) -> dict | None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        return None

    if game.predicted_winner and not force:
        return _game_dict(game)

    home_analysis = await get_team_analysis(db, game.home_team)
    away_analysis = await get_team_analysis(db, game.away_team)
    if not home_analysis or not away_analysis:
        return None

    matchup_line = (
        f"\nMATCHUP: Week {game.week}"
        + (f", {game.start_date.strftime('%b %d, %Y')}" if game.start_date else "")
        + f" — {'Neutral site' if game.neutral_site else f'at {game.home_team}'}"
        + (f" ({game.venue})" if game.venue else "")
    )
    context = (
        f"HOME TEAM:\n{_context_text(home_analysis)}\n\n"
        f"AWAY TEAM:\n{_context_text(away_analysis)}\n"
        f"{matchup_line}"
    )

    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=(
            "You are a college football analyst predicting a specific matchup. Use the two teams' records, "
            "SP+ ratings, returning production, and offseason moves provided. Note that if a season hasn't "
            "started or these teams have few/no games played yet, you're working from limited/preseason "
            "information — say so explicitly and lean on roster talent and returning production instead of "
            "in-season form. Respond in this exact format:\n"
            "WINNER: <exact team name as given>\n"
            "CONFIDENCE: <integer 50-99>\n"
            "ANALYSIS: <250-350 word breakdown of why, covering the key factors that decide it>"
        ),
        messages=[{"role": "user", "content": f"Predict this matchup:\n\n{context}"}],
    )
    text = response.content[0].text

    winner_match = re.search(r"WINNER:\s*(.+)", text)
    confidence_match = re.search(r"CONFIDENCE:\s*(\d+)", text)
    analysis_match = re.search(r"ANALYSIS:\s*([\s\S]+)", text)

    game.predicted_winner = winner_match.group(1).strip() if winner_match else None
    game.predicted_confidence = int(confidence_match.group(1)) if confidence_match else None
    game.prediction_analysis = analysis_match.group(1).strip() if analysis_match else text
    await db.commit()
    await db.refresh(game)
    return _game_dict(game)


async def _predict_game_isolated(game_id: int, force: bool) -> dict | None:
    """Runs predict_game on its own DB session — required so multiple games
    can be predicted concurrently (a single AsyncSession can't be shared
    across concurrent coroutines)."""
    async with AsyncSessionLocal() as session:
        return await predict_game(session, game_id, force=force)


async def predict_team_season(db: AsyncSession, school: str, force: bool = False) -> dict | None:
    """Full-season projection for one team: real results for completed games,
    AI predictions (generated + cached per-game via predict_game) for the rest.
    Reuses the same per-game prediction/cache as the Matchups tab, so a game
    predicted here also shows up already-predicted there, and vice versa.
    Predicts all of a team's remaining games concurrently — sequential would
    take N x ~15s (multiple minutes for a full season); in parallel it's
    bounded by the slowest single call."""
    season = await _resolve_season(db)
    if season is None:
        return None

    result = await db.execute(
        select(Game)
        .where(Game.season == season, or_(Game.home_team == school, Game.away_team == school))
        .order_by(Game.week)
    )
    games = result.scalars().all()
    if not games:
        return None

    to_predict = [g for g in games if not g.completed]
    predictions = await asyncio.gather(*[_predict_game_isolated(g.id, force) for g in to_predict])
    pred_by_id = {g.id: p for g, p in zip(to_predict, predictions)}

    wins = losses = 0
    breakdown = []
    for g in games:
        is_home = g.home_team == school
        opponent = g.away_team if is_home else g.home_team
        location = "neutral" if g.neutral_site else ("home" if is_home else "away")

        if g.completed:
            team_pts = g.home_points if is_home else g.away_points
            opp_pts = g.away_points if is_home else g.home_points
            won = (team_pts or 0) > (opp_pts or 0)
            wins += won
            losses += not won
            breakdown.append({
                "week": g.week, "opponent": opponent, "location": location,
                "status": "completed", "result": "W" if won else "L", "score": f"{team_pts}-{opp_pts}",
            })
            continue

        pred = pred_by_id.get(g.id)
        if not pred or not pred.get("predicted_winner"):
            breakdown.append({
                "week": g.week, "opponent": opponent, "location": location,
                "status": "unpredicted", "result": None,
            })
            continue

        predicted_win = school.lower() in pred["predicted_winner"].lower()
        wins += predicted_win
        losses += not predicted_win
        breakdown.append({
            "week": g.week, "opponent": opponent, "location": location,
            "status": "predicted", "result": "W" if predicted_win else "L",
            "confidence": pred["predicted_confidence"], "predicted_winner": pred["predicted_winner"],
        })

    return {
        "school": school, "season": season,
        "projected_wins": wins, "projected_losses": losses,
        "games": breakdown,
    }
