import os
import streamlit as st


def inject_theme():
    st.markdown("""
    <style>
    :root { --bg:#070a0d; --panel:#0d1216; --panel2:#11181d; --text:#f4f7f5; --muted:#8b9691; --lime:#76b900; --violet:#8b7cff; --line:rgba(255,255,255,.08); }
    .stApp { background: radial-gradient(circle at 75% 5%, rgba(118,185,0,.08), transparent 24%), radial-gradient(circle at 18% 35%, rgba(139,124,255,.10), transparent 28%), var(--bg); color:var(--text); }
    .block-container { max-width:1480px; padding:1.4rem 2.2rem 4rem; }
    header[data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { background:#090d10; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] .block-container { padding:1.3rem 1rem; }
    .os-brand { display:flex; align-items:center; gap:12px; margin-bottom:26px; }
    .os-mark { width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,#76b900,#9be33b);color:#071006;font-weight:900;box-shadow:0 0 30px rgba(118,185,0,.2); }
    .os-name { font-weight:750;font-size:18px;letter-spacing:-.4px; }
    .os-sub { color:var(--muted);font-size:11px;margin-top:2px; }
    .nav-label { color:#66716d;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:22px 0 8px; }
    .topline { display:flex;justify-content:space-between;align-items:center;margin:3px 0 22px; }
    .eyebrow { color:#9be33b;font-size:10px;font-weight:800;letter-spacing:1.8px;text-transform:uppercase; }
    .page-title { font-size:34px;font-weight:780;letter-spacing:-1.5px;line-height:1.08;margin:6px 0; }
    .page-sub { color:var(--muted);font-size:13px;line-height:1.6;max-width:760px; }
    .live-pill { border:1px solid rgba(118,185,0,.25);background:rgba(118,185,0,.07);border-radius:999px;padding:8px 12px;color:#b6e56c;font-size:11px; }
    .hero { position:relative;overflow:hidden;border:1px solid var(--line);border-radius:26px;padding:32px;background:linear-gradient(135deg,rgba(118,185,0,.09),rgba(139,124,255,.08) 55%,rgba(255,255,255,.02));box-shadow:0 28px 80px rgba(0,0,0,.25); }
    .hero:after { content:"";position:absolute;width:280px;height:280px;border-radius:50%;right:-90px;top:-100px;background:rgba(118,185,0,.10);filter:blur(12px); }
    .hero-title { font-size:44px;font-weight:800;letter-spacing:-2px;line-height:1.02;max-width:700px;margin:8px 0 14px; }
    .hero-copy { color:#a9b2ae;max-width:690px;line-height:1.7;font-size:14px; }
    .grid-card { border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,rgba(255,255,255,.045),rgba(255,255,255,.018));padding:20px;min-height:118px; }
    .metric-label { color:#7f8a85;font-size:10px;font-weight:750;letter-spacing:1.2px;text-transform:uppercase; }
    .metric-value { font-size:27px;font-weight:780;letter-spacing:-1px;margin-top:10px; }
    .metric-note { color:#77817d;font-size:11px;margin-top:5px; }
    .section-head { margin:30px 0 14px; }
    .section-title { font-size:20px;font-weight:720;letter-spacing:-.6px; }
    .section-sub { color:#75807b;font-size:12px;margin-top:3px; }
    .panel { border:1px solid var(--line);border-radius:20px;background:rgba(13,18,22,.82);padding:22px; }
    .panel-lime { border-color:rgba(118,185,0,.18);background:linear-gradient(145deg,rgba(118,185,0,.08),rgba(13,18,22,.88)); }
    .panel-violet { border-color:rgba(139,124,255,.2);background:linear-gradient(145deg,rgba(139,124,255,.08),rgba(13,18,22,.88)); }
    .tag { display:inline-block;padding:5px 8px;border:1px solid var(--line);border-radius:999px;color:#a8b0ad;font-size:10px;margin:3px 4px 0 0;background:rgba(255,255,255,.025); }
    .spline { border:1px solid rgba(118,185,0,.16);border-radius:24px;overflow:hidden;background:radial-gradient(circle at center,rgba(118,185,0,.10),rgba(8,12,14,.98) 62%);min-height:330px;display:flex;align-items:center;justify-content:center; }
    .spline-fallback { text-align:center;padding:40px;color:#87928d; }
    .core { width:130px;height:130px;border-radius:50%;border:1px solid rgba(155,227,59,.45);box-shadow:0 0 80px rgba(118,185,0,.2),inset 0 0 35px rgba(118,185,0,.08);display:grid;place-items:center;margin:0 auto 20px;animation:pulse 4s ease-in-out infinite; }
    .core:before { content:"";width:72px;height:72px;border-radius:50%;border:1px dashed rgba(155,227,59,.55); }
    @keyframes pulse { 50% { transform:scale(1.05);box-shadow:0 0 100px rgba(118,185,0,.28),inset 0 0 40px rgba(118,185,0,.1); } }
    .core-label { color:#b6e56c;font-size:11px;font-weight:750;letter-spacing:1.5px;text-transform:uppercase; }
    .action-row { border:1px solid var(--line);border-radius:14px;padding:13px 15px;background:rgba(255,255,255,.025);margin:8px 0; }
    .muted { color:var(--muted); }
    div[data-testid="stMetric"] { background:transparent;border:0; }
    div[data-testid="stMetricLabel"] { color:#7f8a85; }
    div[data-testid="stMetricValue"] { color:#f4f7f5; }
    .stButton > button { border-radius:11px;min-height:40px;border:1px solid var(--line);font-weight:650; }
    .stTextArea textarea,.stTextInput input { background:#0b1013!important;border:1px solid var(--line)!important;border-radius:12px!important;color:#f4f7f5!important; }
    .stSelectbox > div > div { background:#0b1013;border-radius:10px; }
    .stTabs [data-baseweb="tab-list"] { gap:18px; }
    .stTabs [data-baseweb="tab"] { color:#818b87; }
    .stTabs [aria-selected="true"] { color:#b6e56c; }
    .main-nav {
    display: flex;
    align-items: center;
    margin-bottom: 18px;
}

.nav-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.nav-mark {
    width: 38px;
    height: 38px;
    border-radius: 11px;
    display: grid;
    place-items: center;
    background: linear-gradient(135deg, #76b900, #9be33b);
    color: #071006;
    font-weight: 900;
    box-shadow: 0 0 30px rgba(118,185,0,.18);
}

.nav-title {
    color: #f4f7f5;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 1px;
}

.nav-subtitle {
    color: #707b76;
    font-size: 9px;
    letter-spacing: 1.4px;
    margin-top: 2px;
}

.nav-status {
    color: #7f8a85;
    font-size: 10px;
    letter-spacing: 1.1px;
    margin: 12px 0 4px;
}

.status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #76b900;
    box-shadow: 0 0 10px rgba(118,185,0,.65);
    margin-right: 6px;
}

.status-separator {
    margin: 0 8px;
    color: #424b47;
}

.nav-divider {
    height: 1px;
    background: rgba(255,255,255,.07);
    margin: 4px 0 26px;
}

[data-testid="stSidebar"] {
    display: none;
}

[data-testid="stHeader"] {
    background: #070a0d !important;
}
    </style>
    """, unsafe_allow_html=True)


def sidebar():
    with st.sidebar:
        st.markdown('<div class="os-brand"><div class="os-mark">N</div><div><div class="os-name">AI Company OS</div><div class="os-sub">NVIDIA intelligence layer</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-label">Workspace</div>', unsafe_allow_html=True)
        pages=[("⌂  Command Center","Command Center"),("◈  Intelligence","Intelligence"),("◌  Agents","Agents"),("$  Financials","Financials"),("✓  Approvals","Approvals"),("◷  History","History")]
        current=st.session_state.get("page","Command Center")
        for label,name in pages:
            if st.button(label,use_container_width=True,key=f"nav_{name}",type="primary" if current==name else "secondary"):
                st.session_state.page=name; st.rerun()
        st.markdown('<div class="nav-label">System</div>', unsafe_allow_html=True)
        st.caption("Deterministic analytics")
        st.caption("Commander orchestration")
        st.caption("Nemotron synthesis")
        st.caption("Human approval gate")
        st.markdown("---")
        st.markdown('<div class="live-pill">● SYSTEM ONLINE</div>',unsafe_allow_html=True)


def page_header(eyebrow,title,subtitle):
    st.markdown(f'<div class="topline"><div><div class="eyebrow">{eyebrow}</div><div class="page-title">{title}</div><div class="page-sub">{subtitle}</div></div><div class="live-pill">● NVIDIA INTELLIGENCE ONLINE</div></div>',unsafe_allow_html=True)


def spline_core():
    url=os.getenv("SPLINE_SCENE_URL","").strip()
    if url:
        st.markdown(f'<div class="spline"><iframe src="{url}" frameborder="0" width="100%" height="380" style="border:0;border-radius:24px"></iframe></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="spline"><div class="spline-fallback"><div class="core"><div></div></div><div class="core-label">AI COMPANY OS · INTELLIGENCE CORE</div><p>Add <code>SPLINE_SCENE_URL</code> to your local .env when your Spline scene is ready.</p></div></div>',unsafe_allow_html=True)
