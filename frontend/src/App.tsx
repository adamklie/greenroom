import { useState } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Disc3,
  PenTool,
  Lightbulb,
  CalendarDays,
  Music,
  ListMusic,
  Share2,
  Inbox,
  RefreshCw,
  Sun,
  Moon,
  TrendingUp,
  Scissors,
  Upload,
  CloudUpload,
  FileText,
  Settings2,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Songs from "./pages/Songs";
import Sessions from "./pages/Sessions";
import SetlistBuilder from "./pages/SetlistBuilder";
import ContentPlanner from "./pages/ContentPlanner";
import Triage from "./pages/Triage";
import Discover from "./pages/Discover";
import Progress from "./pages/Progress";
import ProcessSession from "./pages/ProcessSession";
import Import from "./pages/Import";
import Sync from "./pages/Sync";
import Library from "./pages/Library";
import Settings from "./pages/Settings";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/library", icon: FileText, label: "Library" },
  { to: "/covers", icon: Disc3, label: "Covers" },
  { to: "/originals", icon: PenTool, label: "Originals" },
  { to: "/ideas", icon: Lightbulb, label: "Ideas" },
  { to: "/sessions", icon: CalendarDays, label: "Sessions" },
  { to: "/process", icon: Scissors, label: "Process" },
  { to: "/discover", icon: Music, label: "Discover" },
  { to: "/progress", icon: TrendingUp, label: "Progress" },
  { to: "/setlists", icon: ListMusic, label: "Setlists" },
  { to: "/content", icon: Share2, label: "Content" },
  { to: "/import", icon: Upload, label: "Import" },
  { to: "/triage", icon: Inbox, label: "Triage" },
  { to: "/sync", icon: CloudUpload, label: "Sync" },
  { to: "/settings", icon: Settings2, label: "Settings" },
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
      <nav className="w-56 flex-shrink-0 flex flex-col border-r"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="px-5 py-5">
          <h1 className="text-xl font-bold" style={{ color: "var(--accent)" }}>
            Greenroom
          </h1>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Music Portfolio Builder
          </p>
        </div>
        <div className="flex-1 px-3 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive ? "font-medium" : ""}`
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
        <div className="px-3 pb-4 space-y-2">
          <button onClick={rescan} disabled={scanning}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm border hover:opacity-80 disabled:opacity-50"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <RefreshCw size={16} className={scanning ? "animate-spin" : ""} />
            {scanning ? "Scanning..." : "Rescan Files"}
          </button>
          <button onClick={toggleTheme}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm border hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </button>
        </div>
      </nav>

      <main className="flex-1 overflow-y-auto p-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/covers" element={<Songs songType="cover" title="Covers" />} />
          <Route path="/originals" element={<Songs songType="original" title="Originals" />} />
          <Route path="/ideas" element={<Songs songType="idea" title="Ideas" />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/process" element={<ProcessSession />} />
          <Route path="/library" element={<Library />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/setlists" element={<SetlistBuilder />} />
          <Route path="/content" element={<ContentPlanner />} />
          <Route path="/import" element={<Import />} />
          <Route path="/triage" element={<Triage />} />
          <Route path="/sync" element={<Sync />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
