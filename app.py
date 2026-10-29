"""Youtube Lectures Links To Notes — paste YouTube lecture links, get the teacher's writing as clean notes (PDF / Word / text).

Run:  streamlit run app.py --server.port 8806        (opens on http://localhost:8806)
Needs one free Gemini key in .streamlit/secrets.toml (see README).
"""
import base64
import html
import json
import os
import time

import streamlit as st

import notes_engine as nt

st.set_page_config(page_title=nt.APP_NAME, page_icon=":material/edit_note:", layout="centered",
                   initial_sidebar_state="auto")

# Keys from Streamlit secrets reach the engine as environment variables.
try:
    for _k in ("NOTES_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "NOTES_MODEL"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

# --------------------------------------------------------------------------- logo + styles

LOGO_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
<stop offset='0' stop-color='#ec9a7b'/><stop offset='1' stop-color='#c05a39'/></linearGradient></defs>
<rect x='3' y='3' width='58' height='58' rx='17' fill='url(#g)'/>
<g stroke='#fff' stroke-width='3.6' stroke-linecap='round' fill='none'>
<path d='M16 21h23' stroke-dasharray='23' stroke-dashoffset='0'>{a1}</path>
<path d='M16 31h17' stroke-dasharray='17' stroke-dashoffset='0' opacity='.9'>{a2}</path>
<path d='M16 41h10' stroke-dasharray='10' stroke-dashoffset='0' opacity='.8'>{a3}</path></g>
<path d='M47.5 27.5l5 5-14 14-6.6 1.6 1.6-6.6z' fill='#fff'/>
<path d='M44.2 30.8l5 5' stroke='#c05a39' stroke-width='1.6'/>
</svg>"""


def _anim(length: int, delay: float) -> str:
    return (f"<animate attributeName='stroke-dashoffset' from='{length}' to='0' dur='.55s' begin='{delay}s' "
            f"fill='freeze' calcMode='spline' keySplines='.4 0 .2 1'/>")


def logo_uri(animated: bool = False) -> str:
    svg = LOGO_SVG.format(a1=_anim(23, .25) if animated else "", a2=_anim(17, .55) if animated else "",
                          a3=_anim(10, .85) if animated else "")
    if animated:
        svg = svg.replace("stroke-dashoffset='0'>", "stroke-dashoffset='99'>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


CSS = """<style>
:root { --ink: #d97757; --ink-hi: #f0a283; --ink-lo: #b4532f; --paper: #ecebe8; --mute: #8d8b86;
  --card: rgba(24,24,24,.72); --line: rgba(255,255,255,.07); --ease: cubic-bezier(.22,1,.36,1); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; max-width: 800px; }

/* ambient background: drifting warm glows over faint notebook ruling (sits behind the transparent app) */
html, body { background: #0d0d0d; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }
.ink-bg { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
.ink-bg::before { content: ""; position: absolute; inset: 0;
  background: repeating-linear-gradient(180deg, transparent 0 31px, rgba(255,255,255,.022) 31px 32px);
  mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, #000 20%, transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, #000 20%, transparent 75%); }
.ink-bg i { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .5; }
.ink-bg i:nth-child(1) { width: 520px; height: 520px; left: -160px; top: -180px;
  background: radial-gradient(circle, rgba(217,119,87,.38), transparent 65%); animation: inkDrift 22s ease-in-out infinite; }
.ink-bg i:nth-child(2) { width: 460px; height: 460px; right: -170px; top: 28vh;
  background: radial-gradient(circle, rgba(180,83,47,.30), transparent 65%); animation: inkDrift 28s ease-in-out -9s infinite reverse; }
.ink-bg i:nth-child(3) { width: 380px; height: 380px; left: 30%; bottom: -220px;
  background: radial-gradient(circle, rgba(240,162,131,.16), transparent 65%); animation: inkDrift 32s ease-in-out -4s infinite; }

/* home hero */
.ink-hero { text-align: center; margin: 7vh 0 1.6rem; }
.ink-logo { position: relative; width: 62px; height: 62px; margin: 0 auto; animation: inkPop .8s var(--ease) both; }
.ink-logo img { width: 62px; height: 62px; position: relative; z-index: 1;
  filter: drop-shadow(0 8px 22px rgba(217,119,87,.35)); animation: inkFloat 5s ease-in-out 1s infinite; }
.ink-logo::before { content: ""; position: absolute; inset: -14px; border-radius: 26px;
  background: radial-gradient(circle, rgba(217,119,87,.35), transparent 70%); animation: inkGlow 3.2s ease-in-out infinite; }
.ink-dev { color: #a19f99; font-size: .95rem; margin-top: .75rem; animation: inkUp .7s var(--ease) .1s both; }
.ink-dev b { color: #e89a7c; font-weight: 600; }
.ink-done + .ink-dev { margin: 0 0 .2rem; animation-delay: .05s; }
.ink-tag { display: inline-flex; align-items: center; gap: .45rem; margin-top: 1.1rem; padding: .28rem .8rem;
  border: 1px solid rgba(217,119,87,.28); background: rgba(217,119,87,.08); border-radius: 999px;
  color: #e9a68b; font-size: .78rem; letter-spacing: .02em; animation: inkUp .7s var(--ease) .15s both; }
.ink-tag .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-hi); box-shadow: 0 0 0 0 rgba(240,162,131,.6);
  animation: inkPing 1.8s ease-out infinite; }
.ink-hero h1 { font-family: 'Source Serif 4', Georgia, serif; font-weight: 400; font-size: 2.7rem; line-height: 1.12;
  letter-spacing: -.02em; margin: .9rem 0 .55rem; color: var(--paper); padding: 0;
  animation: inkUp .8s var(--ease) .25s both; }
.ink-hero h1 em { font-style: italic; background: linear-gradient(100deg, #f4b59c 0%, #d97757 35%, #ffd2bf 50%, #d97757 65%, #f4b59c 100%);
  background-size: 250% 100%; -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: inkShine 6s linear infinite; }
.ink-hero p { color: #a19f99; font-size: 1.02rem; margin: 0 auto; max-width: 520px; line-height: 1.6;
  animation: inkUp .8s var(--ease) .38s both; }
.ink-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; margin: 1.9rem 0 1.4rem; }
.ink-step { position: relative; background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: .95rem .95rem .9rem; text-align: left; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  transition: transform .35s var(--ease), border-color .35s, box-shadow .35s; animation: inkUp .8s var(--ease) both; }
.ink-step:nth-child(1) { animation-delay: .5s; } .ink-step:nth-child(2) { animation-delay: .62s; }
.ink-step:nth-child(3) { animation-delay: .74s; }
.ink-step:hover { transform: translateY(-3px); border-color: rgba(217,119,87,.35);
  box-shadow: 0 14px 30px -18px rgba(217,119,87,.55); }
.ink-step .ic { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: linear-gradient(135deg, rgba(236,154,123,.22), rgba(192,90,57,.14)); color: var(--ink-hi); margin-bottom: .6rem; }
.ink-step .ic img { width: 19px; height: 19px; }
.ink-step .num { position: absolute; top: .8rem; right: .95rem; color: #4a4845; font-size: .78rem; font-weight: 600; }
.ink-step b { display: block; color: #ecebe8; font-weight: 600; font-size: .92rem; }
.ink-step span { color: var(--mute); font-size: .82rem; line-height: 1.45; }
.ink-hint { text-align: center; color: #6f6d68; font-size: .82rem; margin-top: .7rem; animation: inkUp .8s var(--ease) 1s both; }
.ink-hint b { color: #8d8b86; font-weight: 500; }

/* link box: warm glow ring, brighter while typing */
[data-testid="stChatInput"] { position: relative; border-radius: 18px; animation: inkUp .8s var(--ease) .86s both;
  transition: box-shadow .4s var(--ease); box-shadow: 0 0 0 1px rgba(217,119,87,.18), 0 18px 40px -22px rgba(217,119,87,.5); }
[data-testid="stChatInput"]:focus-within { box-shadow: 0 0 0 1px rgba(217,119,87,.55), 0 0 0 5px rgba(217,119,87,.12),
  0 22px 50px -20px rgba(217,119,87,.65); }

/* sidebar */
.ink-brand { display: flex; align-items: center; gap: .65rem; margin: .1rem 0 .9rem; }
.ink-brand img { width: 32px; height: 32px; transition: transform .5s var(--ease); }
.ink-brand:hover img { transform: rotate(-8deg) scale(1.08); }
.ink-brand span { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.15rem; line-height: 1.25; color: var(--paper); }
[data-testid="stSidebar"] [data-testid^="stBaseButton"],
[data-testid="stSidebar"] [data-testid^="stBaseButton"] > div { justify-content: flex-start; }
[data-testid="stSidebar"] button { transition: transform .25s var(--ease), background .25s, border-color .25s; }
[data-testid="stSidebar"] button:hover { transform: translateX(3px); }

/* working view */
.ink-bubble { margin: .4rem 0 1rem auto; width: fit-content; max-width: 88%;
  background: linear-gradient(135deg, rgba(217,119,87,.2), rgba(217,119,87,.08)); border: 1px solid rgba(217,119,87,.3);
  border-radius: 18px 18px 4px 18px; padding: .55rem 1rem; color: #f3d6ca; font-size: .9rem; line-height: 1.6;
  word-break: break-all; animation: inkSlide .6s var(--ease) both; }
.ink-work { display: flex; align-items: center; gap: 1.2rem; margin: .4rem 0 1rem; animation: inkUp .7s var(--ease) both; }
.ink-work img { width: 108px; flex: none; filter: drop-shadow(0 12px 24px rgba(217,119,87,.25)); }
.ink-work h3 { font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; font-size: 1.45rem; margin: 0; padding: 0; color: var(--paper); }
.ink-work p { margin: .25rem 0 0; color: var(--mute); font-size: .9rem; line-height: 1.5; }
.st-key-ink_progress { background: var(--card); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
[data-testid="stProgressBarTrack"] { height: 9px !important; border-radius: 99px !important; overflow: hidden;
  background: #232323 !important; }
[data-testid="stProgressBarTrack"] > div { position: relative; overflow: hidden; border-radius: 99px;
  background: linear-gradient(90deg, #b4532f, #d97757 55%, #f0a283) !important; transition: transform .9s var(--ease) !important; }
[data-testid="stProgressBarTrack"] > div::after { content: ""; position: absolute; inset: 0;
  background: linear-gradient(100deg, transparent 20%, rgba(255,255,255,.45) 50%, transparent 80%);
  transform: translateX(-100%); animation: inkSweep 1.6s ease-in-out infinite; }
.ink-list { margin: .3rem 0 0; font-size: .88rem; }
.ink-list div { display: flex; align-items: center; gap: .7rem; padding: .42rem 0; border-top: 1px solid #222; color: #b8b6b0; }
.ink-list b { color: #8d8b86; font-weight: 500; min-width: 1.6rem; }
.ink-list .pill { flex: none; font-size: .76rem; padding: .12rem .6rem; border-radius: 999px; display: inline-flex;
  align-items: center; gap: .35rem; border: 1px solid #2c2c2c; color: #8d8b86; }
.ink-list .ok { color: #8fcb9a; border-color: rgba(127,185,138,.35); background: rgba(127,185,138,.08); }
.ink-list .bad { color: #ef8a82; border-color: rgba(229,115,107,.35); background: rgba(229,115,107,.08); }
.ink-list .on { color: #f0a283; border-color: rgba(217,119,87,.4); background: rgba(217,119,87,.1); }
.ink-list .on::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor;
  animation: inkBlink 1.5s ease-in-out infinite; }

/* finished notes */
.ink-done { display: flex; align-items: center; gap: .55rem; color: #8fcb9a; font-size: .82rem; font-weight: 500;
  letter-spacing: .03em; text-transform: uppercase; margin-bottom: .35rem; animation: inkUp .6s var(--ease) both; }
.ink-done img { width: 18px; height: 18px; }
[data-testid="stHeading"] h2 { animation: inkUp .7s var(--ease) .05s both; }
.ink-meta { display: flex; flex-wrap: wrap; gap: .45rem; margin: -.3rem 0 1rem; animation: inkUp .7s var(--ease) .15s both; }
.ink-meta span { color: #b1aea8; font-size: .8rem; padding: .18rem .7rem; border-radius: 999px; background: #1a1a1a;
  border: 1px solid #2a2a2a; }
.ink-meta span:first-child { color: #f0a283; border-color: rgba(217,119,87,.35); background: rgba(217,119,87,.08); }
.st-key-ink_dl { animation: inkUp .7s var(--ease) .25s both; }
.st-key-ink_dl button { transition: transform .3s var(--ease), box-shadow .3s var(--ease) !important; }
.st-key-ink_dl button:hover { transform: translateY(-2px); box-shadow: 0 12px 26px -14px rgba(217,119,87,.7); }
.st-key-ink_notes_box { background: var(--card); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  animation: inkUp .8s var(--ease) .35s both; }
.ink-notes { font-size: 1rem; line-height: 1.65; color: #e6e4df; }
.ink-notes > * { animation: inkUp .6s var(--ease) both; animation-delay: .9s; }
.ink-notes > :nth-child(1) { animation-delay: .4s; } .ink-notes > :nth-child(2) { animation-delay: .47s; }
.ink-notes > :nth-child(3) { animation-delay: .54s; } .ink-notes > :nth-child(4) { animation-delay: .61s; }
.ink-notes > :nth-child(5) { animation-delay: .68s; } .ink-notes > :nth-child(6) { animation-delay: .75s; }
.ink-notes > :nth-child(7) { animation-delay: .82s; }
.ink-notes h2 { font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; font-size: 1.32rem;
  color: #e89a7c; margin: 1.5rem 0 .55rem; padding: 0; }
.ink-notes .lec { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.45rem; color: #f1efea;
  margin: 2rem 0 .4rem; padding-bottom: .45rem; border-bottom: 1px solid #2c2c2c; position: relative; }
.ink-notes .lec::after { content: ""; position: absolute; left: 0; bottom: -1px; width: 64px; height: 2px;
  background: linear-gradient(90deg, var(--ink), transparent); }
.ink-notes .lec:first-child { margin-top: .2rem; }
.ink-notes p { margin: .35rem 0 .55rem; white-space: pre-line; }
.ink-notes .q { background: linear-gradient(180deg, #1a1a1a, #151515); border: 1px solid #2a2a2a; border-left: 3px solid #d97757;
  border-radius: 14px; padding: .8rem 1.05rem .85rem; margin: 1rem 0 .9rem;
  transition: transform .35s var(--ease), border-color .35s, box-shadow .35s; }
.ink-notes .q:hover { transform: translateX(3px); border-color: #3a3a3a; border-left-color: #f0a283;
  box-shadow: 0 16px 34px -24px rgba(217,119,87,.7); }
.ink-notes .qs { font-weight: 600; color: #f1efea; white-space: pre-line; }
.ink-notes .qs b { display: inline-block; color: #f3c3b0; background: rgba(217,119,87,.16); border-radius: 7px;
  padding: 0 .45rem; margin-right: .5rem; font-size: .9em; }
.ink-notes .lbl { color: #8d8b86; font-size: .74rem; text-transform: uppercase; letter-spacing: .08em;
  margin: .7rem 0 .3rem; display: flex; align-items: center; gap: .5rem; }
.ink-notes .lbl::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, #2c2c2c, transparent); }
.ink-notes .st { font-size: .97rem; color: #dcdad5; padding: .14rem 0 .14rem .85rem;
  border-left: 1px solid #333; white-space: pre-wrap; transition: border-color .25s, color .25s; }
.ink-notes .st:hover { border-left-color: var(--ink); color: #f1efea; }
.ink-notes .ans { margin-top: .65rem; font-weight: 600; color: #f6c3ae; display: inline-block; padding: .25rem .7rem;
  border-radius: 9px; background: rgba(217,119,87,.1); border: 1px solid rgba(217,119,87,.25); }
.ink-notes .fm { text-align: center; background: #141414; border: 1px dashed #3a3a3a; border-radius: 10px;
  padding: .55rem .8rem; margin: .7rem 0; white-space: pre-wrap; }
.ink-notes .df b { color: #e89a7c; }

/* about dialog */
.ink-about { text-align: center; }
.ink-about img { width: 64px; height: 64px; animation: inkPop .7s var(--ease) both; filter: drop-shadow(0 8px 20px rgba(217,119,87,.35)); }
.ink-about h3 { font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; margin: .5rem 0 .1rem; }
.ink-about .v { color: #8d8b86; font-size: .85rem; }
.ink-card { background: #171717; border: 1px solid #2a2a2a; border-radius: 14px; padding: .9rem 1rem;
  margin-top: .9rem; text-align: left; line-height: 1.7; animation: inkUp .6s var(--ease) both; }
.ink-card:nth-of-type(2) { animation-delay: .12s; }
.ink-card a { color: #e89a7c; text-decoration: none; }
.ink-card .k { color: #8d8b86; font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; }

/* splash (first visit) */
.ink-splash { position: fixed; inset: 0; z-index: 999999; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: .3rem; background: radial-gradient(ellipse at 50% 42%, #1c1410 0%, #0d0d0d 60%);
  animation: inkOut .8s ease 3.6s forwards; }
.ink-splash .lg { position: relative; width: 92px; height: 92px; display: grid; place-items: center; }
.ink-splash .lg img { width: 86px; height: 86px; position: relative; z-index: 1; animation: inkPop .8s cubic-bezier(.2,.9,.3,1.2) both;
  filter: drop-shadow(0 10px 30px rgba(217,119,87,.45)); }
.ink-splash .lg i { position: absolute; inset: 0; border-radius: 28px; border: 1.5px solid rgba(217,119,87,.55);
  animation: inkRing 2.2s ease-out .3s infinite; }
.ink-splash .lg i + i { animation-delay: 1.4s; }
.ink-splash .n { font-family: 'Source Serif 4', Georgia, serif; font-size: 2rem; color: #ecebe8;
  margin-top: 1rem; animation: inkUp .7s var(--ease) .35s both; }
.ink-splash .t { color: #8d8b86; font-size: .95rem; animation: inkUp .7s var(--ease) .5s both; }
.ink-splash .bar { width: 160px; height: 3px; border-radius: 9px; background: #222; margin-top: 1.6rem; overflow: hidden;
  animation: inkUp .6s var(--ease) .6s both; }
.ink-splash .bar::after { content: ""; display: block; height: 100%; width: 100%; transform-origin: left;
  background: linear-gradient(90deg, #b4532f, #f0a283); animation: inkFill 2.8s var(--ease) .7s both; }
.ink-splash .c { margin-top: 2rem; text-align: center; color: #9a9893; font-size: .85rem; line-height: 1.6;
  animation: inkUp .7s var(--ease) .9s both; }
.ink-splash .c b { color: #e89a7c; font-weight: 600; }

@keyframes inkPop { from { transform: scale(.6); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes inkUp { from { transform: translateY(14px); opacity: 0; filter: blur(4px); } to { transform: none; opacity: 1; filter: none; } }
@keyframes inkSlide { from { transform: translateX(24px); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes inkOut { to { opacity: 0; visibility: hidden; } }
@keyframes inkDrift { 0%,100% { transform: translate(0,0) scale(1); } 33% { transform: translate(60px,40px) scale(1.1); }
  66% { transform: translate(-40px,70px) scale(.94); } }
@keyframes inkFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@keyframes inkGlow { 0%,100% { opacity: .55; transform: scale(.92); } 50% { opacity: 1; transform: scale(1.06); } }
@keyframes inkShine { to { background-position: -250% 0; } }
@keyframes inkPing { 0% { box-shadow: 0 0 0 0 rgba(240,162,131,.6); } 100% { box-shadow: 0 0 0 8px rgba(240,162,131,0); } }
@keyframes inkSweep { to { transform: translateX(100%); } }
@keyframes inkBlink { 0%,100% { opacity: 1; } 50% { opacity: .25; } }
@keyframes inkRing { from { transform: scale(.9); opacity: .9; } to { transform: scale(1.7); opacity: 0; } }
@keyframes inkFill { from { transform: scaleX(0); } to { transform: scaleX(1); } }

@media (max-width: 640px) {
  .ink-hero h1 { font-size: 2.05rem; }
  .ink-steps { grid-template-columns: 1fr; }
  .ink-work img { width: 84px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; }
}
</style>"""

st.html(CSS)
st.html('<div class="ink-bg"><i></i><i></i><i></i></div>')

# Small inline icons (Material Symbols paths) for the home steps.
ICON = {
    "link": "M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 "
            "13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z",
    "pause": "M9 16h2V8H9v8zm3-14C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59"
             "-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-4h2V8h-2v8z",
    "down": "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
}


def svg_img(svg: str) -> str:
    # st.html strips inline <svg>, so SVGs go in as data-URI images (their own <style> animations still run).
    return f"<img src='data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}' alt=''>"


def icon(name: str) -> str:
    return svg_img(f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='#f0a283' d='{ICON[name]}'/></svg>")


DONE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="#8fcb9a" stroke-width="1.8"
stroke-linecap="round" stroke-linejoin="round"><style>
circle { stroke-dasharray: 57; stroke-dashoffset: 57; animation: d .7s cubic-bezier(.22,1,.36,1) .1s forwards; }
path { stroke-dasharray: 14; stroke-dashoffset: 14; animation: d .45s cubic-bezier(.22,1,.36,1) .6s forwards; }
@keyframes d { to { stroke-dashoffset: 0; } }</style>
<circle cx="10" cy="10" r="9"/><path d="M6 10.3l2.7 2.7L14 7.7"/></svg>"""

# Notebook page being read: lines get written while a scan beam sweeps down.
WORKING_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 96"><style>
.ln { stroke: #e9a68b; stroke-width: 3; stroke-linecap: round; fill: none; stroke-dasharray: 52; stroke-dashoffset: 52;
  animation: w 4.8s cubic-bezier(.22,1,.36,1) infinite; }
.l2 { animation-delay: .45s; } .l3 { animation-delay: .9s; } .l4 { animation-delay: 1.35s; }
.beam { animation: s 2.4s ease-in-out infinite; }
.pen { animation: p 4.8s cubic-bezier(.22,1,.36,1) infinite; }
@keyframes w { 0% { stroke-dashoffset: 52; opacity: 1; } 35%,80% { stroke-dashoffset: 0; opacity: 1; } 100% { stroke-dashoffset: 0; opacity: 0; } }
@keyframes s { 0%,100% { transform: translateY(0); } 50% { transform: translateY(58px); } }
@keyframes p { 0%,100% { transform: translate(0,0); } 20% { transform: translate(-6px,12px); } 40% { transform: translate(-2px,26px); }
  60% { transform: translate(-10px,40px); } 80% { transform: translate(0,14px); } }
</style><defs><linearGradient id="bm" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d97757" stop-opacity="0"/>
<stop offset=".5" stop-color="#f0a283" stop-opacity=".55"/><stop offset="1" stop-color="#d97757" stop-opacity="0"/></linearGradient></defs>
<rect x="14" y="6" width="86" height="84" rx="10" fill="#171717" stroke="#333"/>
<g fill="#0d0d0d" stroke="#3a3a3a"><circle cx="24" cy="20" r="2.6"/><circle cx="24" cy="36" r="2.6"/>
<circle cx="24" cy="52" r="2.6"/><circle cx="24" cy="68" r="2.6"/></g>
<path class="ln" d="M36 22h52"/><path class="ln l2" d="M36 36h40"/><path class="ln l3" d="M36 50h48"/>
<path class="ln l4" d="M36 64h30"/>
<rect class="beam" x="16" y="12" width="82" height="14" fill="url(#bm)"/>
<g class="pen"><path d="M92 14l6 6-16 16-7.5 1.5 1.5-7.5z" fill="#f0a283"/><path d="M88.5 17.5l6 6" stroke="#b4532f" stroke-width="1.4"/></g>
</svg>"""

# --------------------------------------------------------------------------- state


def job_registry() -> dict:
    return nt.JOBS


ss = st.session_state
ss.setdefault("job_id", st.query_params.get("job"))
ss.setdefault("errors", [])


def reset() -> None:
    ss.job_id, ss.errors = None, []
    st.query_params.pop("job", None)


def start(text: str) -> None:
    links = []
    for link in nt.split_links(text):
        if not nt.parse_video_id(link) and nt.parse_playlist_id(link):
            links += [nt.watch_url(v) for v in nt.expand_playlist(nt.parse_playlist_id(link))]
        elif nt.parse_video_id(link) and nt.parse_video_id(link) not in {nt.parse_video_id(x) for x in links}:
            links.append(link)
    if not links:
        ss.errors = [(0, text.strip()[:80], "Paste a YouTube video link, for example https://youtu.be/…")]
        return
    if not nt.get_keys():
        ss.errors = [(0, "", "The notes reader is not switched on yet. (App owner: add the free GEMINI_API_KEY "
                             "in the app's secrets — see README.)")]
        return
    job = nt.Job(links=links[:nt.MAX_LINKS])
    job_registry()[job.id] = job
    nt.start_job(job)
    ss.job_id, ss.errors = job.id, []
    st.query_params["job"] = job.id


# --------------------------------------------------------------------------- exports (cached)


@st.cache_data(max_entries=20, show_spinner=False)
def export(notes_json: str, kind: str) -> bytes:
    n = json.loads(notes_json)
    if kind == "pdf":
        return nt.to_pdf(n)
    if kind == "docx":
        return nt.to_docx(n)
    return nt.to_text(n).encode("utf-8")


def notes_html(n: dict) -> str:
    e = html.escape
    out = ['<div class="ink-notes">']
    for kind, b in nt.grouped(n["items"]):
        if kind == "lecture":
            out.append(f'<div class="lec">{e(b["text"])}</div>')
        elif kind == "heading":
            out.append(f"<h2>{e(b['text'])}</h2>")
        elif kind == "question":
            out.append(f'<div class="q"><div class="qs"><b>Q{b["n"]}.</b>{e(b["text"])}</div>')
            if b["steps"]:
                out.append('<div class="lbl">Solution</div>')
                out += [f'<div class="st">{e(s["text"])}</div>' for s in b["steps"]]
            out += [f'<div class="ans">Answer: {e(a["text"])}</div>' for a in b["answers"]]
            out.append("</div>")
        elif kind == "steps":
            out += [f'<div class="st">{e(s["text"])}</div>' for s in b["steps"]]
        elif kind == "answer":
            out.append(f'<div class="ans">Answer: {e(b["text"])}</div>')
        elif kind == "formula":
            out.append(f'<div class="fm">{e(b["text"])}</div>')
        elif kind == "definition":
            out.append(f'<p class="df"><b>Definition.</b> {e(b["text"])}</p>')
        else:
            out.append(f"<p>{e(b['text'])}</p>")
    out.append("</div>")
    return "".join(out)


def link_list(job: nt.Job) -> str:
    bad = {i for i, _, _ in job.errors}
    rows = []
    for i, link in enumerate(job.links, 1):
        f = job.fractions[i - 1]
        if i in bad:
            state = '<span class="pill bad">could not be read</span>'
        elif f >= 1:
            state = '<span class="pill ok">done</span>'
        elif f > 0:
            state = f'<span class="pill on">{html.escape(job.stages[i - 1])}</span>'
        else:
            state = '<span class="pill">waiting</span>'
        short = html.escape(link.replace("https://", "").replace("www.", "").split("&")[0])
        rows.append(f"<div><b>{i}</b><span style='flex:1;word-break:break-all'>{short}</span>{state}</div>")
    return f'<div class="ink-list">{"".join(rows)}</div>'


# --------------------------------------------------------------------------- about


@st.dialog("About", width="small")
def about() -> None:
    st.html(f"""<div class="ink-about">
      <img src="{logo_uri()}" alt="">
      <h3>{nt.APP_NAME}</h3>
      <div class="v">Version {nt.VERSION} · free for every student</div>
      <div class="ink-card">
        Paste your teacher's YouTube lecture links. The app stops on every written page by itself,
        cleans up the blurry writing and writes out the questions and their solutions exactly as the
        teacher wrote them — no talk, no pictures, no links. Download as PDF, Word or text.
      </div>
      <div class="ink-card">
        <div class="k">Creator</div><b>Muhammad Saif Ur Rehman</b><br>
        Student · Pakistan<br>
        <a href="mailto:saifsaab317@gmail.com">saifsaab317@gmail.com</a>
      </div></div>""")


# --------------------------------------------------------------------------- splash (first visit only)

if not ss.get("splashed"):
    ss.splashed = True
    st.html(f"""<div class="ink-splash">
      <div class="lg"><i></i><i></i><img src="{logo_uri(animated=True)}" alt=""></div>
      <div class="n">{nt.APP_NAME}</div>
      <div class="t">The teacher's writing, as clean notes</div>
      <div class="bar"></div>
      <div class="c">Created by <b>Muhammad Saif Ur Rehman</b><br>Student · Pakistan</div>
    </div>""")

# --------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.html(f'<div class="ink-brand"><img src="{logo_uri()}" alt=""><span>{nt.APP_NAME}</span></div>')
    if st.button("New notes", icon=":material/edit_square:", width="stretch"):
        reset()
        st.rerun()
    st.divider()
    if st.button("About", icon=":material/info:", width="stretch", type="tertiary"):
        about()

# --------------------------------------------------------------------------- main

job = job_registry().get(ss.job_id) if ss.job_id else None
if ss.job_id and job is None:          # server restarted: the job is gone
    reset()

if job is not None and not job.done:
    n = job.total
    st.html(f'<div class="ink-bubble">{n} lecture link{"s" if n > 1 else ""}</div>')
    st.html(f"""<div class="ink-work">{svg_img(WORKING_SVG)}<div>
      <h3>Reading the teacher's pages</h3>
      <p>Stopping on every written page, cleaning the writing and copying out each question and solution.</p>
      </div></div>""")

    @st.fragment(run_every=1.5)
    def progress_view():
        j = job_registry().get(ss.job_id)
        if j is None or j.done:
            st.rerun()
        with st.container(border=True, key="ink_progress"):
            st.markdown("**Making your notes**" + (f" · {j.finished} of {j.total} done" if j.total > 1 else ""))
            st.progress(min(j.progress, 0.99), text=j.stage)
            if j.total > 1:
                st.html(link_list(j))
            mins = int((time.time() - j.started) // 60)
            st.caption("Keep this tab open. Each lecture takes about a minute or two."
                       + (f" Running for {mins} min." if mins else ""))

    progress_view()

elif job is not None:
    notes = nt.combine(job.results)
    if notes:
        if ss.get("toasted") != job.id:
            ss.toasted = job.id
            st.toast("Your notes are ready", icon=":material/task_alt:")
        st.html(f'<div class="ink-done">{svg_img(DONE_SVG)}Notes ready</div>'
                f'<div class="ink-dev">Developer <b>{nt.DEVELOPER}</b></div>')
        st.header(notes["title"] if notes.get("lectures", 1) == 1 else "Your lecture notes", anchor=False)
        qs = sum(1 for i in notes["items"] if i["type"] == "question")
        meta = [f"{notes['lectures']} lectures" if notes["lectures"] > 1 else "",
                f"{qs} question{'s' if qs != 1 else ''}", notes.get("created", "")]
        st.html('<div class="ink-meta">' + "".join(f"<span>{html.escape(m)}</span>" for m in meta if m) + "</div>")
    for num, link, err in job.errors:
        st.error(f"**Link {num}** could not be read: {err}  \n`{link}`", icon=":material/error:")
    if notes:
        payload = json.dumps(notes, ensure_ascii=False, sort_keys=True)
        fname = nt.safe_filename(notes["title"])
        with st.container(horizontal=True, key="ink_dl"):
            st.download_button("PDF", export(payload, "pdf"), f"{fname}.pdf", "application/pdf",
                               icon=":material/picture_as_pdf:", type="primary", on_click="ignore")
            st.download_button("Word", export(payload, "docx"), f"{fname}.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               icon=":material/description:", on_click="ignore")
            st.download_button("Text", export(payload, "txt"), f"{fname}.txt", "text/plain",
                               icon=":material/notes:", on_click="ignore")
        with st.container(border=True, key="ink_notes_box"):
            st.html(notes_html(notes))

    if (text := st.chat_input("Paste more lecture links…", key="link_more")):
        start(text)
        st.rerun()

else:
    st.html(f"""<div class="ink-hero">
      <div class="ink-logo"><img src="{logo_uri(animated=True)}" alt=""></div>
      <div class="ink-dev">Developer <b>{nt.DEVELOPER}</b></div>
      <div class="ink-tag"><span class="dot"></span>Free for every student</div>
      <h1>Turn lectures into <em>clean notes</em></h1>
      <p>Paste the YouTube links. You get every question and solution the teacher wrote — clearly.</p></div>
      <div class="ink-steps">
        <div class="ink-step"><span class="num">01</span><div class="ic">{icon("link")}</div>
          <b>Paste links</b><span>Videos, shorts or a whole playlist</span></div>
        <div class="ink-step"><span class="num">02</span><div class="ic">{icon("pause")}</div>
          <b>Stops on each page</b><span>Finds the written pages and cleans the blur</span></div>
        <div class="ink-step"><span class="num">03</span><div class="ic">{icon("down")}</div>
          <b>Download notes</b><span>Same questions and solutions, as PDF, Word or text</span></div>
      </div>""")
    for num, link, err in ss.errors:
        st.error(f"{err}  \n`{link}`" if link else err, icon=":material/error:")
    with st.container():
        text = st.chat_input("Paste one or more YouTube links…", key="link_home")
    st.html('<div class="ink-hint"><b>Videos, shorts and playlists</b> · as many links as you like · '
            '<b>PDF, Word and text</b></div>')
    if text:
        start(text)
        st.rerun()
