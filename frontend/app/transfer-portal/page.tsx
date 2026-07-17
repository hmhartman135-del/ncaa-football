"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getTransferPortal, gradePortalEntry, getTeamPortalActivity, getPortalRankings, getTeams } from "@/lib/api";

type Tab = "entries" | "team" | "rankings";

export default function TransferPortalPage() {
  const [tab, setTab] = useState<Tab>("entries");

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Transfer Portal</h1>
      <p className="text-gray-400 mb-6 text-sm">2026 cycle, feeding the 2026 season.</p>

      <div className="flex gap-2 mb-6">
        {(["entries", "team", "rankings"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-sm px-3 py-1.5 rounded ${tab === t ? "bg-cfb-crimson text-white" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
          >
            {t === "entries" ? "All Entries" : t === "team" ? "Team Activity" : "Rankings"}
          </button>
        ))}
      </div>

      {tab === "entries" && <EntriesTab />}
      {tab === "team" && <TeamTab />}
      {tab === "rankings" && <RankingsTab />}
    </div>
  );
}

function EntriesTab() {
  const [position, setPosition] = useState("");
  const [gradingId, setGradingId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["portal", position],
    queryFn: () => getTransferPortal({ position: position || undefined, limit: 300 }),
  });

  async function grade(id: number) {
    setGradingId(id);
    try {
      await gradePortalEntry(id);
      queryClient.invalidateQueries({ queryKey: ["portal"] });
    } finally {
      setGradingId(null);
    }
  }

  return (
    <div>
      <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm mb-6" value={position} onChange={(e) => setPosition(e.target.value)}>
        <option value="">All Positions</option>
        {["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"].map((p) => <option key={p} value={p}>{p}</option>)}
      </select>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : entries.length === 0 ? (
        <p className="text-gray-500">No transfer portal data yet.</p>
      ) : (
        <div className="space-y-3">
          {entries.map((e: any) => (
            <div key={e.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white font-medium">
                    {e.player_name} <span className="text-gray-500 text-sm">({e.position})</span>
                  </p>
                  <p className="text-sm text-gray-400">{e.from_school} → {e.to_school || "Uncommitted"}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {e.class_year || "Class year unknown"}
                    {e.stars ? ` · ${e.stars}★` : ""}
                    {e.eligibility_status ? ` · ${e.eligibility_status}` : ""}
                  </p>
                </div>
                {e.overall_grade ? (
                  <span className="text-cfb-gold font-bold text-lg">{e.overall_grade}</span>
                ) : (
                  <button
                    onClick={() => grade(e.id)}
                    disabled={gradingId === e.id}
                    className="bg-gray-800 hover:bg-gray-700 text-white text-xs px-3 py-1.5 rounded disabled:opacity-50"
                  >
                    {gradingId === e.id ? "Grading..." : "AI Grade"}
                  </button>
                )}
              </div>
              {e.ai_analysis && <p className="text-sm text-gray-300 mt-2">{e.ai_analysis}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TeamTab() {
  const [team, setTeam] = useState("");
  const [submittedTeam, setSubmittedTeam] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["portal-team", submittedTeam],
    queryFn: () => getTeamPortalActivity(submittedTeam),
    enabled: !!submittedTeam,
  });

  return (
    <div>
      <form
        className="flex gap-3 mb-6"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmittedTeam(team);
        }}
      >
        <input
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm flex-1 max-w-md"
          placeholder="Team name (e.g. Ohio State)..."
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        />
        <button type="submit" className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded">
          Load
        </button>
      </form>

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Lost ({data.lost.length})</h2>
            <div className="space-y-2">
              {data.lost.map((e: any) => (
                <div key={e.id} className="bg-gray-900 border border-gray-800 rounded p-3 text-sm">
                  <p className="text-white">{e.player_name} <span className="text-gray-500">({e.position})</span></p>
                  <p className="text-xs text-gray-500">
                    → {e.to_school || "uncommitted"} · {e.class_year || "class unknown"}{e.stars ? ` · ${e.stars}★` : ""}
                  </p>
                </div>
              ))}
              {data.lost.length === 0 && <p className="text-gray-600 text-sm">No departures this cycle.</p>}
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Gained ({data.gained.length})</h2>
            <div className="space-y-2">
              {data.gained.map((e: any) => (
                <div key={e.id} className="bg-gray-900 border border-gray-800 rounded p-3 text-sm">
                  <p className="text-white">{e.player_name} <span className="text-gray-500">({e.position})</span></p>
                  <p className="text-xs text-gray-500">
                    from {e.from_school} · {e.class_year || "class unknown"}{e.stars ? ` · ${e.stars}★` : ""}
                  </p>
                </div>
              ))}
              {data.gained.length === 0 && <p className="text-gray-600 text-sm">No commits this cycle.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RankingsTab() {
  const [conference, setConference] = useState("");

  const { data: teams = [] } = useQuery({ queryKey: ["teams-for-conf"], queryFn: () => getTeams() });
  const conferences = Array.from(new Set(teams.map((t: any) => t.conference).filter(Boolean))).sort() as string[];

  const { data, isLoading } = useQuery({
    queryKey: ["portal-rankings", conference],
    queryFn: () => getPortalRankings({ conference: conference || undefined }),
  });

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">
        Ranked by the composite value of talent added via the portal (the standard &quot;who won the portal&quot;
        metric) — net gain/loss and raw counts shown for context.
      </p>
      <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm mb-6" value={conference} onChange={(e) => setConference(e.target.value)}>
        <option value="">All of NCAA</option>
        {conferences.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">#</th>
              <th className="py-1.5 font-medium">Team</th>
              <th className="py-1.5 font-medium">Conference</th>
              <th className="py-1.5 font-medium">In</th>
              <th className="py-1.5 font-medium">Out</th>
              <th className="py-1.5 font-medium">Net</th>
              <th className="py-1.5 font-medium">Gained</th>
              <th className="py-1.5 font-medium">Lost</th>
            </tr>
          </thead>
          <tbody>
            {data?.rankings.map((r: any) => (
              <tr key={r.school} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-1.5 text-gray-400">{r.rank}</td>
                <td className="py-1.5 text-white">{r.school}</td>
                <td className="py-1.5 text-gray-400">{r.conference}</td>
                <td className="py-1.5 text-gray-300">{r.incoming_score}</td>
                <td className="py-1.5 text-gray-300">{r.outgoing_score}</td>
                <td className={`py-1.5 ${r.net_score >= 0 ? "text-green-400" : "text-red-400"}`}>{r.net_score > 0 ? "+" : ""}{r.net_score}</td>
                <td className="py-1.5 text-gray-400">{r.incoming_count}</td>
                <td className="py-1.5 text-gray-400">{r.outgoing_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
