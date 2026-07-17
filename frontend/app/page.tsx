"use client";
import Link from "next/link";

const NAV_CARDS = [
  { href: "/teams", label: "Teams", icon: "🏟️", desc: "FBS Programs · 2026" },
  { href: "/standings", label: "Standings", icon: "📊", desc: "Conference Records" },
  { href: "/rankings", label: "Rankings", icon: "🏆", desc: "AP Top 25 · AI Top 25" },
  { href: "/matchups", label: "Matchups", icon: "🏈", desc: "2026 Schedule · AI Predictions" },
  { href: "/players", label: "Players", icon: "📋", desc: "D1 Rosters" },
  { href: "/analytics", label: "Analytics", icon: "📈", desc: "Leaderboards · Advanced Stats" },
  { href: "/scouting", label: "Scouting", icon: "🔍", desc: "AI Player Reports" },
  { href: "/roster", label: "Roster", icon: "🧩", desc: "Depth Chart · AI Analysis" },
  { href: "/recruiting", label: "Recruiting", icon: "⭐", desc: "2026 & 2027 Classes" },
  { href: "/transfer-portal", label: "Transfer Portal", icon: "🔄", desc: "2026 Cycle" },
  { href: "/draft", label: "Draft Board", icon: "📝", desc: "2027 NFL Draft Prospects" },
];

export default function Dashboard() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">NCAA Football Analytics</h1>
        <p className="text-gray-400 mt-1">
          2026 Preseason · Powered by CollegeFootballData.com + Claude AI
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {NAV_CARDS.map(({ href, label, icon, desc }) => (
          <Link
            key={href}
            href={href}
            className="bg-gray-900 border border-gray-800 hover:border-cfb-crimson rounded-lg p-4 flex items-start gap-3 transition-colors group"
          >
            <span className="text-2xl mt-0.5">{icon}</span>
            <div>
              <p className="font-semibold text-gray-200 group-hover:text-white">{label}</p>
              <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
