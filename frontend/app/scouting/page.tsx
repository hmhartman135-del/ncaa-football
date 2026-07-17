"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getPlayers, comparePlayers } from "@/lib/api";

const MAX_SELECTED = 4;

export default function ScoutingPage() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<{ id: number; name: string; position: string; team: string }[]>([]);
  const [teamContext, setTeamContext] = useState("");
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzedTeamContext, setAnalyzedTeamContext] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { data: players = [] } = useQuery({
    queryKey: ["players-search", search],
    queryFn: () => getPlayers({ search: search || undefined, limit: 20 }),
    enabled: search.length > 1,
  });

  function toggle(p: any) {
    setSelected((prev) => {
      const exists = prev.find((x) => x.id === p.id);
      if (exists) return prev.filter((x) => x.id !== p.id);
      return [...prev, { id: p.id, name: p.name, position: p.position, team: p.team }].slice(-MAX_SELECTED);
    });
  }

  async function runCompare() {
    if (selected.length < 2) return;
    setLoading(true);
    try {
      const res = await comparePlayers(selected.map((p) => p.id), teamContext || undefined);
      setAnalysis(res.analysis);
      setAnalyzedTeamContext(res.team_context);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Scouting</h1>
      <p className="text-gray-400 mb-6 text-sm">
        Search players and select 2-{MAX_SELECTED} to generate an AI comparison — stats, background, career
        history, and who you should prefer. Optionally add a team to also get a fit verdict for that roster.
      </p>

      <input
        className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm w-full max-w-md mb-4"
        placeholder="Search players to compare..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {players.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
          {players.map((p: any) => (
            <button
              key={p.id}
              onClick={() => toggle(p)}
              className={`text-left text-sm border rounded p-2 transition-colors ${
                selected.some((x) => x.id === p.id) ? "border-cfb-crimson bg-cfb-crimson/10" : "border-gray-800 bg-gray-900"
              }`}
            >
              <p className="text-white">{p.name}</p>
              <p className="text-xs text-gray-500">{p.position} · {p.team}</p>
            </button>
          ))}
        </div>
      )}

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {selected.map((p) => (
            <span key={p.id} className="flex items-center gap-1.5 bg-gray-900 border border-cfb-crimson/50 rounded-full pl-3 pr-1 py-1 text-xs text-white">
              {p.name} <span className="text-gray-500">({p.position})</span>
              <button
                onClick={() => toggle(p)}
                className="w-4 h-4 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 flex items-center justify-center"
                aria-label={`Remove ${p.name}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <input
        className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm w-full max-w-md mb-4"
        placeholder="Fit for team (optional, e.g. Ohio State)..."
        value={teamContext}
        onChange={(e) => setTeamContext(e.target.value)}
      />

      <div>
        <button
          onClick={runCompare}
          disabled={selected.length < 2 || loading}
          className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50 mb-6"
        >
          {loading ? "Comparing..." : `Compare Selected (${selected.length})`}
        </button>
      </div>

      {analysis && (
        <div>
          {analyzedTeamContext && (
            <p className="text-xs text-gray-500 mb-2">Includes a fit verdict for {analyzedTeamContext}.</p>
          )}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-200">
            {analysis}
          </div>
        </div>
      )}
    </div>
  );
}
