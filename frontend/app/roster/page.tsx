"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { getCurrentRoster, analyzeRoster } from "@/lib/api";

const STATUS_STYLE: Record<string, string> = {
  "transfer in": "bg-blue-900 text-blue-300",
  signee: "bg-green-900 text-green-300",
};

export default function RosterPage() {
  const [team, setTeam] = useState("");
  const [submittedTeam, setSubmittedTeam] = useState("");
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["roster", "current", submittedTeam],
    queryFn: () => getCurrentRoster(submittedTeam),
    enabled: !!submittedTeam,
  });
  const roster = data?.roster ?? {};

  async function loadAnalysis() {
    if (!submittedTeam) return;
    setLoading(true);
    setAnalysis(null);
    try {
      const res = await analyzeRoster(submittedTeam);
      setAnalysis(res.analysis);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-4">Roster</h1>
      <form
        className="flex gap-3 mb-6"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmittedTeam(team);
          setAnalysis(null);
        }}
      >
        <input
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm flex-1"
          placeholder="Team name (e.g. Alabama)..."
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        />
        <button type="submit" className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded">
          Load Roster
        </button>
      </form>

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {submittedTeam && !isLoading && Object.keys(roster).length === 0 && (
        <p className="text-gray-500">No roster found for &quot;{submittedTeam}&quot;.</p>
      )}

      {Object.keys(roster).length > 0 && (
        <>
          <p className="text-xs text-gray-500 mb-4">
            Base roster from {data.base_season}, adjusted for {data.portal_cycle} portal moves and{" "}
            {data.recruiting_class} signees — CFBD hasn&apos;t published a full {data.portal_cycle} roster yet.
          </p>

          <button
            onClick={loadAnalysis}
            disabled={loading}
            className="bg-gray-800 hover:bg-gray-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50 mb-6"
          >
            {loading ? "Analyzing..." : "AI Roster Analysis"}
          </button>

          {analysis && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-200 mb-6">
              {analysis}
            </div>
          )}

          {Object.entries(roster).map(([pos, players]: [string, any]) => (
            <div key={pos} className="mb-4">
              <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">{pos}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {players.map((p: any) => (
                  <Link
                    key={p.id}
                    href={`/players/${p.id}`}
                    className="bg-gray-900 border border-gray-800 rounded p-2 text-sm hover:border-cfb-crimson transition-colors"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-white">{p.name}</p>
                      {p.status && p.status !== "returning" && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap ${STATUS_STYLE[p.status] ?? "bg-gray-800 text-gray-400"}`}>
                          {p.status}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">#{p.jersey ?? "—"} · {p.year ?? "—"}</p>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
