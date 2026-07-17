"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { getPlayers } from "@/lib/api";

const POSITIONS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P"];

export default function PlayersPage() {
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState("");
  const [team, setTeam] = useState("");

  const { data: players = [], isLoading } = useQuery({
    queryKey: ["players", search, position, team],
    queryFn: () => getPlayers({ search: search || undefined, position: position || undefined, team: team || undefined, limit: 200 }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-4">Players</h1>
      <div className="flex gap-3 mb-6 flex-wrap">
        <input
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm flex-1 min-w-[200px]"
          placeholder="Search players..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={position} onChange={(e) => setPosition(e.target.value)}>
          <option value="">All Positions</option>
          {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <input
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm"
          placeholder="Team..."
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        />
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : players.length === 0 ? (
        <p className="text-gray-500">No players found. Run data ingestion first (see README).</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">Name</th>
              <th className="py-1.5 font-medium">Pos</th>
              <th className="py-1.5 font-medium">Team</th>
              <th className="py-1.5 font-medium">Class</th>
              <th className="py-1.5 font-medium">Ht/Wt</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p: any) => (
              <tr key={p.id} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-1.5">
                  <Link href={`/players/${p.id}`} className="text-white hover:text-cfb-crimson">{p.name}</Link>
                </td>
                <td className="py-1.5 text-gray-300">{p.position}</td>
                <td className="py-1.5 text-gray-300">{p.team}</td>
                <td className="py-1.5 text-gray-300">{p.year}</td>
                <td className="py-1.5 text-gray-400">{p.height || "—"}in / {p.weight || "—"}lb</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
