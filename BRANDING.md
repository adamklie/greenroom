# Greenroom branding assets

Four files, all built against your real `App.tsx` nav and `index.css` tokens
(`--accent` = `#10b981` / `#059669`, `--yellow` = `#eab308` / `#ca8a04`).

| File | Goes in | Purpose |
|------|---------|---------|
| `GreenroomIcons.tsx` | `frontend/src/components/` | The 9 content-tab icons + brand mark + logo lockup |
| `favicon.svg` | `frontend/public/` (replace) | Browser tab icon — already referenced by `index.html` |
| `greenroom-wordmark.svg` | repo root or `docs/` | Static logo for the README header |
| `BRANDING.md` | (this file) | Integration notes + badges |

---

## 1. Tab icons

The icons draw their green with `currentColor`, so they inherit the same
active/muted color your `NavLink` already sets — no behavior change versus
lucide. The `--yellow` accent stays constant for the Greenroom pop. They take
the same `size` prop your render uses (`<Icon size={18} />`).

Custom marks cover the nine **content** tabs; **utility** tabs keep their
lucide icons. Updated `navItems` in `App.tsx`:

```tsx
import {
  DashboardIcon, ImportIcon, LibraryIcon, CoversIcon, OriginalsIcon,
  IdeasIcon, SetlistsIcon, SessionsIcon, ProcessIcon,
} from "./components/GreenroomIcons";
// keep these lucide imports for the utility tabs:
import { MessageSquare, Database, Trash2, Settings2 } from "lucide-react";

const navItems = [
  { to: "/",          icon: DashboardIcon, label: "Dashboard" },
  { to: "/import",    icon: ImportIcon,    label: "Import" },
  { to: "/library",   icon: LibraryIcon,   label: "Library" },
  { to: "/covers",    icon: CoversIcon,    label: "Covers" },
  { to: "/originals", icon: OriginalsIcon, label: "Originals" },
  { to: "/ideas",     icon: IdeasIcon,     label: "Ideas" },
  { to: "/setlists",  icon: SetlistsIcon,  label: "Setlists" },
  { to: "/sessions",  icon: SessionsIcon,  label: "Sessions" },
  { to: "/process",   icon: ProcessIcon,   label: "Process" },
  { to: "/feedback",  icon: MessageSquare, label: "Feedback" },
  { to: "/schemas",   icon: Database,      label: "Schemas", adminOnly: true },
  { to: "/trash",     icon: Trash2,        label: "Trash & Cleanup" },
  { to: "/settings",  icon: Settings2,     label: "Settings" },
];
```

If the constant yellow on inactive items ever feels busy, change `const Y` in
`GreenroomIcons.tsx` from `"var(--yellow, #eab308)"` to `"currentColor"` for a
clean monochrome set.

## 2. Sidebar header

Replace the placeholder glyph + `<h1>Greenroom</h1>` block with the lockup:

```tsx
import { GreenroomLogo } from "./components/GreenroomIcons";

// ...inside the header div (keeps your tagline):
<GreenroomLogo size={22} />
<p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
  Song record keeping
</p>
```

`GreenroomLogo` defaults to all-green (`color: var(--accent)`) to match your
current title. For a two-tone look (green mark, ink wordmark) pass
`style={{ color: "var(--text)" }}`.

## 3. Favicon

`index.html` already has `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />`,
so just drop the new `favicon.svg` into `frontend/public/`, replacing the old one.

## 4. README badges

Greenroom-green shields for the stack actually in `package.json`:

```md
![React](https://img.shields.io/badge/React-10b981?style=flat-square&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-10b981?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-10b981?style=flat-square&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-10b981?style=flat-square&logo=tailwindcss&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-10b981?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-10b981?style=flat-square&logo=sqlite&logoColor=white)
```

A logo header for the top of the README:

```md
<p align="center">
  <img src="./greenroom-wordmark.svg" alt="Greenroom" height="56" />
</p>
<p align="center"><em>The Google Drive for musicians — songbook, recording library, and practice diary.</em></p>
```

(Adjust the FastAPI/SQLite badges to your actual backend if it differs.)

---

### Color tokens (already in your `index.css`)

| Token | Dark | Light |
|-------|------|-------|
| `--accent` (green) | `#10b981` | `#059669` |
| `--yellow` (accent)| `#eab308` | `#ca8a04` |
