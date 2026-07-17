"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { getTeams } from "@/lib/api";

export default function TeamsPage() {
  const [search, setSearch] = useState("");
  const [conference, setConference] = useState("");

  const { data: teams = [], isLoading } = useQuery({
    queryKey: ["teams", search, conference],
    queryFn: () => getTeams({ search: search || undefined, conference: conference || undefined }),
  });

  const conferences = Array.from(new Set(teams.map((t: any) => t.conference).filter(Boolean))).sort();

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-4">Teams</h1>
      <div className="flex gap-3 mb-6">
        <input
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm flex-1"
          placeholder="Search teams..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm"
          value={conference}
          onChange={(e) => setConference(e.target.value)}
        >
          <option value="">All Conferences</option>
          {conferences.map((c: any) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : teams.length === 0 ? (
        <p className="text-gray-500">No teams found. Run data ingestion first (see README).</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {teams.map((t: any) => (
            <Link
              key={t.id}
              href={`/teams/${encodeURIComponent(t.school)}`}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-cfb-crimson transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                {t.logo && <img src={t.logo} alt="" className="w-8 h-8" onError={(e: any) => (e.target.style.display = "none")} />}
                <p className="font-semibold text-white text-sm">{t.school}</p>
              </div>
              <p className="text-xs text-gray-500">{t.conference}</p>
              <p className="text-xs text-gray-400 mt-1">{t.wins ?? 0}-{t.losses ?? 0} ({t.conference_wins ?? 0}-{t.conference_losses ?? 0} conf)</p>
              {t.ap_rank && <p className="text-xs text-cfb-gold mt-1">AP #{t.ap_rank}</p>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
