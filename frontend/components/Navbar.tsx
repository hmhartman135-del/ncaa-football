"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/teams", label: "Teams" },
  { href: "/standings", label: "Standings" },
  { href: "/rankings", label: "Rankings" },
  { href: "/matchups", label: "Matchups" },
  { href: "/players", label: "Players" },
  { href: "/analytics", label: "Analytics" },
  { href: "/scouting", label: "Scouting" },
  { href: "/roster", label: "Roster" },
  { href: "/recruiting", label: "Recruiting" },
  { href: "/transfer-portal", label: "Transfer Portal" },
  { href: "/draft", label: "Draft" },
];

export default function Navbar() {
  const pathname = usePathname();
  return (
    <nav className="bg-cfb-navy border-b border-cfb-crimson">
      <div className="max-w-7xl mx-auto px-4 flex items-center gap-1 h-14 overflow-x-auto">
        <span className="text-white font-bold text-lg mr-6 flex-shrink-0">🏈 NCAA Football</span>
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "px-3 py-1.5 rounded text-sm font-medium transition-colors flex-shrink-0",
              pathname === href
                ? "bg-cfb-crimson text-white"
                : "text-gray-300 hover:text-white hover:bg-white/10"
            )}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
