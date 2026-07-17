"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getDraftEligible, getDraftBoard, gradeDraftProspect } from "@/lib/api";

export default function DraftPage() {
  const [gradingId, setGradingId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: board = [] } = useQuery({
    queryKey: ["draft-board"],
    queryFn: () => getDraftBoard({ draft_year: 2027 }),
  });

  const { data: eligible = [], isLoading } = useQuery({
    queryKey: ["draft-eligible"],
    queryFn: () => getDraftEligible({ limit: 50 }),
  });

  const gradedIds = new Set(board.map((p: any) => p.player_id));

  async function grade(playerId: number) {
    setGradingId(playerId);
    try {
      await gradeDraftProspect(playerId, { draft_year: 2027 });
      queryClient.invalidateQueries({ queryKey: ["draft-board"] });
    } finally {
      setGradingId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Draft Board</h1>
      <p className="text-gray-400 mb-6 text-sm">
        2027 NFL Draft — real draft-eligible players from current rosters, AI-graded on request.
      </p>

      {board.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Graded Prospects</h2>
          <div className="space-y-3">
            {board.map((p: any) => (
              <div key={p.player_id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-white font-medium">{p.name} <span className="text-gray-500 text-sm">({p.position}, {p.college})</span></p>
                  <div className="text-right">
                    <span className="text-cfb-gold font-bold">Round {p.projected_round ?? "—"}</span>
                    <span className="text-gray-400 text-sm ml-2">{p.grade}</span>
                  </div>
                </div>
                {p.nfl_comparison && <p className="text-sm text-gray-400 mb-1">NFL Comp: {p.nfl_comparison}</p>}
                {p.ai_analysis && <p className="text-sm text-gray-300">{p.ai_analysis}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Draft-Eligible Players</h2>
      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : eligible.length === 0 ? (
        <p className="text-gray-500">No draft-eligible players found yet. Run data ingestion first (see README).</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">Name</th>
              <th className="py-1.5 font-medium">Pos</th>
              <th className="py-1.5 font-medium">College</th>
              <th className="py-1.5 font-medium">Class</th>
              <th className="py-1.5 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {eligible.filter((p: any) => !gradedIds.has(p.player_id)).map((p: any) => (
              <tr key={p.player_id} className="border-b border-gray-900">
                <td className="py-1.5 text-white">{p.name}</td>
                <td className="py-1.5 text-gray-300">{p.position}</td>
                <td className="py-1.5 text-gray-300">
                  {p.college}
                  {p.former_college && <span className="text-xs text-cfb-gold ml-1">(transferred from {p.former_college})</span>}
                </td>
                <td className="py-1.5 text-gray-300">{p.class_year}</td>
                <td className="py-1.5 text-right">
                  <button
                    onClick={() => grade(p.player_id)}
                    disabled={gradingId === p.player_id}
                    className="bg-cfb-crimson hover:bg-red-700 text-white text-xs px-3 py-1.5 rounded disabled:opacity-50"
                  >
                    {gradingId === p.player_id ? "Grading..." : "AI Grade"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
