import { useState } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Music,
  CalendarDays,
  Share2,
  RefreshCw,
  ListMusic,
  Sun,
  Moon,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Repertoire from "./pages/Repertoire";
import Sessions from "./pages/Sessions";
import ContentPlanner from "./pages/ContentPlanner";
import SetlistBuilder from "./pages/SetlistBuilder";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/repertoire", icon: Music, label: "Repertoire" },
  { to: "/sessions", icon: CalendarDays, label: "Sessions" },
  { to: "/setlists", icon: ListMusic, label: "Setlists" },
  { to: "/content", icon: Share2, label: "Content" },
];

function getInitialTheme(): "dark" | "light" {
  if (typeof window !== "undefined") {
    return (localStorage.getItem("greenroom-theme") as "dark" | "light") || "dark";
  }
  return "dark";
}

export default function App() {
  const [scanning, setScanning] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(getInitialTheme);
  const queryClient = useQueryClient();

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("greenroom-theme", next);
  };

  // Set initial theme on mount
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
  }

  const rescan = async () => {
    setScanning(true);
    try {
      await fetch("/api/bootstrap/scan", { method: "POST" });
      queryClient.invalidateQueries();
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-56 flex-shrink-0 flex flex-col border-r"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="px-5 py-5">
          <h1 className="text-xl font-bold" style={{ color: "var(--accent)" }}>
            Greenroom
          </h1>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Music Career Manager
          </p>
        </div>
        <div className="flex-1 px-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive ? "font-medium" : ""
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? "var(--bg-hover)" : "transparent",
                color: isActive ? "var(--accent)" : "var(--text-muted)",
              })}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>

        {/* Bottom actions */}
        <div className="px-3 pb-4 space-y-2">
          <button
            onClick={rescan}
            disabled={scanning}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm border transition-colors hover:opacity-80 disabled:opacity-50"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          >
            <RefreshCw size={16} className={scanning ? "animate-spin" : ""} />
            {scanning ? "Scanning..." : "Rescan Files"}
          </button>
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm border transition-colors hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/repertoire" element={<Repertoire />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/setlists" element={<SetlistBuilder />} />
          <Route path="/content" element={<ContentPlanner />} />
        </Routes>
      </main>
    </div>
  );
}
