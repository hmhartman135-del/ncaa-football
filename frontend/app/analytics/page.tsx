"use client";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import Link from "next/link";
import { getMetrics, getLeaderboard, getTeamMetrics, getTeamFullStats, getTeamStatsAnalysis, getTeamStatRankings, getTeams } from "@/lib/api";

type Tab = "team" | "team-rankings" | "player-rankings";
const SEASONS = [2026, 2027];

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>("team");
  const [season, setSeason] = useState(2026);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Analytics</h1>
      <p className="text-gray-400 mb-6 text-sm">
        Advanced team &amp; player metrics, sourced from CollegeFootballData.
        {season === 2027 && " 2027 season hasn't started — nothing to show yet, but the tab's here for when it does."}
      </p>

      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-2">
          {(["team", "team-rankings", "player-rankings"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-sm px-3 py-1.5 rounded ${tab === t ? "bg-cfb-crimson text-white" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
            >
              {t === "team" ? "Team Stats" : t === "team-rankings" ? "Team Rankings" : "Player Rankings"}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {SEASONS.map((y) => (
            <button
              key={y}
              onClick={() => setSeason(y)}
              className={`text-sm px-3 py-1.5 rounded ${season === y ? "bg-cfb-gold text-black font-medium" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
            >
              {y} Season
            </button>
          ))}
        </div>
      </div>

      {tab === "team" && <TeamStatsTab season={season} />}
      {tab === "team-rankings" && <TeamRankingsTab season={season} />}
      {tab === "player-rankings" && <PlayerRankingsTab season={season} />}
    </div>
  );
}

function StatRow({ label, offense, defense, fmt }: { label: string; offense: any; defense: any; fmt?: (v: any) => string }) {
  const f = fmt ?? ((v: any) => (v === null || v === undefined ? "—" : typeof v === "number" ? v.toFixed(3).replace(/\.?0+$/, "") || "0" : v));
  return (
    <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-gray-900 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-white text-right tabular-nums">{f(offense)}</span>
      <span className="text-gray-300 text-right tabular-nums">{f(defense)}</span>
    </div>
  );
}

function TeamStatsTab({ season }: { season: number }) {
  const [team, setTeam] = useState("");
  const [submittedTeam, setSubmittedTeam] = useState("");
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    setAnalysis(null);
  }, [season, submittedTeam]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["team-full-stats", submittedTeam, season],
    queryFn: () => getTeamFullStats(submittedTeam, { season }),
    enabled: !!submittedTeam,
  });

  const adv = data?.advanced;

  async function runAnalysis() {
    if (!submittedTeam) return;
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const res = await getTeamStatsAnalysis(submittedTeam, { season });
      setAnalysis(res.ai_analysis);
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div>
      <form
        className="flex gap-3 mb-6"
        onSubmit={(e) => {
          e.preventDefault();
          setAnalysis(null);
          setSubmittedTeam(team);
        }}
      >
        <input
          className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm flex-1 max-w-md"
          placeholder="Team name (e.g. Tulane)..."
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        />
        <button type="submit" className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded">
          Load
        </button>
      </form>

      {isLoading && <p className="text-gray-500">Loading...</p>}
      {isError && <p className="text-gray-500">Couldn&apos;t load stats for &quot;{submittedTeam}&quot;.</p>}

      {data && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <p className="text-xs text-gray-500">
              {adv
                ? `Stats from the ${data.stats_season} season (most recent with played games) · roster from ${data.roster_season ?? "—"}`
                : `No ${season} season stats yet — ${season > data.stats_season ? "season hasn't started" : "check back once games are played"}.`}
            </p>
            <button
              onClick={runAnalysis}
              disabled={analyzing || !adv}
              className="bg-gray-800 hover:bg-gray-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50 whitespace-nowrap"
              title={!adv ? "No stats to analyze yet" : undefined}
            >
              {analyzing ? "Analyzing..." : "AI Analysis"}
            </button>
          </div>

          {analysis && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-200 mb-6">
              {analysis}
            </div>
          )}

          {adv ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-10 mb-8">
              <div>
                <div className="grid grid-cols-3 gap-2 pb-2 mb-1 border-b border-gray-800 text-xs text-gray-500 uppercase font-medium">
                  <span>Team Metrics</span>
                  <span className="text-right">Offense</span>
                  <span className="text-right">Defense</span>
                </div>
                <StatRow label="PPA / play" offense={adv.offense?.ppa} defense={adv.defense?.ppa} />
                <StatRow label="Success Rate" offense={adv.offense?.successRate} defense={adv.defense?.successRate} />
                <StatRow label="Explosiveness" offense={adv.offense?.explosiveness} defense={adv.defense?.explosiveness} />
                <StatRow label="Pts / Opportunity" offense={adv.offense?.pointsPerOpportunity} defense={adv.defense?.pointsPerOpportunity} />
                <StatRow label="Total Opportunities" offense={adv.offense?.totalOpportunies} defense={adv.defense?.totalOpportunies} fmt={(v) => v ?? "—"} />
                <StatRow label="Avg Field Position Start" offense={adv.offense?.fieldPosition?.averageStart} defense={adv.defense?.fieldPosition?.averageStart} fmt={(v) => (v == null ? "—" : v.toFixed(1))} />
                <StatRow label="Avg Predicted Pts" offense={adv.offense?.fieldPosition?.averagePredictedPoints} defense={adv.defense?.fieldPosition?.averagePredictedPoints} />
              </div>
              <div>
                <div className="grid grid-cols-3 gap-2 pb-2 mb-1 border-b border-gray-800 text-xs text-gray-500 uppercase font-medium">
                  <span>Rushing / Havoc</span>
                  <span className="text-right">Offense</span>
                  <span className="text-right">Defense</span>
                </div>
                <StatRow label="Power Success" offense={adv.offense?.powerSuccess} defense={adv.defense?.powerSuccess} />
                <StatRow label="Stuff Rate" offense={adv.offense?.stuffRate} defense={adv.defense?.stuffRate} />
                <StatRow label="Line Yards / Rush" offense={adv.offense?.lineYards} defense={adv.defense?.lineYards} />
                <StatRow label="2nd Level Yards / Rush" offense={adv.offense?.secondLevelYards} defense={adv.defense?.secondLevelYards} />
                <StatRow label="Open Field Yards / Rush" offense={adv.offense?.openFieldYards} defense={adv.defense?.openFieldYards} />
                <StatRow label="Havoc Total" offense={adv.offense?.havoc?.total} defense={adv.defense?.havoc?.total} />
                <StatRow label="Havoc Front 7" offense={adv.offense?.havoc?.frontSeven} defense={adv.defense?.havoc?.frontSeven} />
                <StatRow label="Havoc DB" offense={adv.offense?.havoc?.db} defense={adv.defense?.havoc?.db} />
              </div>
            </div>
          ) : (
            <p className="text-gray-500 mb-8">No advanced stats available for this team yet.</p>
          )}

          {Object.keys(data.season_totals || {}).length > 0 && (
            <div className="mb-8">
              <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Season Totals</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(data.season_totals)
                  .filter(([k]) => !k.toLowerCase().endsWith("opponent"))
                  .map(([k, v]: any) => (
                    <div key={k} className="bg-gray-900 border border-gray-800 rounded p-2">
                      <p className="text-xs text-gray-500">{k.replace(/([A-Z])/g, " $1").trim()}</p>
                      <p className="text-white font-medium">{v}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {adv && (
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">Player Metrics — Usage &amp; Production</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="py-1.5 font-medium">Player</th>
                  <th className="py-1.5 font-medium">Pos</th>
                  <th className="py-1.5 font-medium text-right">Overall Usage</th>
                  <th className="py-1.5 font-medium text-right">Pass Usage</th>
                  <th className="py-1.5 font-medium text-right">Rush Usage</th>
                  <th className="py-1.5 font-medium text-right">PPA Total</th>
                  <th className="py-1.5 font-medium text-right">Games</th>
                </tr>
              </thead>
              <tbody>
                {data.players.map((p: any) => (
                  <tr key={p.id} className="border-b border-gray-900 hover:bg-gray-900/50">
                    <td className="py-1.5">
                      <Link href={`/players/${p.id}`} className="text-white hover:text-cfb-crimson">{p.name}</Link>
                    </td>
                    <td className="py-1.5 text-gray-300">{p.position}</td>
                    <td className="py-1.5 text-right tabular-nums text-gray-200">{p.usage ? `${(p.usage.overall * 100).toFixed(1)}%` : "—"}</td>
                    <td className="py-1.5 text-right tabular-nums text-gray-400">{p.usage ? `${(p.usage.pass * 100).toFixed(1)}%` : "—"}</td>
                    <td className="py-1.5 text-right tabular-nums text-gray-400">{p.usage ? `${(p.usage.rush * 100).toFixed(1)}%` : "—"}</td>
                    <td className="py-1.5 text-right tabular-nums text-gray-400">{p.stats?.ppa_total ?? "—"}</td>
                    <td className="py-1.5 text-right tabular-nums text-gray-500">{p.stats?.games ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </div>
      )}
    </div>
  );
}

function TeamRankingsTab({ season }: { season: number }) {
  const [metric, setMetric] = useState("offense_ppa");
  const [conference, setConference] = useState("");

  const { data: teamMetrics = [] } = useQuery({ queryKey: ["team-metrics"], queryFn: getTeamMetrics });
  const { data: teams = [] } = useQuery({ queryKey: ["teams-for-conf"], queryFn: () => getTeams() });
  const conferences = Array.from(new Set(teams.map((t: any) => t.conference).filter(Boolean))).sort() as string[];

  const { data, isLoading } = useQuery({
    queryKey: ["team-rankings", metric, conference, season],
    queryFn: () => getTeamStatRankings({ metric, season, conference: conference || undefined }),
  });

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">
        {data?.better === "low" ? "Lower is better for this metric — rank 1 is the stingiest defense." : "Higher is better for this metric."}
        {data?.season ? ` Season: ${data.season}.` : ""}
      </p>
      <div className="flex gap-3 mb-6">
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={metric} onChange={(e) => setMetric(e.target.value)}>
          {teamMetrics.map((m: any) => <option key={m.key} value={m.key}>{m.label}</option>)}
        </select>
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={conference} onChange={(e) => setConference(e.target.value)}>
          <option value="">All of NCAA</option>
          {conferences.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : !data?.rankings.length ? (
        <p className="text-gray-500">{season === 2027 ? "No 2027 season stats yet — season hasn't started." : "No data available."}</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">#</th>
              <th className="py-1.5 font-medium">Team</th>
              <th className="py-1.5 font-medium">Conference</th>
              <th className="py-1.5 font-medium text-right">{data.label}</th>
            </tr>
          </thead>
          <tbody>
            {data.rankings.map((r: any) => (
              <tr key={r.school} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-1.5 text-gray-400">{r.rank}</td>
                <td className="py-1.5 text-white">{r.school}</td>
                <td className="py-1.5 text-gray-400">{r.conference}</td>
                <td className="py-1.5 text-right text-white font-medium tabular-nums">{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function PlayerRankingsTab({ season }: { season: number }) {
  const [metric, setMetric] = useState("passing_yards");
  const [position, setPosition] = useState("");

  const { data: metrics = [] } = useQuery({ queryKey: ["metrics"], queryFn: getMetrics });
  const { data: leaders = [], isLoading } = useQuery({
    queryKey: ["leaderboard", metric, position, season],
    queryFn: () => getLeaderboard({ metric, season, position: position || undefined }),
  });

  return (
    <div>
      <div className="flex gap-3 mb-6">
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={metric} onChange={(e) => setMetric(e.target.value)}>
          {metrics.map((m: string) => (
            <option key={m} value={m}>{m.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-sm" value={position} onChange={(e) => setPosition(e.target.value)}>
          <option value="">All Positions</option>
          {["QB", "RB", "WR", "TE", "DEF", "OL"].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : leaders.length === 0 ? (
        <p className="text-gray-500">{season === 2027 ? "No 2027 season stats yet — season hasn't started." : "No stats found for this metric yet."}</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="py-1.5 font-medium">#</th>
              <th className="py-1.5 font-medium">Name</th>
              <th className="py-1.5 font-medium">Pos</th>
              <th className="py-1.5 font-medium">Team</th>
              <th className="py-1.5 font-medium text-right">{metric.replace(/_/g, " ")}</th>
            </tr>
          </thead>
          <tbody>
            {leaders.map((l: any) => (
              <tr key={l.player_id} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-1.5 text-gray-500">{l.rank}</td>
                <td className="py-1.5">
                  <Link href={`/players/${l.player_id}`} className="text-white hover:text-cfb-crimson">{l.name}</Link>
                </td>
                <td className="py-1.5 text-gray-300">{l.position}</td>
                <td className="py-1.5 text-gray-300">{l.team}</td>
                <td className="py-1.5 text-right text-gray-200 font-medium tabular-nums">{l.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
