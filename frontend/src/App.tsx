import { useEffect, useState } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Sun,
  Moon,
  Database,
  Settings2,
  MessageSquare,
  Trash2,
  LogOut,
} from "lucide-react";
import {
  DashboardIcon,
  ImportIcon,
  LibraryIcon,
  CoversIcon,
  OriginalsIcon,
  IdeasIcon,
  SetlistsIcon,
  SessionsIcon,
  ProcessIcon,
  GreenroomLogo,
} from "./components/GreenroomIcons";
import Dashboard from "./pages/Dashboard";
import Songs from "./pages/Songs";
import Sessions from "./pages/Sessions";
import SetlistBuilder from "./pages/SetlistBuilder";
import ProcessSession from "./pages/ProcessSession";
import Import from "./pages/Import";
import Library from "./pages/Library";
import Schemas from "./pages/Schemas";
import Settings from "./pages/Settings";
import Trash from "./pages/Trash";
import Feedback from "./pages/Feedback";
import Login from "./auth/Login";
import { useCurrentUser } from "./auth/useCurrentUser";
import { api, setForbiddenHandler } from "./api/client";
import { ThemeProvider, useTheme } from "./theme";
import { ProjectProvider, useProject } from "./project";
import ProjectSwitcher from "./components/ProjectSwitcher";

const navItems = [
  { to: "/", icon: DashboardIcon, label: "Dashboard" },
  { to: "/import", icon: ImportIcon, label: "Import" },
  { to: "/library", icon: LibraryIcon, label: "Library" },
  { to: "/covers", icon: CoversIcon, label: "Covers" },
  { to: "/originals", icon: OriginalsIcon, label: "Originals" },
  { to: "/ideas", icon: IdeasIcon, label: "Ideas" },
  { to: "/setlists", icon: SetlistsIcon, label: "Setlists" },
  { to: "/sessions", icon: SessionsIcon, label: "Sessions" },
  { to: "/process", icon: ProcessIcon, label: "Process" },
  { to: "/feedback", icon: MessageSquare, label: "Feedback" },
  { to: "/schemas", icon: Database, label: "Schemas", adminOnly: true },
  { to: "/trash", icon: Trash2, label: "Trash & Cleanup" },
  { to: "/settings", icon: Settings2, label: "Settings" },
];

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
  const { theme, toggleTheme } = useTheme();
  const { user } = useCurrentUser();
  const { multiProject } = useProject();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const onLogout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // best-effort
    }
    queryClient.removeQueries({ queryKey: ["auth", "me"] });
    navigate("/login");
  };

  return (
    <div className="flex h-screen">
      <nav className="w-56 flex-shrink-0 flex flex-col border-r"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="px-5 py-5">
          <GreenroomLogo size={22} />
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Song record keeping
          </p>
        </div>
        {multiProject && (
          <div className="px-3 pb-3">
            <ProjectSwitcher />
          </div>
        )}
        <div className="flex-1 px-3 space-y-1 overflow-y-auto">
          {navItems
            .filter((item) => !("adminOnly" in item) || user?.role === "admin")
            .map(({ to, icon: Icon, label }) => (
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
          <Route path="/setlists" element={<SetlistBuilder />} />
          <Route path="/import" element={<Import />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/schemas" element={<Schemas />} />
          <Route path="/trash" element={<Trash />} />
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
    <ThemeProvider>
      <ForbiddenToast />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="*"
          element={user ? <ProjectProvider><AppShell /></ProjectProvider> : <Login />}
        />
      </Routes>
    </ThemeProvider>
  );
}
