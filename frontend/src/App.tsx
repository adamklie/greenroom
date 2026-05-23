import { useEffect, useState } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Disc3,
  PenTool,
  Lightbulb,
  CalendarDays,
  ListMusic,
  Sun,
  Moon,
  TrendingUp,
  Scissors,
  Upload,
  FileText,
  Database,
  Settings2,
  MessageSquare,
  LogOut,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Songs from "./pages/Songs";
import Sessions from "./pages/Sessions";
import SetlistBuilder from "./pages/SetlistBuilder";
import Progress from "./pages/Progress";
import ProcessSession from "./pages/ProcessSession";
import Import from "./pages/Import";
import Library from "./pages/Library";
import Schemas from "./pages/Schemas";
import Settings from "./pages/Settings";
import Feedback from "./pages/Feedback";
import Login from "./auth/Login";
import { useCurrentUser } from "./auth/useCurrentUser";
import { api, setForbiddenHandler } from "./api/client";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/library", icon: FileText, label: "Library" },
  { to: "/covers", icon: Disc3, label: "Covers" },
  { to: "/originals", icon: PenTool, label: "Originals" },
  { to: "/ideas", icon: Lightbulb, label: "Ideas" },
  { to: "/sessions", icon: CalendarDays, label: "Sessions" },
  { to: "/process", icon: Scissors, label: "Process" },
  { to: "/progress", icon: TrendingUp, label: "Progress" },
  { to: "/setlists", icon: ListMusic, label: "Setlists" },
  { to: "/import", icon: Upload, label: "Import" },
  { to: "/feedback", icon: MessageSquare, label: "Feedback" },
  { to: "/schemas", icon: Database, label: "Schemas" },
  { to: "/settings", icon: Settings2, label: "Settings" },
];

function getInitialTheme(): "dark" | "light" {
  if (typeof window !== "undefined") {
    return (localStorage.getItem("greenroom-theme") as "dark" | "light") || "dark";
  }
  return "dark";
}

/**
 * Lightweight 403 toast — registered as the global forbidden handler on
 * mount. Shows for 4 seconds when any mutate call returns 403, so viewers
 * get a hint that the action is blocked without a full modal.
 */
function ForbiddenToast() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setForbiddenHandler((msg) => {
      setMessage(msg);
      setTimeout(() => setMessage(null), 4000);
    });
    return () => setForbiddenHandler(null);
  }, []);

  if (!message) return null;
  return (
    <div
      className="fixed bottom-6 right-6 z-50 rounded-lg border px-4 py-3 text-sm shadow-lg"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      {message}
    </div>
  );
}

function AppShell() {
  const [theme, setTheme] = useState<"dark" | "light">(getInitialTheme);
  const { user } = useCurrentUser();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("greenroom-theme", next);
  };

  const onLogout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // best-effort
    }
    queryClient.removeQueries({ queryKey: ["auth", "me"] });
    navigate("/login");
  };

  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
  }

  return (
    <div className="flex h-screen">
      <nav className="w-56 flex-shrink-0 flex flex-col border-r"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="px-5 py-5">
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 48 48" width="22" height="22" style={{ color: "var(--accent)" }} aria-hidden="true">
              <rect x="8" y="14" width="32" height="30" rx="1.5"
                    fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round"/>
              <line x1="24" y1="16" x2="24" y2="42"
                    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
              <circle cx="33" cy="29" r="1.3" fill="currentColor"/>
              <g fill="currentColor">
                <ellipse cx="20" cy="10" rx="3" ry="2.4" transform="rotate(-22 20 10)"/>
                <rect x="22" y="2" width="1.6" height="10"/>
                <path d="M 22.8 2 Q 28 3 26.8 8 Q 25.5 5 22.8 6 Z"/>
              </g>
            </svg>
            <h1 className="text-xl font-bold" style={{ color: "var(--accent)" }}>
              Greenroom
            </h1>
          </div>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Song record keeping
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
          {user && (
            <div className="rounded-lg border px-3 py-2 text-xs"
              style={{ borderColor: "var(--border)" }}>
              <div className="truncate" style={{ color: "var(--text-muted)" }}>
                {user.email}
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="uppercase tracking-wide"
                  style={{ color: "var(--accent)" }}>
                  {user.role}
                </span>
                <button onClick={onLogout}
                  className="flex items-center gap-1 hover:opacity-80"
                  style={{ color: "var(--text-muted)" }}
                  title="Log out">
                  <LogOut size={12} />
                  Log out
                </button>
              </div>
            </div>
          )}
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
          <Route path="/progress" element={<Progress />} />
          <Route path="/setlists" element={<SetlistBuilder />} />
          <Route path="/import" element={<Import />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/schemas" element={<Schemas />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  const { user, isLoading } = useCurrentUser();

  // While the very first /me call is in flight, show nothing. The query is
  // fast (single DB lookup) so flashing the login screen between mount and
  // resolution would be jarring.
  if (isLoading) return null;

  return (
    <>
      <ForbiddenToast />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="*"
          element={user ? <AppShell /> : <Login />}
        />
      </Routes>
    </>
  );
}
