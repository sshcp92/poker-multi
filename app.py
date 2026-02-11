import streamlit as st
import pandas as pd
import random
import time
import os

# ==========================================
# 1. 디자인 및 스타일 (9-Max 간지 유지)
# ==========================================
st.set_page_config(layout="wide", page_title="🦁 형님의 리얼 멀티 포커", page_icon="🦁")

st.markdown("""<style>
.stApp {background-color:#121212;}
.game-board-container { position:relative; width:100%; height:600px; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; margin: 0 auto;}
.poker-table { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); width: 90%; height: 420px; background: radial-gradient(#5d4037, #3e2723); border: 20px solid #281915; border-radius: 250px; box-shadow: inset 0 0 50px rgba(0,0,0,0.8); }
.seat { position:absolute; width:120px; height:140px; background:#2c2c2c; border:2px solid #666; border-radius:15px; color:white; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center; z-index:10; font-size: 13px;}
.pos-0 {top:20px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:20px; right:25%;} .pos-4 {bottom:20px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:20px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:20px; left:25%;}
.active-turn { border:4px solid #ffd700; box-shadow:0 0 20px #ffd700; }
.my-seat { border: 3px solid #4caf50 !important; }
.card-span {background:white; padding:2px 4px; border-radius:4px; margin:1px; font-weight:bold; font-size:20px; color:black; border: 1px solid #ccc;}
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 관리 (오류 방지 로직 추가)
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
            'name': f'Empty', 
            'seat': i, 
            'stack': 60000, 
            'hand': f"{deck.pop()},{deck.pop()}", 
            'bet': 0, 
            'status': 'alive', 
            'action': '', 
            'is_joined': False
        })
    
    df = pd.DataFrame(players)
    df.to_csv(DB_FILE, index=False)
    
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        comm = ",".join([deck.pop() for _ in range(5)])
        f.write(f"0|200|0|PREFLOP|{comm}|0|게임을 시작하려면 입장하세요!")

def load_data():
    if not os.path.exists(DB_FILE) or not os.path.exists(STATE_FILE):
        init_game()
    
    df = pd.read_csv(DB_FILE)
    # KeyError 방지: 모든 컬럼이 있는지 강제 확인
    cols = ['name', 'seat', 'stack', 'hand', 'bet', 'status', 'action', 'is_joined']
    for col in cols:
        if col not in df.columns:
            init_game()
            df = pd.read_csv(DB_FILE)
            break

    with open(STATE_FILE, "r", encoding='utf-8') as f:
        s = f.read().split('|')
        state = {'pot':int(s[0]), 'cur_bet':int(s[1]), 'turn':int(s[2]), 'phase':s[3], 'comm':s[4], 'open':int(s[5]), 'msg':s[6]}
    return df, state

def save_data(df, state):
    df.to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        f.write(f"{state['pot']}|{state['cur_bet']}|{state['turn']}|{state['phase']}|{state['comm']}|{state['open']}|{state['msg']}")

# ==========================================
# 3. 입장 및 랜덤 좌석 배정 로직
# ==========================================
df, state = load_data()

if 'my_seat' not in st.session_state:
    st.title("🦁 형님의 리얼 멀티 포커판")
    st.markdown("---")
    user_name = st.text_input("사용할 닉네임을 입력하세요", placeholder="예: 한강타짜")
    
    if st.button("빈자리 랜덤 입장하기", type="primary"):
        if not user_name:
            st.error("닉네임을 입력해야 입장 가능합니다!")
        else:
            # 빈자리 찾기
            empty_seats = df[df['is_joined'] == False]['seat'].tolist()
            if not empty_seats:
                st.error("빈자리가 없습니다! ㅠㅠ")
            else:
                chosen_seat = random.choice(empty_seats)
                df.at[chosen_seat, 'name'] = user_name
                df.at[chosen_seat, 'is_joined'] = True
                save_data(df, state)
                st.session_state['my_seat'] = chosen_seat
                st.rerun()
    st.stop()

# ==========================================
# 4. 게임 화면 (디자인)
# ==========================================
my_idx = st.session_state['my_seat']
# 다른 사람이 들어왔는지 확인하기 위해 2초마다 갱신
if state['turn'] != my_idx and state['phase'] != 'SHOWDOWN':
    time.sleep(2); st.rerun()

st.markdown(f"### 📍 내 자리: **{df.iloc[my_idx]['name']}** (Player {my_idx+1}) | 💰 {df.iloc[my_idx]['stack']:,}")

html_code = '<div class="game-board-container"><div class="poker-table"></div>'
comm_list = state['comm'].split(',')
display_comm = "".join([f"<span class='card-span'>{c}</span>" for c in comm_list[:state['open']]]) if state['open'] > 0 else "<span style='color:#666;'>카드가 깔리는 중...</span>"

for i in range(9):
    p = df.iloc[i]
    active = "active-turn" if state['turn'] == i and p['is_joined'] else ""
    my_highlight = "my-seat" if i == my_idx else ""
    
    if i == my_idx or state['phase'] == 'SHOWDOWN':
        h = str(p['hand']).split(',')
        cards = f"<div style='margin-top:5px;'><span class='card-span'>{h[0]}</span><span class='card-span'>{h[1]}</span></div>"
    else:
        cards = "<div style='margin-top:5px; font-size:18px;'>🂠 🂠</div>" if p['is_joined'] else "<div style='color:#444;'>Empty</div>"
    
    name_display = f"<b>{p['name']}</b>" if p['is_joined'] else "<i>Waiting...</i>"
    stack_val = f"{int(p['stack']):,}" if p['is_joined'] else "-"
    
    html_code += f'<div class="seat pos-{i} {active} {my_highlight}"><div>{name_display}</div><div>{stack_val}</div>{cards}<div style="color:#ffeb3b; font-size:11px; font-weight:bold;">{p["action"]}</div></div>'

html_code += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white; width:100%;"><h2>POT: {state["pot"]:,}</h2><div style="margin-bottom:10px;">{display_comm}</div><p style="background:rgba(0,0,0,0.6); padding:5px; border-radius:5px;">{state["msg"]}</p></div></div>'
st.markdown(html_code, unsafe_allow_html=True)

# ==========================================
# 5. 액션 버튼 패널
# ==========================================
st.markdown("---")
if state['turn'] == my_idx and state['phase'] != 'SHOWDOWN':
    st.info("📢 형님 차례입니다!")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("✅ Check/Call", use_container_width=True):
        df.at[my_idx, 'action'] = "Call"; df.at[my_idx, 'stack'] -= 200; state['pot'] += 200
        state['turn'] = (state['turn'] + 1) % 9
        save_data(df, state); st.rerun()
    if c2.button("🚀 Raise 2,000", use_container_width=True):
        df.at[my_idx, 'action'] = "Raise"; df.at[my_idx, 'stack'] -= 2000; state['pot'] += 2000
        state['turn'] = (state['turn'] + 1) % 9
        save_data(df, state); st.rerun()
    if c3.button("❌ Fold", use_container_width=True):
        df.at[my_idx, 'action'] = "Fold"; state['turn'] = (state['turn'] + 1) % 9
        save_data(df, state); st.rerun()
    if c4.button("➡️ 다음 카드 열기", type="primary", use_container_width=True):
        if state['open'] == 0: state['open'] = 3; state['phase'] = 'FLOP'; state['msg'] = "플랍이 열렸습니다!"
        elif state['open'] == 3: state['open'] = 4; state['phase'] = 'TURN'; state['msg'] = "턴 카드가 공개되었습니다!"
        elif state['open'] == 4: state['open'] = 5; state['phase'] = 'RIVER'; state['msg'] = "마지막 리버 카드입니다!"
        else: state['phase'] = 'SHOWDOWN'; state['msg'] = "게임 종료!"
        save_data(df, state); st.rerun()

if st.sidebar.button("💾 판 갈기 (전체 초기화)"):
    init_game(); st.rerun()
