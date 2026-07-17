"use client";
import { useQuery } from "@tanstack/react-query";
import { getStandings, getRankings } from "@/lib/api";

export default function StandingsPage() {
  const { data: standings = {}, isLoading } = useQuery({
    queryKey: ["standings"],
    queryFn: () => getStandings(),
  });
  const { data: rankings = [] } = useQuery({
    queryKey: ["rankings"],
    queryFn: () => getRankings(),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-4">Standings</h1>

      {rankings.length > 0 && (
        <div className="mb-8 bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-gray-400 uppercase mb-3">AP Top 25</h2>
          <ol className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1">
            {rankings.map((r: any) => (
              <li key={r.rank} className="text-sm text-gray-200 flex justify-between">
                <span>#{r.rank} {r.school}</span>
                <span className="text-gray-500">{r.record}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : Object.keys(standings).length === 0 ? (
        <p className="text-gray-500">No standings data yet. Run data ingestion first (see README).</p>
      ) : (
        Object.entries(standings).map(([conf, teams]: [string, any]) => (
          <div key={conf} className="mb-6">
            <h2 className="text-sm font-semibold text-gray-400 uppercase mb-2">{conf}</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="py-1.5 font-medium">Team</th>
                  <th className="py-1.5 font-medium text-right">Overall</th>
                  <th className="py-1.5 font-medium text-right">Conf</th>
                  <th className="py-1.5 font-medium text-right">SP+</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((t: any) => (
                  <tr key={t.school} className="border-b border-gray-900">
                    <td className="py-1.5 text-gray-200">
                      {t.ap_rank && <span className="text-cfb-gold mr-1">#{t.ap_rank}</span>}
                      {t.school}
                    </td>
                    <td className="py-1.5 text-right text-gray-300">{t.wins}-{t.losses}</td>
                    <td className="py-1.5 text-right text-gray-300">{t.conference_wins}-{t.conference_losses}</td>
                    <td className="py-1.5 text-right text-gray-300">{t.sp_rating ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}
