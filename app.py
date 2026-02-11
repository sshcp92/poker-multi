import streamlit as st
import pandas as pd
import random
import time
import os

# ==========================================
# 1. 디자인 및 설정 (형님 원판 그대로)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - 멀티", page_icon="🦁")

# 형님이 주신 블라인드 구조 & 핸드 맵핑 그대로 유지
BLIND_STRUCTURE = [(100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800),
                   (500, 1000, 1000), (1000, 2000, 2000), (2000, 4000, 4000), (5000, 10000, 10000)]
LEVEL_DURATION = 600
RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 16px; }
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container { position:relative; width:100%; height:650px; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
.poker-table { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723); border: 20px solid #281915; border-radius: 250px; box-shadow: inset 0 0 50px rgba(0,0,0,0.8); }
.seat { position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666; border-radius:15px; color:white; text-align:center; display:flex; flex-direction:column; justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10; }
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; background:#3a3a3a; box-shadow:0 0 25px #ffd700; z-index: 20; }
.active-turn { border:4px solid #ffeb3b !important; box-shadow: 0 0 15px #ffeb3b; }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:26px; color:black; border:1px solid #ccc; line-height: 1.0;}
.role-badge { position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; color: black; font-weight: bold; line-height: 26px; border: 2px solid #333; z-index: 100; font-size: 14px; }
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000; z-index:100;}
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 멀티플레이 데이터 엔진 (CSV 기반)
# ==========================================
DB_FILE = "poker_db.csv"
STATE_FILE = "state.txt"

def init_game():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    for i in range(9):
        players.append({'name': 'Empty', 'seat': i+1, 'stack': 60000, 'hand': f"{deck.pop()},{deck.pop()}", 'bet': 0, 'status': 'waiting', 'action': '', 'is_joined': False, 'role': '', 'buyin': 1})
    pd.DataFrame(players).to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        comm = ",".join([deck.pop() for _ in range(5)])
        # pot|cur_bet|turn|phase|comm|open|msg|sb|bb|ante|dealer_idx|level|start_time
        f.write(f"0|200|0|PREFLOP|{comm}|0|Ready|100|200|0|0|1|{time.time()}")

def load_data():
    try:
        df = pd.read_csv(DB_FILE).fillna('')
        with open(STATE_FILE, "r", encoding='utf-8') as f:
            s = f.read().split('|')
            state = {'pot':int(s[0]), 'cur_bet':int(s[1]), 'turn':int(s[2]), 'phase':s[3], 'comm':s[4], 'open':int(s[5]), 'msg':s[6], 'sb':s[7], 'bb':s[8], 'ante':s[9], 'dealer_idx':int(s[10]), 'level':int(s[11]), 'start_time':float(s[12])}
        return df, state
    except:
        init_game(); return load_data()

def save_data(df, state):
    df.to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        f.write(f"{state['pot']}|{state['cur_bet']}|{state['turn']}|{state['phase']}|{state['comm']}|{state['open']}|{state['msg']}|{state['sb']}|{state['bb']}|{state['ante']}|{state['dealer_idx']}|{state['level']}|{state['start_time']}")

# ==========================================
# 3. 형님이 주신 유틸리티 (핸드 강도 로직 등)
# ==========================================
def make_card(card):
    if not card: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

# ==========================================
# 4. 메인 UI 및 로직
# ==========================================
df, state = load_data()

# 블라인드 타이머 로직 (형님 원판 그대로)
elapsed = time.time() - state['start_time']
lvl_idx = int(elapsed // LEVEL_DURATION)
if lvl_idx < len(BLIND_STRUCTURE):
    sb_new, bb_new, ante_new = BLIND_STRUCTURE[lvl_idx]
    state['sb'], state['bb'], state['ante'], state['level'] = sb_new, bb_new, ante_new, lvl_idx + 1
    time_left = max(0, int((lvl_idx + 1) * LEVEL_DURATION - elapsed))
    timer_str = f"{time_left//60:02d}:{time_left%60:02d}"
else:
    timer_str = "MAX LEVEL"

if 'my_seat' not in st.session_state:
    st.title("🦁 몬스터 토너먼트 - 멀티")
    u_name = st.text_input("닉네임", value="👑 형님")
    if st.button("랜덤 빈자리 입장"):
        empty_seats = df[df['is_joined'] == False].index.tolist()
        if u_name and empty_seats:
            idx = random.choice(empty_seats)
            df.at[idx, 'name'] = u_name; df.at[idx, 'is_joined'] = True; df.at[idx, 'status'] = 'alive'
            if df['is_joined'].sum() == 1: df.at[idx, 'role'] = 'D'
            save_data(df, state); st.session_state['my_seat'] = idx; st.rerun()
    st.stop()

my_idx = st.session_state['my_seat']
if state['turn'] != my_idx and state['phase'] != 'SHOWDOWN':
    time.sleep(2); st.rerun()

# 상단 HUD (형님 원판 폼)
st.markdown(f'<div class="top-hud"><div>LEVEL {state["level"]}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {state["sb"]}/{state["bb"]} (A{state["ante"]})</div><div>📊 Avg: 60,000</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    html_code = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_list = state['comm'].split(',')
    display_comm = "".join([make_card(c) for c in comm_list[:state['open']]])
    
    for i in range(9):
        p = df.iloc[i]
        active = "active-turn" if state['turn'] == i and p['is_joined'] else ""
        hero_style = "hero-seat" if i == my_idx else ""
        role_badge = f'<div class="role-badge role-{p["role"]}">{p["role"]}</div>' if p['role'] else ""
        
        if i == my_idx or state['phase'] == 'SHOWDOWN':
            h = str(p['hand']).split(',')
            cards = f"<div style='margin-top:5px;'>{make_card(h[0])}{make_card(h[1])}</div>"
        else:
            cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>" if p['is_joined'] else "<div style='color:#444;'>Empty</div>"
        
        html_code += f'<div class="seat pos-{i} {active} {hero_style}">{role_badge}<div>SEAT {i+1}</div><div><b>{p["name"]}</b></div><div>Entry: {int(p["buyin"])}/3</div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'

    html_code += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white; width:100%;"><h2>Pot: {state["pot"]:,}</h2><div style="margin:20px 0;">{display_comm}</div><p>{state["msg"]}</p></div></div>'
    st.markdown(html_code, unsafe_allow_html=True)

with col_controls:
    st.markdown("### 🎮 Control Panel")
    if state['turn'] == my_idx:
        st.success("📢 형님 차례입니다!")
        to_call = int(state['cur_bet']) - int(df.at[my_idx, 'bet'])
        if st.button(f"✅ 콜/체크 ({to_call:,})", use_container_width=True):
            df.at[my_idx, 'stack'] -= to_call; df.at[my_idx, 'bet'] += to_call; state['pot'] += to_call
            df.at[my_idx, 'action'] = "Call" if to_call > 0 else "Check"
            state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
        
        raise_amt = st.number_input("Raise Amt", min_value=int(state['cur_bet']*2), step=100)
        if st.button("🚀 레이즈", use_container_width=True):
            added = raise_amt - df.at[my_idx, 'bet']
            df.at[my_idx, 'stack'] -= added; df.at[my_idx, 'bet'] = raise_amt; state['pot'] += added
            state['cur_bet'] = raise_amt; df.at[my_idx, 'action'] = "Raise"
            state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()

        if st.button("❌ 폴드", use_container_width=True):
            df.at[my_idx, 'action'] = "Fold"; state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
        
        if st.button("➡️ 다음 단계 (딜러)", type="primary", use_container_width=True):
            state['open'] = 3 if state['open'] == 0 else min(5, state['open'] + 1)
            if state['open'] == 5: state['phase'] = 'SHOWDOWN'
            save_data(df, state); st.rerun()
    else:
        st.info("다른 플레이어 대기 중...")
    
    if st.sidebar.button("💾 데이터 초기화"): init_game(); st.rerun()
