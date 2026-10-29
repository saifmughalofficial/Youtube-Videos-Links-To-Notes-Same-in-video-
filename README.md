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
5. Up to 3 lectures are processed at once; all of them end up in one document, in link order.
   Finished lectures are cached, so a repeated link is instant.

If YouTube blocks the download on a server, the model watches the video straight from YouTube instead.

## One-time free key (the app owner, not students)

1. https://aistudio.google.com/apikey → sign in → **Create API key** (free, no card).
2. PC: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste the key.
3. Streamlit Cloud: App → **Settings → Secrets** → `GEMINI_API_KEY = "AIza..."`.

Several keys separated by commas are used in turn (more lectures per day).

## Run on your PC

```
pip install -r requirements.txt
streamlit run app.py
```
Opens on http://localhost:8806.

## Deploy on Streamlit Community Cloud

Push this folder to GitHub (`secrets.toml` is git-ignored) → share.streamlit.io → **New app** →
main file `app.py` → add the secret → **Deploy**.

## Files

| File | What it is |
|---|---|
| `app.py` | The interface (black theme, splash, About) |
| `notes_engine.py` | Download, page detection, enhancement, reading, PDF/Word/text export |
| `test_notes_engine.py` | 41 offline checks incl. a synthetic notebook video: `python -m pytest -q` |
| `fonts/` | DejaVu fonts so maths symbols print correctly in the PDF |
