import { useQuery } from "@tanstack/react-query";
import { api, type CurrentUser } from "../api/client";

/**
 * Returns the currently signed-in user, or null if unauthed / loading.
 *
 * When the backend has GREENROOM_AUTH_REQUIRED=false (the dev default),
 * /api/auth/me returns a synthetic admin (id=0, email='dev@local'), so this
 * hook always resolves to *some* user in dev. In prod with real auth, an
 * unauthed visitor gets a 401 from /me, which surfaces here as `user=null`
 * + `isLoading=false` — App.tsx uses that to redirect to /login.
 */
export function useCurrentUser(): { user: CurrentUser | null; isLoading: boolean } {
  const { data, isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await api.auth.me();
      } catch {
        // /me throws on 401 — treat as "not signed in" rather than an error.
        return null;
      }
    },
    staleTime: 60_000,
    retry: false,
  });

  return { user: data ?? null, isLoading };
}
