import { Routes, Route, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Music,
  CalendarDays,
  Share2,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Repertoire from "./pages/Repertoire";
import Sessions from "./pages/Sessions";
import ContentPlanner from "./pages/ContentPlanner";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/repertoire", icon: Music, label: "Repertoire" },
  { to: "/sessions", icon: CalendarDays, label: "Sessions" },
  { to: "/content", icon: Share2, label: "Content" },
];

export default function App() {
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
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/repertoire" element={<Repertoire />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/content" element={<ContentPlanner />} />
        </Routes>
      </main>
    </div>
  );
}
