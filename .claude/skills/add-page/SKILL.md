---
description: Scaffold a new React page, register it in App.tsx (imports + sidebar + route), and optionally wire up an API client function. Triggers on "add a new page for X", "create a Gigs page", "scaffold a frontend page", "add X to the sidebar". Usage: /add-page <name>
---

# /add-page

Scaffold a new frontend page end-to-end: page component file, three-place patch to `App.tsx`, optional API client wiring. Mirrors the conventions in `frontend/src/pages/Songs.tsx`.

## Instructions

### 1. Gather the inputs

Ask the user (don't guess):

1. **Page name.** PascalCase derived from the argument. `gigs` → `Gigs`. If ambiguous, ask.
2. **Route path.** Default = kebab-case of the arg (`/gigs`). Confirm.
3. **`lucide-react` icon name.** Default = `FileText`. The user usually has an icon in mind (e.g. `Mic2`, `Calendar`, `Music`). Confirm.
4. **Layout type:** list / detail / form. Defaults to list — that's what most greenroom pages are.
5. **Does this page need a backend endpoint?** If yes, offer to chain `/add-router` first.
6. **Should `frontend/src/api/client.ts` get a typed fetch function?** (yes / no.)

### 2. Create `frontend/src/pages/<Name>.tsx`

Use the template below. The inline comments are intentional — the user is a data analyst learning React, so the template doubles as a reference.

```tsx
// <Name>.tsx — list-style page following the Songs.tsx pattern.
// React conventions used here:
//   - useState for local UI state (search box, filters)
//   - useQuery (TanStack Query) for fetching data from the backend
//   - NavLink/Routes wiring lives in App.tsx, not here
//   - Tailwind classes + CSS variables (--bg, --text, --accent) for theming

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Search } from "lucide-react";

export default function <Name>() {
  // Local UI state — only what this page needs
  const [search, setSearch] = useState("");

  // useQuery: ["<plural-lower>", params] is the cache key.
  // When the key changes, react-query refetches automatically.
  // queryFn is the actual network call. If you don't have an API yet,
  // return `[]` here and replace once /add-router has shipped the endpoint.
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["<plural-lower>", { search }],
    queryFn: () => api.<plural-lower>.list({ search }),
    // If api.<plural-lower>.list doesn't exist yet, swap this for:
    //   queryFn: async () => [] as Array<{ id: number; name: string }>,
  });

  const inputStyle = {
    borderColor: "var(--border)",
    color: "var(--text)",
    background: "var(--bg)",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold"><Name></h2>
      </div>

      <div className="flex gap-3 mb-6 flex-wrap">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-lg border text-sm bg-transparent outline-none"
            style={inputStyle}
          />
        </div>
        <span className="self-center text-sm" style={{ color: "var(--text-muted)" }}>
          {items.length} items
        </span>
      </div>

      {isLoading ? (
        <div style={{ color: "var(--text-muted)" }}>Loading...</div>
      ) : (
        <div className="rounded-xl border overflow-hidden"
          style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
          {/* Replace this with a real table once the data shape is known.
              See Songs.tsx for a fully-built table with sorting + filters. */}
          <div className="p-6 text-sm" style={{ color: "var(--text-muted)" }}>
            No data yet — wire up <code>api.<plural-lower>.list</code> in
            <code>frontend/src/api/client.ts</code>.
          </div>
        </div>
      )}
    </div>
  );
}
```

For a **detail** layout, look at `SongDetailPanel` in `Songs.tsx` — it's a fixed right-side panel with `useQuery({ queryKey: ["<name>", id], queryFn: () => api.<plural>.get(id) })`. For a **form** layout, look at the `showCreate` block in `Songs.tsx` for input + button + mutation pattern.

### 3. Patch `frontend/src/App.tsx` in THREE places

Read `App.tsx` first to see the current state, then apply:

**Edit 1 — imports block.** Add the icon to the `lucide-react` import (alphabetical) and a new line importing the page component:

```tsx
// Inside the existing lucide-react import — add <Icon> alphabetically:
import {
  ...,
  <Icon>,
  ...
} from "lucide-react";

// New line after the existing page imports:
import <Name> from "./pages/<Name>";
```

**Edit 2 — `navItems` array.** Insert a new entry. Where in the list? Ask the user — sidebar order is meaningful. Default = before `Schemas` / `Settings` (those stay at the bottom).

```tsx
{ to: "<route>", icon: <Icon>, label: "<Name>" },
```

**Edit 3 — `<Routes>` block.** Add a route. Match the existing order with the navItems entry.

```tsx
<Route path="<route>" element={<<Name> />} />
```

### 4. (Optional) Add backend wiring

If step 1 said this page needs a backend endpoint, run `/add-router` first (chained). The page's `queryFn` will then resolve cleanly.

### 5. (Optional) Add typed client function to `frontend/src/api/client.ts`

Read the file first. Follow the existing `api.songs.list(params)` pattern — same `{ list, get, create, update, delete }` shape where applicable. Don't invent a new convention.

### 6. Verify

```bash
cd frontend && npx tsc --noEmit
```

If this errors, the most common cause is the `api.<plural>.list` reference in the page template when the client function doesn't exist yet. Either add the client function (step 5) or temporarily swap the `queryFn` for the inline placeholder shown in the template comment.

## Rules

- **Don't** modify other pages. The only files that change are the new page file and three places in `App.tsx`.
- **Don't** invent global state (Zustand, Redux). greenroom uses local `useState` + react-query — match that.
- **Don't** use `fetch` directly. All HTTP goes through `frontend/src/api/client.ts`. If the function you need doesn't exist, add it there.
- CSS variables only (`var(--accent)`, `var(--bg)`, etc.) — no hardcoded colors. Theme toggle in `App.tsx` swaps `data-theme` on `<html>`, and the variables follow.
- Sidebar order matters to the user. Ask where the new page belongs rather than appending to the end.
