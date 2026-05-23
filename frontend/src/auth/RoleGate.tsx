import type { ReactNode } from "react";
import { useCurrentUser } from "./useCurrentUser";

type Role = "viewer" | "editor" | "admin";

const RANK: Record<Role, number> = { viewer: 1, editor: 2, admin: 3 };

interface Props {
  role: Role;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Render `children` only if the current user is at least `role`.
 *
 * Mirrors the backend's role rank (viewer < editor < admin). Use this to
 * hide mutation UI for read-only viewers — the backend will still 403 if
 * they hit the API directly, so this is purely an affordance.
 */
export function RoleGate({ role, children, fallback = null }: Props) {
  const { user, isLoading } = useCurrentUser();
  if (isLoading) return null;
  if (!user) return <>{fallback}</>;
  if (RANK[user.role] < RANK[role]) return <>{fallback}</>;
  return <>{children}</>;
}
