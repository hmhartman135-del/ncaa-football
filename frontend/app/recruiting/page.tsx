"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getRecruits, getTeamRecruits, get247TeamRankings, getTeams } from "@/lib/api";

type Tab = "players" | "team" | "rankings";
const CLASS_YEARS = [2026, 2027];

export default function RecruitingPage() {
  const [tab, setTab] = useState<Tab>("players");
  const [classYear, setClassYear] = useState(2026);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Recruiting</h1>
      <p className="text-gray-400 mb-6 text-sm">
        {classYear} signing class
        {classYear === 2027 && " — very early, most 2027 recruits haven't committed or been ranked by recruiting services yet"}
      </p>

      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-2">
          {(["players", "team", "rankings"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-sm px-3 py-1.5 rounded ${tab === t ? "bg-cfb-crimson text-white" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
            >
              {t === "players" ? "Player Rankings" : t === "team" ? "Team Recruits" : "Team Rankings"}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {CLASS_YEARS.map((y) => (
            <button
              key={y}
              onClick={() => setClassYear(y)}
              className={`text-sm px-3 py-1.5 rounded ${classYear === y ? "bg-cfb-gold text-black font-medium" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
            >
              Class of {y}
            </button>
          ))}
        </div>
      </div>

      {tab === "players" && <PlayersTab classYear={classYear} />}
      {tab === "team" && <TeamTab classYear={classYear} />}
      {tab === "rankings" && <RankingsTab classYear={classYear} />}
    </div>
  );
}

function EmptyClassNote({ classYear }: { classYear: number }) {
  if (classYear !== 2027) return <p className="text-gray-500">No recruiting data found.</p>;
  return (
    <p className="text-gray-500">
      No 2027 recruits in our data source yet. CollegeFootballData hasn&apos;t started tracking this class —
      that&apos;s expected this early (mid-2026); it fills in as recruits commit and get ranked over the next year.
      Check back later, or view the <span className="text-gray-300">Class of 2026</span> tab above for a fully populated class.
    </p>
  );
}

function PlayersTab({ classYear }: { classYear: number }) {
  const [position, setPosition] = useState("");
  const [minStars, setMinStars] = useState("");

  const { data: recruits = [], isLoading } = useQuery({
    queryKey: ["recruits", classYear, position, minStars],
    queryFn: () => getRecruits({ class_year: classYear, position: position || undefined, min_stars: minStars || undefined, limit: 300 }),
  });

  return (
    <div>
      <div className="flex gap-3 mb-6">
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={position} onChange={(e) => setPosition(e.target.value)}>
          <option value="">All Positions</option>
          {["QB", "RB", "WR", "TE", "OT", "IOL", "EDGE", "DL", "LB", "CB", "S", "ATH"].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={minStars} onChange={(e) => setMinStars(e.target.value)}>
          <option value="">Any Stars</option>
          {[5, 4, 3].map((s) => <option key={s} value={s}>{s}+ Stars</option>)}
        </select>
      </div>

      {recruits[0]?.source === "247sports" && (
        <p className="text-xs text-gray-600 mb-4">
          Source: 247Sports.com — manual snapshot fetched {new Date(recruits[0].fetched_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })} (CFBD has no {classYear} recruit data yet).
        </p>
      )}

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : recruits.length === 0 ? (
        <EmptyClassNote classYear={classYear} />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">Natl #</th>
              <th className="py-1.5 font-medium">Name</th>
              <th className="py-1.5 font-medium">Pos</th>
              <th className="py-1.5 font-medium">Pos #</th>
              <th className="py-1.5 font-medium">State #</th>
              <th className="py-1.5 font-medium">Stars</th>
              <th className="py-1.5 font-medium">Hometown</th>
              <th className="py-1.5 font-medium">Committed</th>
            </tr>
          </thead>
          <tbody>
            {recruits.map((r: any) => (
              <tr key={r.id} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-1.5 text-white font-medium">{r.national_rank ?? "—"}</td>
                <td className="py-1.5 text-white">{r.name}</td>
                <td className="py-1.5 text-gray-300">{r.position}</td>
                <td className="py-1.5 text-gray-400">{r.position_rank ?? "—"}</td>
                <td className="py-1.5 text-gray-400">{r.state_rank ?? "—"}</td>
                <td className="py-1.5 text-cfb-gold">{"★".repeat(r.stars || 0)}</td>
                <td className="py-1.5 text-gray-400">{[r.city, r.state_province].filter(Boolean).join(", ") || "—"}</td>
                <td className="py-1.5 text-gray-300">{r.committed_to || "Uncommitted"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function TeamTab({ classYear }: { classYear: number }) {
  const [team, setTeam] = useState("");
  const [submittedTeam, setSubmittedTeam] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["recruiting-team", submittedTeam, classYear],
    queryFn: () => getTeamRecruits(submittedTeam, { class_year: classYear }),
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
        <>
          <p className="text-sm text-gray-400 mb-4">
            {data.recruits.length} commits · class of {classYear}
            {data.average_rating ? ` · avg rating ${data.average_rating}` : ""}
          </p>
          <div className="space-y-2">
            {data.recruits.map((r: any) => (
              <div key={r.id} className="bg-gray-900 border border-gray-800 rounded p-3 text-sm flex items-center justify-between">
                <div>
                  <p className="text-white">{r.name} <span className="text-gray-500">({r.position})</span></p>
                  <p className="text-xs text-gray-500">
                    Natl #{r.national_rank ?? "—"} · Pos #{r.position_rank ?? "—"} · {[r.city, r.state_province].filter(Boolean).join(", ") || "—"}
                  </p>
                </div>
                <span className="text-cfb-gold">{"★".repeat(r.stars || 0)}</span>
              </div>
            ))}
            {data.recruits.length === 0 && <EmptyClassNote classYear={classYear} />}
          </div>
        </>
      )}
    </div>
  );
}

function RankingsTab({ classYear }: { classYear: number }) {
  const [conference, setConference] = useState("");

  const { data: teams = [] } = useQuery({ queryKey: ["teams-for-conf"], queryFn: () => getTeams() });
  const conferences = Array.from(new Set(teams.map((t: any) => t.conference).filter(Boolean))).sort() as string[];

  const { data, isLoading } = useQuery({
    queryKey: ["247-rankings", classYear, conference],
    queryFn: () => get247TeamRankings({ class_year: classYear, conference: conference || undefined }),
  });

  const fetchedLabel = data?.fetched_at
    ? new Date(data.fetched_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : null;

  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">
        Source: 247Sports.com team recruiting rankings (their own points formula — a Gaussian curve weighting each
        team&apos;s best commits most heavily) — top {data?.rankings.length ? "50" : "—"} teams captured per class.
      </p>
      <p className="text-xs text-gray-600 mb-4">
        {fetchedLabel ? `Manual snapshot fetched ${fetchedLabel} — 247Sports has no API, so this doesn't auto-update. Ask to refresh it with fresh 247Sports links when needed.` : ""}
      </p>
      <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm mb-6" value={conference} onChange={(e) => setConference(e.target.value)}>
        <option value="">All of NCAA</option>
        {conferences.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : !data?.rankings.length ? (
        <p className="text-gray-500">
          No 247Sports snapshot loaded for the {classYear} class yet. Paste a 247Sports team-rankings link for this
          class and it can be loaded in.
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">#</th>
              <th className="py-1.5 font-medium">Team</th>
              <th className="py-1.5 font-medium">Conference</th>
              <th className="py-1.5 font-medium">Points</th>
              <th className="py-1.5 font-medium">Commits</th>
              <th className="py-1.5 font-medium">Avg Rating</th>
            </tr>
          </thead>
          <tbody>
            {data.rankings.map((r: any) => (
              <tr key={r.school} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-1.5 text-gray-400">{r.rank}</td>
                <td className="py-1.5 text-white">{r.school}</td>
                <td className="py-1.5 text-gray-400">{r.conference ?? "—"}</td>
                <td className="py-1.5 text-white font-medium">{r.points ?? "—"}</td>
                <td className="py-1.5 text-gray-300">{r.commits ?? "—"}</td>
                <td className="py-1.5 text-gray-300">{r.avg_rating ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
