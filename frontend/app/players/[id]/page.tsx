"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getPlayerProfile, getScoutingReport } from "@/lib/api";
import { useState } from "react";

export default function PlayerDetailPage() {
  const params = useParams();
  const ref = String(params.id);
  const isRealPlayer = /^\d+$/.test(ref);
  const [report, setReport] = useState<string | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["player-profile", ref],
    queryFn: () => getPlayerProfile(ref),
  });

  async function loadReport() {
    setLoadingReport(true);
    try {
      const res = await getScoutingReport(Number(ref));
      setReport(res.report);
    } finally {
      setLoadingReport(false);
    }
  }

  if (isLoading) return <p className="text-gray-500">Loading...</p>;
  if (!profile) return <p className="text-gray-500">Player not found.</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">{profile.name}</h1>
      <p className="text-gray-400 mb-6">{profile.position} · {profile.team} · {profile.year}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <Stat label="Height" value={profile.height ? `${profile.height}in` : "—"} />
        <Stat label="Weight" value={profile.weight ? `${profile.weight}lb` : "—"} />
        <Stat label="Hometown" value={[profile.home_city, profile.home_state].filter(Boolean).join(", ") || "—"} />
        <Stat label="Jersey" value={profile.jersey ?? "—"} />
      </div>

      <div className="mb-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">AI Player Profile</h2>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-200">
          {profile.ai_bio}
        </div>
      </div>

      {profile.team_history?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Team History</h2>
          <div className="space-y-1">
            {profile.team_history.map((th: any, i: number) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded p-2 text-sm flex justify-between">
                <span className="text-white">{th.season} — {th.team}</span>
                <span className="text-gray-500">{th.position} · class {th.year ?? "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {profile.transfers?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Transfer Portal Activity</h2>
          <div className="space-y-1">
            {profile.transfers.map((t: any, i: number) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded p-2 text-sm flex justify-between">
                <span className="text-white">{t.season} — {t.from_school} → {t.to_school ?? "uncommitted"}</span>
                <span className="text-gray-500">{t.stars ? `${t.stars}★` : "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {profile.season_stats?.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Season-by-Season Stats</h2>
          {profile.season_stats.map((s: any, i: number) => (
            <div key={i} className="mb-3">
              <p className="text-xs text-gray-500 mb-1">{s.season} — {s.team}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(s)
                  .filter(([k, v]) => !["season", "team"].includes(k) && v !== null && v !== undefined)
                  .map(([k, v]) => (
                    <Stat key={k} label={k.replace(/_/g, " ")} value={v as any} />
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {isRealPlayer && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">AI Scouting Report</h2>
          {!report ? (
            <button
              onClick={loadReport}
              disabled={loadingReport}
              className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50"
            >
              {loadingReport ? "Generating..." : "Generate Scouting Report"}
            </button>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-200">
              {report}
            </div>
          )}
        </div>
      )}
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
