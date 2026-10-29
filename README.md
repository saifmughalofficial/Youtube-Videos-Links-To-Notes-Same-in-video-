# Youtube Lectures Links To Notes

Paste a teacher's YouTube lecture links (videos, shorts, playlists — as many as you like) and get
the questions and solutions the teacher **wrote**, cleanly typed, in one **PDF / Word / text** file.
No talk, no pictures, no links, no sign-up for students.

## How it works

1. Each video's picture is downloaded at the best quality available between 240p and 720p.
2. The app "pauses" the video by itself: it finds every moment a page / board / screen is fullest —
   just before it is turned, wiped or scrolled — and keeps that still. A hand resting on the page is
   not mistaken for a page turn, and a second view is kept when the hand hides part of the page.
3. Each still is zoomed to the writing, upscaled, contrast-boosted and sharpened.
4. A free vision model (Google Gemini) reads the stills and writes out the question statements and
   every solution line exactly as written. Blurry digits are decided using the maths itself. Nothing
   is solved, added or summarised.
5. All lectures end up in one document, in link order. Finished lectures are cached, so a repeated
   link is instant.

## Built for a whole class (100 students)

- Up to **50 links** per paste; lectures up to **2 hours** long.
- **One shared line** for every user: only a few lectures are worked on at once (`NOTES_WORKERS`,
  default 2), so the free server never runs out of memory.
- **Fair turns:** users are served one lecture each, round and round — a 50-link paste never blocks
  a 2-link paste. Each link shows its place in the line.
- **Each lecture is made once:** if 60 students paste the same lecture, it is read once and all 60 get it.
- **Download what's ready:** finished lectures can be downloaded while the rest are still being made.
- **Come back later:** the page link holds the job for 12 hours, so the tab can be closed.
- **Several keys:** `GEMINI_API_KEY = "key1,key2"`; a key that is full for the minute hands the request
  to the next one.
- **Backup reader:** add `GROQ_API_KEY = "gsk_…,gsk_…"` (free at console.groq.com). When every Gemini key is
  used up or busy, the pages are read by Groq (`qwen/qwen3.8-27b`, a few pages per request) instead.
  Videos that can't be downloaded are read straight from YouTube, which only Gemini can do.
- With a paid (billing-enabled) key, add `NOTES_MIN_GAP = "0.5"` and `NOTES_WORKERS = "3"` to the secrets
  for faster reading.

If YouTube blocks the download on a server, the model watches the video straight from YouTube instead.

## One-time free key (the app owner, not students)

1. https://aistudio.google.com/apikey → sign in → **Create API key** (free, no card).
2. PC: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste the key.
3. Streamlit Cloud: App → **Settings → Secrets** → `GEMINI_API_KEY = "AIza..."`.

Several keys separated by commas are used in turn (more lectures per day).

## Run on your PC

```
pip install -r requirements.txt
streamlit run app.py --server.port 8806
```
Opens on http://localhost:8806. (Don't put the port in `.streamlit/config.toml` — Streamlit Cloud needs its own port.)

## Deploy on Streamlit Community Cloud

Push this folder to GitHub (`secrets.toml` is git-ignored) → share.streamlit.io → **New app** →
main file `app.py` → add the secret → **Deploy**.

## Files

| File | What it is |
|---|---|
| `app.py` | The interface (black theme, splash, About) |
| `notes_engine.py` | Download, page detection, enhancement, reading, PDF/Word/text export |
| `test_notes_engine.py` | 42 offline checks incl. a synthetic notebook video: `python -m pytest -q` |
| `fonts/` | DejaVu fonts so maths symbols print correctly in the PDF |
