import streamlit as st
import pandas as pd
import random
import time
import os
from datetime import datetime

# ==========================================
# 1. 디자인 및 스타일 (형님 코드 100% 복사)
# ==========================================
st.set_page_config(layout="wide", page_title="🦁 형님의 리얼 멀티 포커", page_icon="🦁")

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud {
    display: flex; justify-content: space-around; align-items: center;
    background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px;
    border: 1px solid #555; color: white; font-weight: bold; font-size: 16px;
}
.game-board-container { position:relative; width:100%; height:650px; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
.poker-table {
    position:absolute; top:45%; left:50%; transform:translate(-50%,-50%);
    width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723);
    border: 20px solid #281915; border-radius: 250px; box-shadow: inset 0 0 50px rgba(0,0,0,0.8);
}
.seat {
    position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666;
    border-radius:15px; color:white; text-align:center; display:flex; flex-direction:column;
    justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10;
}
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.active-turn { border:4px solid #ffd700; box-shadow:0 0 25px #ffd700; }
.my-seat { border: 4px solid #4caf50 !important; }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:28px; color:black; border:1px solid #ccc;}
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size:11px; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 멀티플레이어 데이터 엔진 (DB)
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
        players.append({
            'name': 'Empty', 'seat': i, 'stack': 60000, 
            'hand': f"{deck.pop()},{deck.pop()}", 'bet': 0, 
            'status': 'waiting', 'action': '', 'is_joined': False
        })
    df = pd.DataFrame(players)
    df.to_csv(DB_FILE, index=False)
    
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        comm = ",".join([deck.pop() for _ in range(5)])
        # pot|cur_bet|turn|phase|comm|open|msg
        f.write(f"0|200|0|PREFLOP|{comm}|0|친구들을 기다리고 있습니다!")

def load_data():
    if not os.path.exists(DB_FILE): init_game()
    df = pd.read_csv(DB_FILE)
    with open(STATE_FILE, "r", encoding='utf-8') as f:
        s = f.read().split('|')
        state = {'pot':int(s[0]), 'cur_bet':int(s[1]), 'turn':int(s[2]), 'phase':s[3], 'comm':s[4], 'open':int(s[5]), 'msg':s[6]}
    return df, state

def save_data(df, state):
    df.to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        f.write(f"{state['pot']}|{state['cur_bet']}|{state['turn']}|{state['phase']}|{state['comm']}|{state['open']}|{state['msg']}")

# ==========================================
# 3. 게임 로직 및 UI
# ==========================================
df, state = load_data()

# [입장 로직]
if 'my_seat' not in st.session_state:
    st.title("🃏 형님의 9-Max 멀티 포커판")
    u_name = st.text_input("닉네임 입력", placeholder="예: 경기도타짜")
    if st.button("랜덤 빈자리 입장하기", type="primary"):
        empty_seats = df[df['is_joined'] == False]['seat'].tolist()
        if not u_name: st.error("이름 써주십쇼!")
        elif not empty_seats: st.error("자리가 없어요!")
        else:
            idx = random.choice(empty_seats)
            df.at[idx, 'name'] = u_name; df.at[idx, 'is_joined'] = True; df.at[idx, 'status'] = 'alive'
            save_data(df, state); st.session_state['my_seat'] = idx; st.rerun()
    st.stop()

my_idx = st.session_state['my_seat']
if state['turn'] != my_idx and state['phase'] != 'SHOWDOWN':
    time.sleep(2); st.rerun()

# [테이블 렌더링]
st.markdown(f'<div class="top-hud"><div>PHASE: {state["phase"]}</div><div>💰 내 잔액: {df.iloc[my_idx]["stack"]:,}</div><div>📍 내 자리: {df.iloc[my_idx]["name"]}</div></div>', unsafe_allow_html=True)

html_code = '<div class="game-board-container"><div class="poker-table"></div>'
comm_list = state['comm'].split(',')
display_comm = "".join([f"<span class='card-span'>{c}</span>" for c in comm_list[:state['open']]])

for i in range(9):
    p = df.iloc[i]
    active = "active-turn" if state['turn'] == i and p['is_joined'] else ""
    my_hi = "my-seat" if i == my_idx else ""
    
    if i == my_idx or state['phase'] == 'SHOWDOWN':
        h = str(p['hand']).split(',')
        cards = f"<div style='margin-top:5px;'><span class='card-span'>{h[0]}</span><span class='card-span'>{h[1]}</span></div>"
    else:
        cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>" if p['is_joined'] else "<div style='color:#444;'>Empty</div>"
    
    html_code += f'<div class="seat pos-{i} {active} {my_hi}"><div><b>{p["name"]}</b></div><div>{int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'

html_code += f'<div class="center-hud" style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; width:100%; color:white;"><h2>POT: {state["pot"]:,}</h2><div>{display_comm}</div><p>{state["msg"]}</p></div></div>'
st.markdown(html_code, unsafe_allow_html=True)

# [컨트롤 패널]
st.markdown("---")
if state['turn'] == my_idx:
    st.info("📢 형님 차례입니다!")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("✅ Check/Call"):
        df.at[my_idx, 'action'] = "Call"; df.at[my_idx, 'stack'] -= 200; state['pot'] += 200
        state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
    if c2.button("🚀 Raise 2,000"):
        df.at[my_idx, 'action'] = "Raise"; df.at[my_idx, 'stack'] -= 2000; state['pot'] += 2000
        state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
    if c3.button("❌ Fold"):
        df.at[my_idx, 'action'] = "Fold"; state['turn'] = (state['turn'] + 1) % 9; save_data(df, state); st.rerun()
    if c4.button("➡️ 다음 단계 (딜러)"):
        state['open'] = 3 if state['open'] == 0 else min(5, state['open'] + 1)
        if state['open'] == 5: state['phase'] = 'SHOWDOWN'
        save_data(df, state); st.rerun()

if st.sidebar.button("💾 데이터 초기화"):
    init_game(); st.rerun()
