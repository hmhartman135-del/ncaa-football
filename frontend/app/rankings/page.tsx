"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getRankingWeeks, getApPoll, getAiTop25, generateAiTop25 } from "@/lib/api";

type Tab = "poll" | "ai";

export default function RankingsPage() {
  const [tab, setTab] = useState<Tab>("poll");

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Rankings</h1>
      <p className="text-gray-400 mb-6 text-sm">Top 25 polls and an independent AI-generated ranking.</p>

      <div className="flex gap-2 mb-6">
        {(["poll", "ai"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-sm px-3 py-1.5 rounded ${tab === t ? "bg-cfb-crimson text-white" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
          >
            {t === "poll" ? "AP Top 25" : "AI Top 25"}
          </button>
        ))}
      </div>

      {tab === "poll" && <ApPollTab />}
      {tab === "ai" && <AiTop25Tab />}
    </div>
  );
}

function ApPollTab() {
  const [week, setWeek] = useState<number | null>(null);

  const { data: weeksData } = useQuery({ queryKey: ["ranking-weeks"], queryFn: () => getRankingWeeks() });
  const weeks: number[] = weeksData?.weeks ?? [];

  const { data, isLoading } = useQuery({
    queryKey: ["ap-poll", week],
    queryFn: () => getApPoll(week !== null ? { week } : undefined),
  });

  useEffect(() => {
    if (week === null && data?.week) setWeek(data.week);
  }, [data, week]);

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">
        The real AP Top 25 — the poll ESPN and other major outlets report — live from CollegeFootballData.
        {data?.week ? ` Showing Week ${data.week}.` : ""}
      </p>

      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setWeek(null)}
          className={`text-sm px-3 py-1.5 rounded ${week === null ? "bg-cfb-gold text-black font-medium" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
        >
          Latest
        </button>
        {weeks.map((w) => (
          <button
            key={w}
            onClick={() => setWeek(w)}
            className={`text-sm px-3 py-1.5 rounded ${week === w ? "bg-cfb-crimson text-white" : "bg-gray-900 border border-gray-800 text-gray-400"}`}
          >
            Week {w}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : !data?.rankings.length ? (
        <p className="text-gray-500">
          No AP poll released yet for this week. Preseason polls typically come out in August, right
          before the season starts — check back then, or browse a prior season&apos;s poll if you just want to see it working.
        </p>
      ) : (
        <ol className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {data.rankings.map((r: any) => (
            <li key={r.rank} className="bg-gray-900 border border-gray-800 rounded p-3 flex items-center justify-between text-sm">
              <div>
                <span className="text-cfb-gold font-bold mr-2">#{r.rank}</span>
                <Link href={`/teams/${encodeURIComponent(r.school)}`} className="text-white hover:text-cfb-crimson">{r.school}</Link>
                <span className="text-gray-500 ml-2">{r.conference}</span>
              </div>
              <div className="text-right text-gray-400 text-xs">
                {r.first_place_votes ? `${r.first_place_votes} 1st place` : ""} {r.points ? `· ${r.points} pts` : ""}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function AiTop25Tab() {
  const [generating, setGenerating] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({ queryKey: ["ai-top25"], queryFn: () => getAiTop25() });

  async function generate() {
    setGenerating(true);
    try {
      await generateAiTop25();
      queryClient.invalidateQueries({ queryKey: ["ai-top25"] });
    } finally {
      setGenerating(false);
    }
  }

  const generatedLabel = data?.generated_at
    ? new Date(data.generated_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
    : null;

  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">
        AI-generated, independent of the official polls — ranked using SP+ ratings, this season&apos;s
        record so far, and last season&apos;s record. Not auto-updated; press the button any time in the
        season to get a fresh ranking reflecting the latest results.
      </p>
      {generatedLabel && <p className="text-xs text-gray-600 mb-4">Last generated {generatedLabel}.</p>}

      <button
        onClick={generate}
        disabled={generating}
        className="bg-cfb-crimson hover:bg-red-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50 mb-6"
      >
        {generating ? "Generating..." : data?.rankings?.length ? "Regenerate AI Top 25" : "Generate AI Top 25"}
      </button>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : !data?.rankings?.length ? (
        <p className="text-gray-500">No AI ranking generated yet — click the button above.</p>
      ) : (
        <ol className="space-y-2">
          {data.rankings.map((r: any) => (
            <li key={r.rank} className="bg-gray-900 border border-gray-800 rounded p-3 text-sm">
              <div className="flex items-start gap-3">
                <span className="text-cfb-gold font-bold w-6 flex-shrink-0">#{r.rank}</span>
                <div>
                  <Link href={`/teams/${encodeURIComponent(r.school)}`} className="text-white font-medium hover:text-cfb-crimson">{r.school}</Link>
                  <p className="text-gray-400 text-xs mt-0.5">{r.blurb}</p>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
