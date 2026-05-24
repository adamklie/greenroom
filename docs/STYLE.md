# Documentation Style

Three principles: **clarity, conciseness, layout**.

---

## Headings

- **H1** — file title only. One per file.
- **H2** — main sections.
- **H3** — sparingly, for sub-sections inside a long H2.
- **H4+** — never. If you need it, split the doc.

## Sentences

Short. Active voice. Cut every word that doesn't change meaning.

| Wrong | Right |
|---|---|
| "The system has been designed to..." | "The system..." |
| "It is important to note that..." | (just say the thing) |
| "We've worked hard to ensure that..." | (delete) |
| "delightful experience" | (delete) |

## Layout

| Use | When |
|---|---|
| **Tables** | Reference info, comparisons, "X means Y" |
| **Bullets** | Lists of 3+ items, parallel structures |
| **Code blocks** | Commands, paths, file contents, env vars |
| **Prose** | Explaining concepts; transitions between sections |

Generous whitespace between sections. Horizontal rules (`---`) only between major top-level sections, not between every H2.

## Length

| Doc type | Max lines |
|---|---|
| User-facing (USER_GUIDE, DEMO_SCRIPT) | 300 |
| Operator (DEPLOYMENT, MIGRATIONS) | 300 |
| Engineer (ARCHITECTURE, SCHEMAS) | 500 |
| Reference/cheat sheet | 100 |

If you'd exceed, split into single-concept files.

## Links

Always relative paths.

| Good | Bad |
|---|---|
| `[ARCHITECTURE.md](ARCHITECTURE.md)` | `[ARCHITECTURE.md](./ARCHITECTURE.md)` (extra `./`) |
| `[main README](../README.md)` | `[main README](https://github.com/adamklie/greenroom/blob/main/README.md)` |
| `[#5-storage-layout](ARCHITECTURE.md#5-storage-layout)` | `[storage section](ARCHITECTURE.md#storage)` (anchor doesn't match) |

Relative links work locally, on GitHub, and in a future mkdocs site. Absolute URLs break when the repo moves.

## Filenames

- `SCREAMING_SNAKE_CASE.md`
- One concept per file
- File name = concept (`DEPLOYMENT.md`, not `HOW_TO_DEPLOY.md`)
- New file requires asking: "could this go in an existing doc instead?"

## Tone

Friendly + precise. Like a smart colleague explaining something at a whiteboard, not a vendor selling something.

| Avoid | Prefer |
|---|---|
| "powerful" | (just say what it does) |
| "best-in-class" | (delete) |
| "seamless" | (delete) |
| "robust" | (delete) |
| "delightful" | (delete) |
| "easy" | (delete — if it's easy, the steps prove it) |

If something is broken, say so plainly with a fix or a TODO.

## Tables

Headers in title case. Left-align text columns. Don't over-format with bold inside cells — the table structure is the visual anchor.

## Code blocks

- Use fenced ``` with a language tag (` ```bash `, ` ```python `, ` ```sql `).
- Bash blocks should be copy-paste-runnable when possible (real paths, real flags).
- Don't paste enormous code blocks; link to the file or to a GitHub permalink.

## Doc starts

No "what this is / who's it for" preamble. The title + first paragraph should make both obvious. If you can't, the title is wrong.

**Don't write:**

> # Auth
>
> ## What this is
>
> This document describes the authentication system.
>
> ## Who's it for
>
> Developers working on auth-related code.

**Write:**

> # Auth
>
> Magic-link login with JWT cookies. Three roles. Token lifetime 15 min, cookie lifetime 7 days. See [ARCHITECTURE.md#auth](ARCHITECTURE.md#6-auth-model) for the request flow.

## When in doubt

Cut, don't add. The best version of a doc is the shortest one that still answers the question.
