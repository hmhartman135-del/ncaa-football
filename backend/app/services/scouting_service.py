import asyncio
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.player_profile_service import get_player_context, _context_text as _player_context_text
from ..services.team_service import get_team_analysis, _context_text as _team_context_text
from ..config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def generate_scouting_report(db: AsyncSession, player_id: int) -> str:
    profile = await get_player_context(db, player_id)
    if not profile:
        return "Player not found."

    context = _player_context_text(profile)
    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=(
            "You are a college football scout writing professional player evaluations. "
            "Use the full career history, stats, and background provided — not just the most "
            "recent season. Cover: strengths, weaknesses, role fit, eligibility/development outlook, "
            "and a final letter grade (A/B/C/D/F with +/-). Keep it under 500 words."
        ),
        messages=[{"role": "user", "content": f"Write a scouting report for:\n\n{context}"}],
    )
    return response.content[0].text


async def compare_players(db: AsyncSession, player_ids: list[int], team_context: str | None = None) -> str:
    sections = []
    for pid in player_ids:
        profile = await get_player_context(db, pid)
        if not profile:
            continue
        sections.append(_player_context_text(profile))

    if not sections:
        return "Players not found."

    players_block = "\n\n".join(f"Player {i+1}:\n{ctx}" for i, ctx in enumerate(sections))

    team_block = ""
    if team_context:
        team_analysis = await get_team_analysis(db, team_context)
        if team_analysis:
            team_block = f"\n\nTeam to evaluate fit for — {team_context}:\n{_team_context_text(team_analysis)}"

    instructions = (
        "You are a senior college football analyst doing a detailed player comparison. Use the full "
        "career history, stats, and background (hometown, recruiting profile, transfer history) provided "
        "for each player — not just their most recent season. Give a thorough side-by-side breakdown "
        "covering production, trajectory, strengths, and weaknesses. End with a clear verdict on who you'd "
        "prefer **in general** (as a prospect/talent, independent of any team) and why."
    )
    if team_context:
        instructions += (
            f" Then, separately, give a distinct **fit verdict for {team_context}** specifically — using "
            "that team's actual roster needs, returning players at the same position(s), scheme, and depth "
            "chart situation from the team context provided. The general verdict and the team-fit verdict "
            "can reasonably disagree (e.g. the better overall prospect might not be the best fit for this "
            "specific roster) — call that out explicitly if it happens."
        )

    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=1800,
        system=instructions,
        messages=[{"role": "user", "content": f"Compare these players:\n\n{players_block}{team_block}"}],
    )
    return response.content[0].text
