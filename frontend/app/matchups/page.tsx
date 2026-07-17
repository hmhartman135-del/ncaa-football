"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getGameWeeks, getGamesForWeek, predictGame } from "@/lib/api";

export default function MatchupsPage() {
  const [week, setWeek] = useState<number | null>(null);
  const [predictingId, setPredictingId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: weeksData } = useQuery({ queryKey: ["game-weeks"], queryFn: () => getGameWeeks() });
  const weeks: number[] = weeksData?.weeks ?? [];

  useEffect(() => {
    if (week === null && weeks.length > 0) setWeek(weeks[0]);
  }, [weeks, week]);

  const { data, isLoading } = useQuery({
    queryKey: ["games-for-week", week],
    queryFn: () => getGamesForWeek({ week: week! }),
    enabled: week !== null,
  });

  async function predict(gameId: number) {
    setPredictingId(gameId);
    try {
      await predictGame(gameId);
      queryClient.invalidateQueries({ queryKey: ["games-for-week", week] });
    } finally {
      setPredictingId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Matchups</h1>
      <p className="text-gray-400 mb-6 text-sm">
        {data?.season ?? ""} season schedule, by week — get an AI prediction for any game.
      </p>

      <div className="flex flex-wrap gap-2 mb-6">
        {weeks.map((w) => (
          <button
            key={w}
            onClick={() => setWeek(w)}
            className={`text-sm px-3 py-1.5 rounded ${week === w ? "bg-cfb-crimson text-white" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
          >
            Week {w}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : !data?.games.length ? (
        <p className="text-gray-500">No games found for this week.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.games.map((g: any) => (
            <GameCard
              key={g.id}
              game={g}
              predicting={predictingId === g.id}
              onPredict={() => predict(g.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function GameCard({ game, predicting, onPredict }: { game: any; predicting: boolean; onPredict: () => void }) {
  const date = game.start_date
    ? new Date(game.start_date).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
    : null;

  const winner = game.predicted_winner;
  const homeIsWinner = winner && game.home_team && winner.toLowerCase().includes(game.home_team.toLowerCase());
  const awayIsWinner = winner && game.away_team && winner.toLowerCase().includes(game.away_team.toLowerCase());

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-500 mb-2">
        {date ?? "Date TBD"}
        {game.venue && ` · ${game.venue}`}
        {game.neutral_site && " (neutral site)"}
      </p>

      <div className="flex items-center justify-between mb-1">
        <TeamLine name={game.away_team} points={game.away_points} isWinner={!!awayIsWinner} />
        <span className="text-gray-600 text-xs px-2">@</span>
        <TeamLine name={game.home_team} points={game.home_points} isWinner={!!homeIsWinner} align="right" />
      </div>

      {game.completed && (
        <p className="text-xs text-cfb-gold mt-2">Final</p>
      )}

      {!winner ? (
        <button
          onClick={onPredict}
          disabled={predicting}
          className="mt-3 w-full bg-gray-800 hover:bg-gray-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
        >
          {predicting ? "Predicting..." : "AI Predict"}
        </button>
      ) : (
        <div className="mt-3 bg-gray-950 border border-gray-800 rounded p-3">
          <p className="text-sm text-white font-medium mb-1">
            Predicted: {winner} <span className="text-gray-500 font-normal">({game.predicted_confidence}% confidence)</span>
          </p>
          <p className="text-xs text-gray-400 whitespace-pre-wrap">{game.prediction_analysis}</p>
        </div>
      )}
    </div>
  );
}

function TeamLine({ name, points, isWinner, align = "left" }: { name: string; points: number | null; isWinner: boolean; align?: "left" | "right" }) {
  return (
    <div className={`flex-1 ${align === "right" ? "text-right" : ""}`}>
      <Link href={`/teams/${encodeURIComponent(name)}`} className={`text-sm hover:text-cfb-crimson ${isWinner ? "text-cfb-gold font-semibold" : "text-white"}`}>
        {name}
      </Link>
      {points !== null && <span className="text-gray-400 text-sm ml-2 tabular-nums">{points}</span>}
    </div>
  );
}
