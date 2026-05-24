# Greenroom — Demo Script

A walkthrough for showing the app to a bandmate (or anyone). Target time: **10 minutes**.

URL: <https://greenroom-1.fly.dev>

---

## The 30-second pitch (start here)

> "This is a private app for tracking every song we've ever played, every recording we've ever made, and every practice session we've ever run. Think of it as a digital songbook + recording library + practice diary. Your stuff is in here, mine is in here, we can both add to it, and we both get the same view."

Show the URL. Wait for them to navigate there.

---

## 1 — Signing in (1 min)

1. They land on the login screen. Just an email field.
2. They enter their email → click "Send magic link".
3. They check their inbox → click the link → they're in.

**What to say:**
- "No password to remember. Magic link only."
- "Session lasts 7 days. After that, request another link."
- "If you don't see it, check Spam. Subject line is 'Sign in to Greenroom'."

---

## 2 — Dashboard (1 min)

Show:
- **Focus Songs** at the top — "These are the 3 songs we're actively working on. Tag any song with `focus` to pin it here."
- **The stat tiles** — "226 songs, 31 sessions, X unrated takes."
- **Recent Songs / Recent Audio / Recent Sessions** — "Three columns of what's been added or touched recently."
- **Covers / Originals / Ideas** — "Same 226 songs sliced three ways."

---

## 3 — Library (3 min, the heart of the app)

This is the room you spend the most time in. Click `Library` in the sidebar.

**Show:**
- "**This is every recording we have. 712 files**."
- Use the search bar → type a song title → live filter
- Use "All sources" dropdown → show `apple_music`, `gopro`, `garageband`, `phone`, etc. — "Where the recording came from"
- Use "All roles" → show `recording`, `practice_clip`, `demo`, `backing_track`
- **Click a row → it plays inline.** This is the demo "wow" moment.
- Point out the audio control — "Scrubs, skips, native browser controls."
- Mention: "**The audio doesn't go through our server.** It's a redirect to Cloudflare's storage, so it streams directly to your browser. Egress is free, scales infinitely, can't be slow."

**Show editing:**
- Click the song-link column on an unlinked clip → type a song name → pick from dropdown → it links instantly.
- Click "Notes" to add a note → save.

---

## 4 — Songs (2 min)

Click `Covers` or `Originals` in the sidebar.

**Show:**
- A song with lyrics → "Lyrics are versioned — every edit keeps the previous version."
- Tag chips on a song
- "Click any song → see the full history: all linked recordings, status (idea → learning → rehearsed → polished → recorded), ratings over time."

---

## 5 — Sessions (2 min)

Click `Sessions` in the sidebar.

**Show:**
- A practice session row → "Each row is one practice. The date is in the title."
- Click to expand → "Inside is every take from that session, in order."
- Click the star rating on a take → **changes save instantly**.
- Show the 7 rating dimensions: overall + vocals + guitar + drums + tone + timing + energy. "We can rate any take across any of these. Helps us figure out our best take of a song."

---

## 6 — Settings (30 sec)

Click `Settings` in the sidebar.

**Show:**
- **App Info** — stats, last backup, backend version
- **Data Backup → Export JSON** button → click it → file downloads. "This is your portable backup. Every song, recording, rating, note in one human-readable file. Use it if you ever want to leave the app or just for your own peace of mind."

---

## 7 — Closing pitch (1 min)

> "Everything you change is saved instantly and backed up automatically:
> - Every database change replicates to cloud storage within a second
> - Daily volume snapshots on top of that
> - JSON export any time
>
> If anything looks weird, hard-refresh (Cmd-Shift-R) and tell me. Total cost to run this is about $5/month."

---

## What NOT to click in this demo (yet)

These pages exist but are either owner-only or work-in-progress:

| Page | Why skip |
|---|---|
| **Process** | Video cutting tool. Runs locally only, not in the cloud build |
| **Import** | File upload from a remote machine. For bulk additions, owner runs an ingest script locally |
| **Schemas** | Database structure reference. Advanced; not needed for daily use |
| **Setlists** | Phase 2 feature, may be incomplete |

In the Library, **avoid clicking the trash / delete action** until the cloud-mode robustness sweep is merged. Soft-delete works in the DB but the file-move step may 500. (Update this doc when the sweep lands.)

---

## Q&A prep

**"Where does the data live?"**
- Database (text data): on a tiny private cloud machine in Los Angeles (Fly.io)
- Audio/video files: on Cloudflare R2 cloud storage
- Both are continuously replicated to backups

**"What if I delete something I didn't mean to?"**
- Soft-delete: marked as deleted, file stays. Toggle "Show deleted" in Library to see + restore.
- Database point-in-time recovery: 30-day window
- Daily volume snapshots: 5-day window
- JSON export any time you want a manual backup

**"Can I add new songs / files?"**
- Songs: yes, click "Add Song" in Library
- Lyrics, tags, ratings: yes, anywhere those appear
- Bulk file uploads: for now, owner ingests via local script. Working on a direct upload path

**"How much does this cost to run?"**
- ~$5–7/month all-in (Fly machine + R2 storage + Resend free tier)
- Will stay there until we exceed 3,000 emails/month or many TB

**"What if you (Adam) get hit by a bus?"**
- All data is in standard formats: SQLite + raw audio files in S3-compatible storage + JSON export
- Code is on GitHub (and documented in `docs/ARCHITECTURE.md`)
- Anyone with the credentials could clone and redeploy in an afternoon

---

## After the demo

Ask:
1. "What's missing for you?"
2. "What's confusing?"
3. "How would you describe this app to someone in one sentence?" — useful for refining the pitch

Then make them an admin (or editor — viewer if they just want read access) and let them explore solo.
