"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import { getTeamAnalysis, getTeamDiscussion, predictTeamSeason } from "@/lib/api";

export default function TeamDetailPage() {
  const params = useParams();
  const school = decodeURIComponent(String(params.school));
  const [discussion, setDiscussion] = useState<string | null>(null);
  const [loadingDiscussion, setLoadingDiscussion] = useState(false);
  const [seasonPrediction, setSeasonPrediction] = useState<any | null>(null);
  const [predictingSeason, setPredictingSeason] = useState(false);

  const { data: analysis, isLoading } = useQuery({
    queryKey: ["team-analysis", school],
    queryFn: () => getTeamAnalysis(school),
  });

  async function loadDiscussion() {
    setLoadingDiscussion(true);
    try {
      const res = await getTeamDiscussion(school);
      setDiscussion(res.ai_discussion);
    } finally {
      setLoadingDiscussion(false);
    }
  }

  async function loadSeasonPrediction() {
    setPredictingSeason(true);
    try {
      const res = await predictTeamSeason(school);
      setSeasonPrediction(res);
    } finally {
      setPredictingSeason(false);
    }
  }

  const predictionByWeek: Record<number, any> = {};
  if (seasonPrediction) {
    for (const g of seasonPrediction.games) predictionByWeek[g.week] = g;
  }

  if (isLoading) return <p className="text-gray-500">Loading...</p>;
  if (!analysis) return <p className="text-gray-500">Team not found.</p>;

  const { team, last_season, best_players, offseason, schedule, record_so_far } = analysis;

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        {team.logo && <img src={team.logo} alt="" className="w-10 h-10" onError={(e: any) => (e.target.style.display = "none")} />}
        <h1 className="text-2xl font-bold text-white">{team.school}</h1>
        {team.ap_rank && <span className="text-cfb-gold text-sm font-semibold">AP #{team.ap_rank}</span>}
      </div>
      <p className="text-gray-400 mb-6">{team.mascot} · {team.conference}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <Stat
          label={last_season ? `${last_season.season} Record` : "Last Season"}
          value={last_season ? `${last_season.wins}-${last_season.losses}` : "—"}
        />
        <Stat
          label="Conference Record"
          value={last_season ? `${last_season.conference_wins}-${last_season.conference_losses}` : "—"}
        />
        <Stat
          label="SP+ Rating"
          value={team.sp_rating ? `${team.sp_rating.rating} (#${team.sp_rating.ranking})` : "—"}
        />
        <Stat
          label={record_so_far ? `${analysis.season} Record` : `${analysis.season} Status`}
          value={record_so_far ? `${record_so_far.wins}-${record_so_far.losses}` : "Preseason"}
        />
      </div>

      <div className="mb-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">AI Team Discussion</h2>
        {!discussion ? (
          <button
            onClick={loadDiscussion}
            disabled={loadingDiscussion}
            className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
          >
            {loadingDiscussion ? "Analyzing..." : "Discuss This Team"}
          </button>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-200">
            {discussion}
          </div>
        )}
      </div>

      {best_players?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Best Returning Players</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {best_players.map((p: any, i: number) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded p-3 text-sm">
                <div className="flex justify-between">
                  <p className="text-white font-medium">{p.name}</p>
                  <p className="text-gray-500">{p.position} · class {p.year}</p>
                </div>
                <p className="text-xs text-gray-400 mt-1">{p.stat_line || "limited stats"}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Offseason Activity</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-2">Departed ({offseason.departed.length})</p>
            <div className="space-y-1">
              {offseason.departed.slice(0, 8).map((d: any, i: number) => (
                <p key={i} className="text-xs text-gray-400">{d.name} <span className="text-gray-600">({d.position})</span> → {d.to_school || "uncommitted"}</p>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-2">Incoming Transfers ({offseason.incoming_transfers.length})</p>
            <div className="space-y-1">
              {offseason.incoming_transfers.slice(0, 8).map((t: any, i: number) => (
                <p key={i} className="text-xs text-gray-400">{t.name} <span className="text-gray-600">({t.position})</span> from {t.from_school}</p>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-2">Signees ({offseason.signees.length})</p>
            <div className="space-y-1">
              {offseason.signees
                .slice()
                .sort((a: any, b: any) => (b.stars || 0) - (a.stars || 0))
                .slice(0, 8)
                .map((s: any, i: number) => (
                  <p key={i} className="text-xs text-gray-400">{s.name} <span className="text-gray-600">({s.position})</span> {s.stars ? `${s.stars}★` : ""}</p>
                ))}
            </div>
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-400 uppercase">{analysis.season} Schedule</h2>
          <button
            onClick={loadSeasonPrediction}
            disabled={predictingSeason}
            className="bg-gray-800 hover:bg-gray-700 text-white text-xs px-3 py-1.5 rounded disabled:opacity-50"
          >
            {predictingSeason ? "Predicting full season..." : seasonPrediction ? "Re-predict Season" : "AI Predict Season"}
          </button>
        </div>

        {seasonPrediction && (
          <p className="text-sm text-cfb-gold font-medium mb-3">
            Projected record: {seasonPrediction.projected_wins}-{seasonPrediction.projected_losses}
          </p>
        )}

        <div className="space-y-1">
          {schedule.map((g: any, i: number) => {
            const pred = predictionByWeek[g.week];
            return (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded p-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-white">
                    Wk {g.week ?? "—"} · {g.location === "home" ? "vs" : g.location === "away" ? "@" : "vs (neutral)"} {g.opponent}
                  </span>
                  <span className={g.completed ? "text-gray-300" : "text-gray-600"}>
                    {g.completed
                      ? `${(g.team_points ?? 0) > (g.opponent_points ?? 0) ? "W" : "L"} ${g.team_points}-${g.opponent_points}`
                      : pred?.status === "predicted"
                        ? `Predicted ${pred.result} (${pred.confidence}%)`
                        : "Not played"}
                  </span>
                </div>
                {pred?.status === "predicted" && (
                  <p className="text-xs text-gray-500 mt-1">AI picks {pred.predicted_winner}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-8">
        <Link href="/teams" className="text-xs text-gray-500 hover:text-gray-300">← Back to Teams</Link>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      <p className="text-xs text-gray-500 uppercase">{label}</p>
      <p className="text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
