import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, setActiveProject, type Project } from "./api/client";

/**
 * Active-project state for v2 multi-project.
 *
 * Only meaningful when the backend's `multi_project` flag is on (read from
 * /api/health). While it's off the provider stays inert: no active project is
 * set, the API client sends no X-Greenroom-Project header, and the app behaves
 * exactly like V1. Once on, the switcher in the sidebar drives `activeProjectId`,
 * which is persisted to localStorage and pushed into the API client so every
 * request is scoped.
 */
interface ProjectContextValue {
  multiProject: boolean;
  projects: Project[];
  activeProjectId: number | null;
  activeProject: Project | null;
  setActiveProjectId: (id: number) => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

const STORAGE_KEY = "greenroom.activeProjectId";

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health.get(),
    staleTime: Infinity,
  });
  const multiProject = health?.multi_project ?? false;

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(),
    enabled: multiProject,
    staleTime: 60_000,
  });

  const [activeProjectId, setActiveProjectIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });

  // Once projects load, make sure the active id points at one we can access;
  // fall back to the first project otherwise.
  useEffect(() => {
    if (!multiProject || projects.length === 0) return;
    const valid = projects.some((p) => p.id === activeProjectId);
    if (!valid) {
      const next = projects[0].id;
      setActiveProjectIdState(next);
      localStorage.setItem(STORAGE_KEY, String(next));
    }
  }, [multiProject, projects, activeProjectId]);

  const setActiveProjectId = (id: number) => {
    if (id === activeProjectId) return;
    setActiveProjectIdState(id);
    localStorage.setItem(STORAGE_KEY, String(id));
    // Apply the new scope to the API client NOW, before invalidating — otherwise
    // invalidateQueries() fires the refetch synchronously while the header still
    // points at the previous project, and the new view loads stale data.
    setActiveProject(id);
    // Refetch data views under the new scope, but leave the switcher's own
    // queries (projects, health) alone so the sidebar/banner don't churn.
    queryClient.invalidateQueries({
      predicate: (q) => q.queryKey[0] !== "projects" && q.queryKey[0] !== "health",
    });
  };

  // Push the active id into the API client synchronously during render, so the
  // header is set before any child query fires. Inert when the flag is off
  // (activeProjectId stays null → no header).
  const effectiveId = multiProject ? activeProjectId : null;
  setActiveProject(effectiveId);

  const value = useMemo<ProjectContextValue>(() => ({
    multiProject,
    projects,
    activeProjectId: effectiveId,
    activeProject: projects.find((p) => p.id === effectiveId) ?? null,
    setActiveProjectId,
  }), [multiProject, projects, effectiveId]);

  // Hold rendering until we know the flag state, and (when on) until an active
  // project is set — otherwise child queries would fire before the header is
  // ready and the backend would reject them as unscoped.
  if (healthLoading) return null;
  // Wait while projects load, or while they exist but the active one is still
  // being picked. A user with zero projects renders through (the switcher shows
  // an empty state + create button) rather than blanking forever.
  if (multiProject && projectsLoading) return null;
  if (multiProject && projects.length > 0 && effectiveId == null) return null;

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within a ProjectProvider");
  return ctx;
}
