import streamlit as st
import pandas as pd
import random
import time
import os

# ==========================================
# 1. 디자인 및 스타일 (형님 원판 100% 복사)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - 멀티", page_icon="🦁")

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud {
    display: flex; justify-content: space-around; align-items: center;
    background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px;
    border: 1px solid #555; color: white; font-weight: bold; font-size: 16px;
}
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container {
    position:relative; width:100%; height:650px; margin:0 auto; 
    background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; 
}
.poker-table {
    position:absolute; top:45%; left:50%; transform:translate(-50%,-50%);
    width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723);
    border: 20px solid #281915; border-radius: 250px;
    box-shadow: inset 0 0 50px rgba(0,0,0,0.8), 0 10px 30px rgba(0,0,0,0.5);
}
.seat {
    position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666;
    border-radius:15px; color:white; text-align:center; font-size:12px;
    display:flex; flex-direction:column; justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10;
}
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; background:#3a3a3a; box-shadow:0 0 25px #ffd700; z-index: 20; }
.active-turn { border:4px solid #ffeb3b !important; box-shadow: 0 0 15px #ffeb3b; }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:28px; color:black; border:1px solid #ccc; line-height: 1.0;}
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000;}
.bet-chip {color:#42a5f5; font-weight:bold; font-size:13px;}
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 멀티플레이 데이터 엔진 (DB)
# ==========================================
DB_FILE = "poker_db.csv"
STATE_FILE = "state.txt"

def init_game():
    ranks = '23456789TJQKA'
    suits = ['♠', '♥', '♦', '♣']
    deck = [r+s for r in ranks for s in suits]
    random.shuffle(deck)
    players = []
    for i in range(9):
        players.append({'name': 'Empty', 'seat': i, 'stack': 60000, 'hand': f"{deck.pop()},{deck.pop()}", 'bet': 0, 'status': 'waiting', 'action': '', 'is_joined': False, 'buyin': 1})
    pd.DataFrame(players).to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        comm = ",".join([deck.pop() for _ in range(5)])
        f.write(f"0|200|0|PREFLOP|{comm}|0|친구들을 기다리고 있습니다!|100|200|0|00:00")

def load_data():
    try:
        df = pd.read_csv(DB_FILE)
        with open(STATE_FILE, "r", encoding='utf-8') as f:
            s = f.read().split('|')
            state = {'pot':int(s[0]), 'cur_bet':int(s[1]), 'turn':int(s[2]), 'phase':s[3], 'comm':s[4], 'open':int(s[5]), 'msg':s[6], 'sb':s[7], 'bb':s[8], 'ante':s[9], 'timer':s[10]}
        return df, state
    except:
        init_game()
        return load_data()

def save_data(df, state):
    df.to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        f.write(f"{state['pot']}|{state['cur_bet']}|{state['turn']}|{state['phase']}|{state['comm']}|{state['open']}|{state['msg']}|{state['sb']}|{state['bb']}|{state['ante']}|{state['timer']}")

# ==========================================
# 3. 메인 로직 및 입장 (랜덤 배정)
# ==========================================
df, state = load_data()

if 'my_seat' not in st.session_state:
    st.title("🦁 몬스터 토너먼트 멀티플레이")
    u_name = st.text_input("닉네임을 입력하세요", placeholder="예: 👑 형님")
    if st.button("빈자리 랜덤 입장하기", type="primary"):
        empty_seats = df[df['is_joined'] == False]['seat'].tolist()
        if not u_name: st.error("이름을 입력해주세요!")
        elif not empty_seats: st.error("만석입니다!")
        else:
            idx = random.choice(empty_seats)
            df.at[idx, 'name'] = u_name; df.at[idx, 'is_joined'] = True; df.at[idx, 'status'] = 'alive'
            save_data(df, state); st.session_state['my_seat'] = idx; st.rerun()
    st.stop()

my_idx = st.session_state['my_seat']
if state['turn'] != my_idx and state['phase'] != 'SHOWDOWN':
    time.sleep(2); st.rerun()

# [HUD 상단]
st.markdown(f"""<div class="top-hud"><div>LEVEL 1</div><div class="hud-time">⏱️ {state['timer']}</div><div>🟡 {state['sb']}/{state['bb']} (A{state['ante']})</div><div>📊 Avg: 60,000</div></div>""", unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    # [포커 테이블 메인]
    html_code = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_list = state['comm'].split(',')
    display_comm = "".join([f"<span class='card-span'>{c}</span>" for c in comm_list[:state['open']]]) if state['open'] > 0 else "Waiting..."
    
    for i in range(9):
        p = df.iloc[i]
        active = "active-turn" if state['turn'] == i and p['is_joined'] else ""
        hero_style = "hero-seat" if i == my_idx else ""
        
        # 카드 표시
        if i == my_idx or state['phase'] == 'SHOWDOWN':
            h = str(p['hand']).split(',')
            cards = f"<div style='margin-top:5px;'><span class='card-span'>{h[0]}</span><span class='card-span'>{h[1]}</span></div>"
        else:
            cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>" if p['is_joined'] else "<div style='color:#444;'>Empty</div>"
        
        act_badge = f"<div class='action-badge'>{p['action']}</div>" if p['action'] else ""
        bet_display = f"<div class='bet-chip'>Bet: {int(p['bet']):,}</div>" if p['bet'] > 0 else ""
        
        html_code += f'<div class="seat pos-{i} {active} {hero_style}"><div>SEAT {i+1}</div><div><b>{p["name"]}</b></div><div>Entry: {int(p["buyin"])}/3</div><div>🪙 {int(p["stack"]):,}</div>{cards}{bet_display}{act_badge}</div>'

    html_code += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white; width:100%;"><h2>Pot: {state["pot"]:,}</h2><div style="margin:20px 0;">{display_comm}</div><div style="color:#aaa;">{state["phase"]}</div><div style="color:#ffcc80; font-weight:bold;">{state["msg"]}</div></div></div>'
    st.markdown(html_code, unsafe_allow_html=True)

with col_controls:
    st.markdown("### 🎮 Control Panel")
    if state['turn'] == my_idx:
        st.success("당신의 차례입니다!")
        if st.button("✅ 체크/콜", use_container_width=True):
            df.at[my_idx, 'action'] = "Call"; df.at[my_idx, 'stack'] -= 200; state['pot'] += 200
            state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
        if st.button("🚀 레이즈 2,000", use_container_width=True):
            df.at[my_idx, 'action'] = "Raise"; df.at[my_idx, 'stack'] -= 2000; state['pot'] += 2000
            state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
        if st.button("❌ 폴드", use_container_width=True):
            df.at[my_idx, 'action'] = "Fold"; state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
        if st.button("➡️ 다음 카드 (딜러)", type="primary", use_container_width=True):
            state['open'] = 3 if state['open'] == 0 else min(5, state['open'] + 1)
            if state['open'] == 5: state['phase'] = 'SHOWDOWN'
            save_data(df, state); st.rerun()
    else:
        st.info("다른 플레이어 대기 중...")
    
    if st.button("🔄 화면 새로고침", use_container_width=True): st.rerun()
    if st.sidebar.button("💾 판 갈기 (초기화)"): init_game(); st.rerun()
