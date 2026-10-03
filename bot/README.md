# Backnote

A private Telegram study base for university subjects, lectures and online courses.
Built with [aiogram 3](https://docs.aiogram.dev) and [aiogram-dialog 2](https://aiogram-dialog.readthedocs.io).

Friends add lectures and materials; everyone studies from the same base while keeping
personal progress and notes. No grades, deadlines or teachers — just a place to learn.

## Features

- **Whitelist access** — one admin (from `ADMIN_ID`) and a list of members. Strangers who press
  `/start` send an access request that the admin approves with one tap.
- **📘 Subjects** — university subjects (Software Engineering programme) tagged with study
  *year* and *term* (3 terms a year); the list shows the newest term first.
  Code, instructor, ECTS, description, link; archive old terms instead of deleting them.
- **🎯 Courses** — online courses and extra tracks (AI, agents, Coursera/edX, bootcamps…)
  with provider and link. Same structure as subjects.
- **🎓 Lessons** — lecture / seminar / practice / lab / video / reading, auto-numbered per type.
  YouTube recordings show a large preview right in the chat. Prev/next navigation and a
  shareable deep link (`t.me/<bot>?start=l42`).
- **✅ Personal progress** — each member marks lessons as completed independently; progress
  bars per subject, overall stats and a *Continue* button for the next unfinished lesson.
- **🗒 Private notes** per lesson.
- **📎 Materials** — files (PDF, slides, photos, video, audio) or links attached to a subject
  or a lesson. Forward several files at once.
- **🧠 Summaries** — shown as Telegram **Rich Messages** (Bot API 10.1+): headings, tables,
  task lists, LaTeX formulas, collapsible answers. Write them yourself (text or `.md` file) or
  generate them with **Gemini** for free from a public YouTube recording.
- **🔔 Notifications** — members get a message when a new lesson is added
  (can be turned off in Settings).
- **🔎 Search** across subjects, lesson titles, descriptions and summaries.
- **🛡 Admin panel** — members, requests, add by ID/contact/forward, block/remove, broadcast.

## Quick start

```bash
cp .env.example .env        # set BOT_TOKEN and ADMIN_ID
uv sync
uv run backnote             # applies DB migrations, then starts polling
```

Or with Docker:

```bash
docker compose up -d --build
```

The SQLite database lives in `./data/backnote.db`.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | — | Token from @BotFather |
| `ADMIN_ID` | — | Your Telegram user id (the bot answers `/id`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/backnote.db` | SQLAlchemy async URL |
| `TIMEZONE` | `Europe/Kyiv` | Used for dates |
| `GEMINI_API_KEY` | — | Enables AI summaries ([get a free key](https://aistudio.google.com/apikey)) |
| `GEMINI_MODEL` | `gemini-flash-latest` | Any Gemini model that supports video |
| `SUMMARY_LANGUAGE` | `Ukrainian` | Language of AI summaries |

### AI summaries

Gemini can watch public YouTube videos directly by URL; the free tier allows up to 8 hours of
YouTube video per day ([docs](https://ai.google.dev/gemini-api/docs/video-understanding)).
Private or unlisted videos are not supported. Note that on the free tier Google may use the
content to improve its products. Without a key, the summary slot stays available for manual
notes.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run alembic revision --autogenerate -m "describe change"   # after changing models
```

Project layout:

```
backnote/
  __main__.py        entry point (migrations, then the bot)
  config.py          settings from environment / .env
  db/                SQLAlchemy models, engine, migration runner
  migrations/        Alembic migrations
  services/          data access and business logic (no Telegram code)
  formatting.py      HTML / Rich Markdown helpers
  ai.py              Gemini client
  bot/
    dialogs/         aiogram-dialog windows (menu, subjects, lessons, …)
    handlers.py      commands, deep links, notification buttons
    middlewares.py   whitelist gate
    notifier.py      new-lesson notifications
tests/
```

## Ideas for later

- Telegram Mini App with a richer UI.
- Quizzes / flashcards generated from summaries, spaced repetition.
- AI summaries for PDFs and slides, not only videos.
- Grade tracker per subject, exam schedule.
- Import a term schedule from the university LMS / Google Calendar.
