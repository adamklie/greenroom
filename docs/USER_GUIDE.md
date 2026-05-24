# User Guide

For the owner and bandmates. If you're an engineer looking for "how does
this work?", read [`ARCHITECTURE.md`](ARCHITECTURE.md) instead.

---

## 1. What is Greenroom?

A private app for tracking your band's songs, recordings, and practice
sessions. Think of it as a digital songbook plus a recording library plus
a practice diary, all in one place. Every audio or video clip you upload
gets cataloged, you can rate takes across multiple dimensions, link
recordings to songs, write lyrics, organize setlists, and pull
guitar-pro tabs in for reference.

---

## 2. How to sign in

1. Go to <https://greenroom-1.fly.dev>.
2. Type your email and hit "Send magic link."
3. Check your inbox for a message titled **"Sign in to Greenroom"**.
4. Click the link. You're in.

A few details worth knowing:

- The link expires after **15 minutes** and can only be used **once**.
  Click it sooner rather than later, and don't forward it to anyone.
- Once you're in, the session cookie keeps you signed in for **7 days**
  before you'll need a new magic link.
- The "If that email is registered…" response is intentional — the app
  won't tell you whether an address has an account, so nobody can use
  the login page to fish for valid emails.
- The owner has to add your email to the user list before any magic
  link will actually be sent. If you never get an email, that's the
  most likely reason.

---

## 3. The pages, in order

The sidebar runs top to bottom in this order. (The route names in
parentheses are the URLs, in case you want to bookmark something.)

- **Dashboard** (`/`) — at-a-glance stats: counts of songs, sessions,
  recordings, what's unrated, recent activity.
- **Library** (`/library`) — every audio / video clip in the system, in
  one big sortable list. Filter by source, role, file type, or "show
  deleted." Click play to stream. Click a row to inline-edit the song
  link, ratings, tags.
- **Covers** (`/covers`) — songs filtered to `type=cover`. Lyrics,
  history of recordings, ratings over time.
- **Originals** (`/originals`) — same view, but `type=original`.
- **Ideas** (`/ideas`) — same view, but `type=idea`. Rough sketches and
  half-formed song seeds live here.
- **Sessions** (`/sessions`) — practice sessions grouped by date. Each
  session expands to show its takes, which are ratable across seven
  dimensions (overall, vocals, guitar, drums, tone, timing, energy).
- **Process** (`/process`) — the video-cutting tool. Carve a long
  rehearsal recording into per-song clips.
- **Progress** (`/progress`) — graphs and trends from the rating data
  (how a song's overall rating has moved over weeks; best/worst takes).
- **Setlists** (`/setlists`) — ordered song collections for performances.
  Build a setlist, drag songs in, see total runtime.
- **Import** (`/import`) — drag-and-drop upload zone for new audio /
  video. See "Adding a new recording" below.
- **Feedback** (`/feedback`) — leave notes for the owner / file bug
  reports against the app itself.
- **Schemas** (`/schemas`) — a developer-oriented reference page that
  dumps the backend's data shapes. Mostly noise unless you're poking
  at the API.
- **Settings** (`/settings`) — app version, total counts, last backup
  timestamp. Light / dark mode lives in the *sidebar* (the sun / moon
  button at the bottom), not on this page.

Note: there's no single "Songs" page right now — `Covers`, `Originals`,
and `Ideas` together cover that ground. Use whichever matches the song
type you care about.

---

## 4. Core workflows

### Adding a new recording

Two ways:

1. **Drag-and-drop (Import page).** Open `/import`. Drag in one or more
   audio (`.m4a`, `.mp3`, `.wav`) or video (`.mp4`, `.mov`) files. For
   each one, pick an existing song from the dropdown or type a new song
   title to create one on the fly. Click "Import" (or "Import all").
   Video files are auto-transcoded to m4a server-side — the original
   format is noted, the audio is what gets stored. Anyone with `editor`
   role can do this.
2. **Bulk CLI import (owner only, for ingesting big folders).**
   `make bootstrap` runs `app.services.bootstrap.run_bootstrap`, which
   scans the iCloud music tree and inserts whatever it finds. This is
   the path that built the initial 712 / 226 / 31 corpus and is mostly
   useful for one-off bulk loads — not the daily workflow.

Either path: every file gets a content-addressed identifier
(10 chars, e.g. `AFE9C7481F`) and the file lands in R2 at
`files/{identifier}.{ext}`. Re-uploading the same file under the same
filename + timestamp would resolve to the same identifier, so duplicates
collapse rather than pile up.

### Rating a take

1. Go to **Sessions** (or **Library** for one-off recordings).
2. Expand a session. Each take shows seven star rows: Overall, Vocals,
   Guitar, Drums, Tone, Timing, Energy. Half-stars supported.
3. Click a star. It saves immediately — no submit button. (The
   `PATCH /api/audio_files/{id}` request is fired on click.)
4. Adjust at any time. The latest value wins.

You can also rate from the Library page; the same star widget appears
when you expand a row.

### Editing song metadata (lyrics, tags, notes)

1. Go to **Covers**, **Originals**, or **Ideas** depending on the song's
   type.
2. Click the song's row to open its detail view.
3. Inline-edit title, key, tempo, tuning, vibe, lyrics, notes, tags.
   Saves on blur. Lyrics aren't versioned in the UI yet, but every
   change is captured in the database's `lyrics_versions` table — ask
   the owner if you ever need to roll back.

### Linking a recording to a song

From **Library**: the "Song" column on each row has an inline picker.
Type the song's title, pick from the autocomplete dropdown, and the link
saves. If the recording wasn't matched on import (often the case for
practice-session takes), this is where you tidy them up.

### Uploading a guitar-pro tab

From a Song detail view: there's a drop zone that accepts `.gp`, `.gp3`,
`.gp4`, `.gp5`, `.gpx`, or `.gp7` files. After upload, the tab renders
in-browser via AlphaTab and stays attached to the song for future
reference. Each song can have multiple tab files (different
arrangements).

### Building a setlist

1. Go to **Setlists** → "New setlist."
2. Give it a name and config (acoustic, electric, etc.).
3. Add songs in performance order. Each entry can carry a
   per-song duration estimate and a note.
4. Total estimated runtime updates as you add.

A dedicated performance-mode view (full-screen, swipe between songs)
is on the roadmap but not built yet.

### Deleting a recording

From **Library**: click the row's trash icon → confirm.

What actually happens: the file is moved into a `_trash/` directory and
the `role` column is set to `"deleted"`. The R2 object is **not**
removed — that means restore is a metadata-only flip, and a stray click
can be undone.

To see deleted rows, tick the "Show deleted" checkbox at the top of
Library.

### Restoring something you deleted

- **Recording (audio_file):** Library → tick "Show deleted" → find the
  row → flip its `role` back via inline edit. (A one-click restore
  button is on the to-do list; for now the inline edit on `role` is the
  path.)
- **Song:** the `Trash` API has dedicated restore endpoints
  (`POST /api/trash/restore/{song_id}` and the `Songs` page surfaces a
  "deleted songs" section via the same data). For audio_files we lean on
  the "Show deleted" filter described above.

### Exporting your data

There's an export endpoint in the backend
(`backend/app/services/backup.export_annotations`) that writes a
timestamped JSON of every song, take, setlist, and tag into the vault's
`exports/` dir — but it's not currently wired to a Settings button in
the cloud build. Use one of:

- Owner running `python -c "from app.services.backup import export_annotations; …"` over `fly ssh console`.
- The auto-snapshots described below (those are the recovery path that
  matters in practice).

---

## 5. Backups — how your data is protected

Multiple, overlapping tiers. You'd have to lose all of them simultaneously
to lose annotations.

| Tier | What | Where | Frequency / retention |
|---|---|---|---|
| **Continuous (Litestream)** | Every DB write streams as WAL frames to R2 within roughly 1 second. | Cloudflare R2, `${R2_DB_BACKUP_BUCKET}/greenroom-db/` | 30 days. |
| **Boot snapshot** | Each time the app starts, a timestamped copy of the live DB lands on the Fly volume. | `/data/vault/backups/greenroom_*.db` on the Fly volume. | Rolling, last 10 kept. |
| **Volume snapshots** | Fly auto-snapshots the volume itself (filesystem-level). | Fly infrastructure. | Approximately daily, with several days' retention. (Defaults to a 5-day window unless changed.) |
| **Media files** | Every audio / video file is content-addressed by hash and lives in its own R2 bucket. Cannot be silently overwritten — the identifier *is* part of the path. | `${R2_BUCKET}/files/AF…ext` | As long as you keep the bucket. |

To restore from Litestream, the owner would `fly ssh console` and run
`litestream restore -if-replica-exists -o /data/greenroom.db -config
/etc/litestream.yml` (the same command the entrypoint uses on a fresh
volume).

---

## 6. What to do if something looks broken

| Symptom | What it usually means | What to do |
|---|---|---|
| Red **"Backend unreachable"** banner at the top of the page | The Fly machine briefly restarted, or your wifi blipped. | Hard-refresh (Cmd+Shift+R). If it persists more than a minute or two, tell the owner. |
| **"Magic link expired"** or **"Invalid or expired link"** | The link is over 15 minutes old, or it's already been clicked once. | Go back to the login page and request a fresh one. |
| Audio button just spins, or you get a 404 in the network tab | The recording's row exists in the DB but the file isn't in R2 yet. During the initial ~33 GB media migration that's normal. | If the bulk upload is still in progress (ask the owner), wait. If it should be there, file a Feedback note with the row ID. |
| A take you rated yesterday looks unrated | Almost certainly a stale browser tab — react-query caches per session. | Refresh the page. If the rating's truly gone, the owner can restore from one of the backup tiers above. |
| You can read pages but every star click flashes "Insufficient role" | Your account is `viewer`, not `editor`. Reads work; mutations are blocked. | Ask the owner to bump you to `editor`. |
| The login page comes back after you sign in | Cookie didn't stick (private window, third-party cookies blocked, etc.). | Try a normal window. If it still fails, send the owner the browser + version. |

---

## 7. Roles, briefly

| Role | Use case |
|---|---|
| `admin` | Everything, including user management eventually. Owner only. |
| `editor` | Can rate, annotate, upload, link, delete, restore. For active bandmates. |
| `viewer` | Read-only — every page renders, but mutations are blocked at the API. Good for friends / family with a "let me see what you're working on" interest. |

The owner sets your role when adding your email. If you need a different
role, ask.

---

## 8. Asking for changes

Bug reports and feature requests go through the **Feedback** page
inside the app. Submissions become real GitHub issues at
<https://github.com/adamklie/greenroom/issues> with the category
(feedback / bug / feature / question) and priority as labels. The owner
(admin) reviews them there. For anything urgent or that needs
back-and-forth, talk to the owner directly.

---

## See also

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — how it all works under the hood, including the magic-link auth flow.
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — for the owner / contributors deploying the app.
