"""Spurs-inspired 視覺風格常數與全域樣式注入。

不使用任何 NBA 官方 logo 或受版權保護素材，僅以黑、銀、白幾何線條建立視覺語言。
"""
from __future__ import annotations

import streamlit as st

COLORS = {
    "black": "#0B0B0C",
    "silver": "#C4CED4",
    "white": "#F8F8F8",
    "dark_gray": "#1D1F21",
    "cool_blue_gray": "#7E8A97",
    "success": "#2E7D5B",
    "warning": "#B94A48",
}

SOURCE_BADGE_STYLES = {
    "api": {"label": "NBA API", "bg": "#2E7D5B", "fg": "#F8F8F8"},
    "partial_api": {"label": "部分 API", "bg": "#B58A2D", "fg": "#0B0B0C"},
    "seed": {"label": "展示資料", "bg": "#7E8A97", "fg": "#0B0B0C"},
}

_GLOBAL_CSS = f"""
<style>
:root {{
    --color-black: {COLORS["black"]};
    --color-silver: {COLORS["silver"]};
    --color-white: {COLORS["white"]};
    --color-dark-gray: {COLORS["dark_gray"]};
}}

div[data-testid="stAppViewContainer"] {{
    background:
        radial-gradient(circle at 12% 8%, rgba(196, 206, 212, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 92% 88%, rgba(126, 138, 151, 0.05) 0%, transparent 50%),
        {COLORS["black"]};
}}

section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #131416 0%, #0B0B0C 100%);
    border-right: 1px solid #1D1F21;
}}

section[data-testid="stSidebar"] h1 {{
    color: {COLORS["silver"]};
    letter-spacing: 0.12em;
    font-size: 1.1rem;
}}

.spurs-hero {{
    position: relative;
    padding: 2.4rem 2.2rem;
    margin: -0.5rem 0 1.6rem 0;
    border-radius: 14px;
    background:
        linear-gradient(135deg, #1D1F21 0%, #0B0B0C 100%);
    border: 1px solid #2A2C2F;
    overflow: hidden;
}}

.spurs-hero::before {{
    content: "";
    position: absolute;
    inset: 0;
    background:
        repeating-linear-gradient(
            115deg,
            rgba(196, 206, 212, 0.05) 0px,
            rgba(196, 206, 212, 0.05) 1px,
            transparent 1px,
            transparent 22px
        );
    pointer-events: none;
}}

.spurs-hero h1 {{
    color: {COLORS["white"]};
    font-size: 2rem;
    margin: 0 0 0.4rem 0;
    letter-spacing: 0.04em;
}}

.spurs-hero p {{
    color: {COLORS["silver"]};
    margin: 0;
    font-size: 1rem;
    opacity: 0.85;
}}

.spurs-hero .court-line {{
    position: absolute;
    right: -60px;
    bottom: -60px;
    width: 220px;
    height: 220px;
    border: 2px solid rgba(196, 206, 212, 0.18);
    border-radius: 50%;
}}

.spurs-hero .court-line::after {{
    content: "";
    position: absolute;
    inset: 30px;
    border: 2px solid rgba(196, 206, 212, 0.12);
    border-radius: 50%;
}}

.spurs-section-title {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1.6rem 0 0.8rem 0;
}}

.spurs-section-title .bar {{
    width: 4px;
    height: 22px;
    background: {COLORS["silver"]};
    border-radius: 2px;
}}

.spurs-section-title h3 {{
    margin: 0;
    color: {COLORS["white"]};
    font-size: 1.15rem;
    letter-spacing: 0.04em;
}}

.spurs-badge {{
    display: inline-block;
    padding: 0.18rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}}

div[data-testid="stMetric"] {{
    background: #131416;
    border: 1px solid #2A2C2F;
    border-radius: 10px;
    padding: 0.8rem 1rem;
}}

div[data-testid="stMetricLabel"] p {{
    color: {COLORS["cool_blue_gray"]};
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-size: 0.75rem;
}}

div[data-testid="stMetricValue"] {{
    color: {COLORS["white"]};
}}

div[data-testid="stDataFrame"] {{
    border: 1px solid #2A2C2F;
    border-radius: 8px;
}}

.stButton > button {{
    background: {COLORS["dark_gray"]};
    color: {COLORS["white"]};
    border: 1px solid {COLORS["silver"]};
    border-radius: 6px;
    transition: all 0.15s ease;
}}

.stButton > button:hover {{
    background: {COLORS["silver"]};
    color: {COLORS["black"]};
    border-color: {COLORS["silver"]};
}}

hr {{
    border-color: #2A2C2F !important;
}}

/* ── Sidebar 功能選單 ── */

/* radiogroup 容器：讓選項之間有間距 */
section[data-testid="stSidebar"] div[role="radiogroup"] {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}

/* 每個選項的 label wrapper（Streamlit 渲染為 div，包住 input + p） */
section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
    display: flex;
    align-items: center;
    padding: 0.5rem 0.8rem;
    border-radius: 7px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
    position: relative;
}}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
    background: rgba(196, 206, 212, 0.07);
    border-color: rgba(196, 206, 212, 0.15);
}}

/* 選中：label 內有 input[type=radio]:checked */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
    background: rgba(196, 206, 212, 0.11);
    border-color: rgba(196, 206, 212, 0.28);
}}

/* 選中時左側銀色指示條 */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked)::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 20%;
    height: 60%;
    width: 3px;
    background: {COLORS["silver"]};
    border-radius: 0 2px 2px 0;
}}

/* 選項文字顏色 */
section[data-testid="stSidebar"] div[role="radiogroup"] > label p {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.93rem;
    margin: 0;
    transition: color 0.15s ease;
}}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover p,
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
    color: {COLORS["white"]};
    font-weight: 600;
}}

/* ── M11 Dashboard 元件 ── */

.spurs-card {{
    background: #131416;
    border: 1px solid #2A2C2F;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s ease, transform 0.2s ease;
}}

.spurs-card:hover {{
    border-color: rgba(196, 206, 212, 0.35);
}}

/* Stat card：自訂指標卡 */
.spurs-stat-card {{
    background: #131416;
    border: 1px solid #2A2C2F;
    border-left: 3px solid {COLORS["silver"]};
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
}}

.spurs-stat-card .label {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 0 0 0.3rem 0;
}}

.spurs-stat-card .value {{
    color: {COLORS["white"]};
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.2;
}}

.spurs-stat-card .sub {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.78rem;
    margin: 0.25rem 0 0 0;
}}

.spurs-stat-card.accent-green {{ border-left-color: {COLORS["success"]}; }}
.spurs-stat-card.accent-red {{ border-left-color: {COLORS["warning"]}; }}
.spurs-stat-card.accent-blue {{ border-left-color: {COLORS["cool_blue_gray"]}; }}

/* KPI strip：橫向指標列 */
.spurs-kpi-strip {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.7rem;
    margin: 0.4rem 0 1.2rem 0;
}}

.spurs-kpi-strip .kpi {{
    background: linear-gradient(135deg, #15171A 0%, #0E0F11 100%);
    border: 1px solid #2A2C2F;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    position: relative;
    overflow: hidden;
}}

.spurs-kpi-strip .kpi::after {{
    content: "";
    position: absolute;
    right: -20px;
    top: -20px;
    width: 60px;
    height: 60px;
    border: 1px solid rgba(196, 206, 212, 0.08);
    border-radius: 50%;
}}

.spurs-kpi-strip .kpi .k-label {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.spurs-kpi-strip .kpi .k-value {{
    color: {COLORS["white"]};
    font-size: 1.55rem;
    font-weight: 700;
    margin-top: 0.2rem;
}}

.spurs-kpi-strip .kpi .k-sub {{
    color: {COLORS["silver"]};
    font-size: 0.75rem;
    margin-top: 0.15rem;
    opacity: 0.7;
}}

/* Player card */
.spurs-player-card {{
    background: linear-gradient(160deg, #15171A 0%, #0E0F11 100%);
    border: 1px solid #2A2C2F;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.7rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    min-height: 170px;
    transition: border-color 0.2s ease, transform 0.2s ease;
}}

.spurs-player-card:hover {{
    border-color: rgba(196, 206, 212, 0.4);
    transform: translateY(-2px);
}}

.spurs-player-card .head {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
}}

.spurs-player-card .avatar {{
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, {COLORS["silver"]} 0%, #7E8A97 100%);
    color: {COLORS["black"]};
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
}}

.spurs-player-card .avatar-img {{
    width: 52px;
    height: 52px;
    border-radius: 50%;
    object-fit: cover;
    object-position: center top;
    border: 2px solid #2A2C2F;
    flex-shrink: 0;
    background: linear-gradient(135deg, {COLORS["silver"]} 0%, #7E8A97 100%);
}}

.spurs-player-card .name {{
    color: {COLORS["white"]};
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    line-height: 1.2;
}}

.spurs-player-card .team-chip {{
    display: inline-block;
    background: rgba(196, 206, 212, 0.12);
    color: {COLORS["silver"]};
    padding: 0.1rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    margin-top: 0.2rem;
}}

.spurs-player-card .pos-chip {{
    display: inline-block;
    background: rgba(126, 138, 151, 0.15);
    color: {COLORS["cool_blue_gray"]};
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.7rem;
    margin-left: 0.3rem;
}}

.spurs-player-card .stats {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.4rem;
    border-top: 1px solid #2A2C2F;
    padding-top: 0.6rem;
}}

.spurs-player-card .stats .stat-item {{
    text-align: center;
}}

.spurs-player-card .stats .stat-item .s-label {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}

.spurs-player-card .stats .stat-item .s-value {{
    color: {COLORS["white"]};
    font-size: 1.05rem;
    font-weight: 600;
}}

.spurs-player-card .footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #2A2C2F;
    padding-top: 0.5rem;
    font-size: 0.78rem;
}}

.spurs-player-card .footer .fs {{
    color: {COLORS["silver"]};
}}

.spurs-player-card .footer .salary {{
    color: {COLORS["white"]};
    font-weight: 600;
}}

/* Team color variants for matchup player cards */
.spurs-player-card.team-blue {{
    background: linear-gradient(160deg, #0D1827 0%, #09111E 100%);
    border-color: #1B4C8A;
}}
.spurs-player-card.team-blue:hover {{
    border-color: rgba(60, 140, 240, 0.65);
}}
.spurs-player-card.team-red {{
    background: linear-gradient(160deg, #270D0D 0%, #1E0909 100%);
    border-color: #8A1B1B;
}}
.spurs-player-card.team-red:hover {{
    border-color: rgba(220, 60, 60, 0.65);
}}

/* Progress ring（純 CSS conic-gradient） */
.spurs-ring-wrap {{
    display: flex;
    align-items: center;
    gap: 1rem;
    background: #131416;
    border: 1px solid #2A2C2F;
    border-radius: 12px;
    padding: 1rem 1.2rem;
}}

.spurs-ring {{
    width: 86px;
    height: 86px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    flex-shrink: 0;
}}

.spurs-ring::before {{
    content: "";
    position: absolute;
    inset: 8px;
    background: #131416;
    border-radius: 50%;
}}

.spurs-ring .ring-value {{
    position: relative;
    color: {COLORS["white"]};
    font-size: 1rem;
    font-weight: 700;
    z-index: 1;
}}

.spurs-ring-wrap .ring-info .ring-label {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.spurs-ring-wrap .ring-info .ring-sub {{
    color: {COLORS["white"]};
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 0.2rem;
}}

.spurs-ring-wrap .ring-info .ring-note {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.75rem;
    margin-top: 0.15rem;
}}

/* VS block：Matchup 兩隊大字對抗 */
.spurs-vs {{
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 1.2rem;
    background: linear-gradient(135deg, #15171A 0%, #0E0F11 100%);
    border: 1px solid #2A2C2F;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin: 0.5rem 0 1rem 0;
}}

.spurs-vs .side {{
    text-align: center;
}}

.spurs-vs .side.right {{ text-align: center; }}

.spurs-vs .side .team-name {{
    color: {COLORS["white"]};
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
    letter-spacing: 0.02em;
}}

.spurs-vs .side .win-rate {{
    color: {COLORS["silver"]};
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1;
}}

.spurs-vs .side .win-rate-suffix {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.85rem;
    margin-left: 0.15rem;
}}

.spurs-vs .vs-text {{
    color: {COLORS["silver"]};
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    opacity: 0.7;
    padding: 0 0.8rem;
    border-left: 1px solid #2A2C2F;
    border-right: 1px solid #2A2C2F;
}}

.spurs-vs .side.winner .win-rate {{
    color: {COLORS["white"]};
}}

.spurs-vs .side.winner .team-name::after {{
    content: " ★";
    color: {COLORS["silver"]};
}}

/* Scoreboard card：賽程卡 */
.spurs-game-card {{
    background: #131416;
    border: 1px solid #2A2C2F;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    grid-template-rows: auto auto;
    grid-template-areas:
        "hname mid-top aname"
        "hscore status  ascore";
    align-items: center;
    gap: 0.15rem 0.8rem;
}}

.spurs-game-card .gc-home {{ text-align: right; }}
.spurs-game-card .gc-away {{ text-align: left; }}

.spurs-game-card .gc-name.gc-home {{ grid-area: hname; }}
.spurs-game-card .gc-name.gc-away {{ grid-area: aname; }}
.spurs-game-card .gc-mid-top {{ grid-area: mid-top; }}
.spurs-game-card .gc-score.gc-home {{ grid-area: hscore; }}
.spurs-game-card .gc-score.gc-away {{ grid-area: ascore; }}
.spurs-game-card .gc-status {{ grid-area: status; }}

.spurs-game-card .gc-name {{
    color: {COLORS["white"]};
    font-weight: 600;
    font-size: 0.95rem;
}}

.spurs-game-card .gc-score {{
    color: {COLORS["silver"]};
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1;
}}

.spurs-game-card .gc-status {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.78rem;
    text-align: center;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border: 1px solid #2A2C2F;
    border-radius: 4px;
}}

/* Feature card（home page） */
.spurs-feature-card {{
    background: linear-gradient(160deg, #15171A 0%, #0E0F11 100%);
    border: 1px solid #2A2C2F;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 0.7rem;
    height: 100%;
    transition: border-color 0.2s ease;
}}

.spurs-feature-card:hover {{
    border-color: rgba(196, 206, 212, 0.35);
}}

.spurs-feature-card .f-title {{
    color: {COLORS["white"]};
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

.spurs-feature-card .f-title::before {{
    content: "";
    width: 3px;
    height: 14px;
    background: {COLORS["silver"]};
    border-radius: 2px;
}}

.spurs-feature-card .f-desc {{
    color: {COLORS["cool_blue_gray"]};
    font-size: 0.85rem;
    line-height: 1.5;
}}

/* Input 微調 */
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {{
    background: #131416 !important;
    border-color: #2A2C2F !important;
    color: {COLORS["white"]} !important;
}}

/* ── RWD：手機 ≤ 768px ────────────────────────────── */
@media (max-width: 768px) {{
    /* Hero：縮小 padding 與字級 */
    .spurs-hero {{
        padding: 1.4rem 1.2rem;
        margin: -0.3rem 0 1rem 0;
    }}
    .spurs-hero h1 {{
        font-size: 1.4rem;
        letter-spacing: 0.02em;
    }}
    .spurs-hero p {{
        font-size: 0.85rem;
    }}
    .spurs-hero .court-line {{
        width: 130px;
        height: 130px;
        right: -40px;
        bottom: -40px;
    }}
    .spurs-hero .court-line::after {{
        inset: 18px;
    }}

    /* Section 標題縮小 */
    .spurs-section-title h3 {{
        font-size: 1rem;
    }}
    .spurs-section-title {{
        margin: 1.1rem 0 0.6rem 0;
    }}

    /* KPI strip：強制 2 欄、字級縮小 */
    .spurs-kpi-strip {{
        grid-template-columns: repeat(2, 1fr);
        gap: 0.5rem;
    }}
    .spurs-kpi-strip .kpi {{
        padding: 0.65rem 0.8rem;
    }}
    .spurs-kpi-strip .kpi .k-value {{
        font-size: 1.2rem;
    }}
    .spurs-kpi-strip .kpi .k-label {{
        font-size: 0.62rem;
    }}
    .spurs-kpi-strip .kpi .k-sub {{
        font-size: 0.68rem;
    }}

    /* Stat card 縮小 */
    .spurs-stat-card {{
        padding: 0.7rem 0.9rem;
    }}
    .spurs-stat-card .value {{
        font-size: 1.3rem;
    }}

    /* Player card：縮小頭像與字級 */
    .spurs-player-card {{
        padding: 0.8rem 0.9rem;
        min-height: 0;
    }}
    .spurs-player-card .avatar,
    .spurs-player-card .avatar-img {{
        width: 40px;
        height: 40px;
        font-size: 0.9rem;
    }}
    .spurs-player-card .name {{
        font-size: 0.9rem;
    }}
    .spurs-player-card .stats {{
        grid-template-columns: repeat(3, 1fr);
        gap: 0.35rem;
    }}
    .spurs-player-card .stats .stat-item .s-value {{
        font-size: 0.9rem;
    }}
    .spurs-player-card .stats .stat-item .s-label {{
        font-size: 0.6rem;
    }}
    .spurs-player-card .team-chip,
    .spurs-player-card .pos-chip {{
        font-size: 0.65rem;
    }}

    /* VS block：字級大幅縮小、避免溢出 */
    .spurs-vs {{
        padding: 1rem 0.8rem;
        gap: 0.5rem;
    }}
    .spurs-vs .side .team-name {{
        font-size: 0.85rem;
    }}
    .spurs-vs .side .win-rate {{
        font-size: 1.5rem;
    }}
    .spurs-vs .side .win-rate-suffix {{
        font-size: 0.7rem;
    }}
    .spurs-vs .vs-text {{
        font-size: 1rem;
        padding: 0 0.4rem;
    }}

    /* Game card：縮小比分字級 */
    .spurs-game-card {{
        padding: 0.7rem 0.8rem;
        gap: 0.1rem 0.5rem;
    }}
    .spurs-game-card .gc-name {{
        font-size: 0.8rem;
    }}
    .spurs-game-card .gc-score {{
        font-size: 1.35rem;
    }}
    .spurs-game-card .gc-status {{
        font-size: 0.65rem;
        padding: 0.15rem 0.4rem;
    }}

    /* Progress ring：縮小尺寸 */
    .spurs-ring-wrap {{
        padding: 0.8rem 1rem;
        gap: 0.7rem;
    }}
    .spurs-ring {{
        width: 68px;
        height: 68px;
    }}
    .spurs-ring::before {{
        inset: 6px;
    }}
    .spurs-ring .ring-value {{
        font-size: 0.85rem;
    }}
    .spurs-ring-wrap .ring-info .ring-sub {{
        font-size: 0.95rem;
    }}

    /* Feature card */
    .spurs-feature-card {{
        padding: 0.85rem 1rem;
    }}
    .spurs-feature-card .f-title {{
        font-size: 0.92rem;
    }}
    .spurs-feature-card .f-desc {{
        font-size: 0.78rem;
    }}

    /* Streamlit columns：在手機上強制單欄堆疊，避免並排太擠 */
    div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap;
    }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
    }}
}}

/* ── RWD：極窄手機 ≤ 380px ────────────────────────── */
@media (max-width: 380px) {{
    /* KPI strip：1 欄 */
    .spurs-kpi-strip {{
        grid-template-columns: 1fr;
    }}
    /* VS block：堆疊式（含 vs 字樣居中） */
    .spurs-vs {{
        grid-template-columns: 1fr;
        text-align: center;
    }}
    .spurs-vs .vs-text {{
        border: none;
        padding: 0.3rem 0;
    }}
    /* Game card：仍保持三欄但更緊湊 */
    .spurs-game-card .gc-score {{
        font-size: 1.2rem;
    }}
}}
</style>
"""


def inject_global_styles() -> None:
    """注入全域 CSS。每次 rerun 都需重新注入，否則 Streamlit 重渲染後樣式會消失。"""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
