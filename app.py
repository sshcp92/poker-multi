import streamlit as st
import pandas as pd
import random
import time
import os
from datetime import datetime

# ==========================================
# 1. 설정 및 초기화
# ==========================================
st.set_page_config(layout="wide", page_title="♠️ 우리들의 포커판", page_icon="🃏")

# 데이터 파일 (이게 서버 역할 함)
DATA_FILE = "poker_db.csv"

# 카드 덱 생성 함수
def new_deck():
    ranks = '23456789TJQKA'
    suits = ['♠', '♥', '♦', '♣']
    deck = [r+s for r in ranks for s in suits]
    random.shuffle(deck)
    return deck

# 게임 상태 초기화 (리셋)
def init_game():
    deck = new_deck()
    # 4명 플레이어 초기화
    players = []
    for i in range(4):
        players.append({
            'name': f'Player {i+1}', 
            'seat': i, 
            'stack': 10000,  # 시작 자금 1만원
            'hand': f"{deck.pop()},{deck.pop()}", # 핸드 2장
            'bet': 0, 
            'action': '', 
            'status': 'alive',
            'last_active': time.time()
        })
    
    # 커뮤니티 카드 5장 미리 뽑아둠 (아직 안 보여줌)
    community = [deck.pop() for _ in range(5)]
    
    # 데이터프레임으로 변환
    df = pd.DataFrame(players)
    
    # 게임 상태 저장
    state = {
        'pot': 0,
        'current_bet': 0,
        'turn_idx': 0, # 0번 플레이어부터 시작
        'phase': 'PREFLOP', # PREFLOP -> FLOP -> TURN -> RIVER -> SHOWDOWN
        'community_cards': ",".join(community),
        'community_open_idx': 0, # 0: 안보임, 3: 플랍, 4: 턴, 5: 리버
        'msg': "게임이 시작되었습니다! Player 1부터 배팅하세요.",
        'update_time': time.time()
    }
    
    save_data(df, state)

# 데이터 저장 (CSV로 저장해서 공유)
def save_data(df, state):
    # 플레이어 정보 저장
    df.to_csv(DATA_FILE, index=False)
    # 게임 상태 별도 저장 (꼼수: csv 파일 맨 끝에 주석처럼 달거나 별도 파일 써야 함. 
    # 여기서는 간단하게 별도 파일 state.csv 사용)
    with open("state.txt", "w") as f:
        f.write(f"{state['pot']}|{state['current_bet']}|{state['turn_idx']}|{state['phase']}|{state['community_cards']}|{state['community_open_idx']}|{state['msg']}|{state['update_time']}")

# 데이터 불러오기
def load_data():
    if not os.path.exists(DATA_FILE) or not os.path.exists("state.txt"):
        init_game()
        
    df = pd.read_csv(DATA_FILE)
    
    with open("state.txt", "r") as f:
        content = f.read().split('|')
        state = {
            'pot': int(content[0]),
            'current_bet': int(content[1]),
            'turn_idx': int(content[2]),
            'phase': content[3],
            'community_cards': content[4],
            'community_open_idx': int(content[5]),
            'msg': content[6],
            'update_time': float(content[7])
        }
    return df, state

# ==========================================
# 2. 게임 로직
# ==========================================
def next_turn(df, state):
    # 다음 살아있는 사람 찾기
    original_idx = state['turn_idx']
    next_idx = (original_idx + 1) % 4
    
    # 한 바퀴 돌았는지 확인 (phase 넘기기용)
    # (여기서는 간단하게 4명 다 돌면 다음 페이즈로 넘기는 로직)
    # 실제로는 배팅액 맞을 때까지 돌아야 하지만 약식 구현
    
    state['turn_idx'] = next_idx
    
    # 턴 넘기면서 간단하게 페이즈 진행 (테스트용)
    if next_idx == 0: # 한 바퀴 돎
        if state['phase'] == 'PREFLOP': 
            state['phase'] = 'FLOP'; state['community_open_idx'] = 3
            state['msg'] = "플랍이 열렸습니다!"
        elif state['phase'] == 'FLOP': 
            state['phase'] = 'TURN'; state['community_open_idx'] = 4
            state['msg'] = "턴 카드 오픈!"
        elif state['phase'] == 'TURN': 
            state['phase'] = 'RIVER'; state['community_open_idx'] = 5
            state['msg'] = "리버 오픈! 마지막 배팅!"
        elif state['phase'] == 'RIVER':
            state['phase'] = 'SHOWDOWN'
            state['msg'] = "쇼다운! 승자를 확인하세요. (새 게임: 리셋 버튼)"

    save_data(df, state)

# ==========================================
# 3. UI 화면 (친구들이 보는 화면)
# ==========================================

# 1. 로그인 (내 자리 선택)
if 'my_seat' not in st.session_state:
    st.title("🃏 친구들과 포커 한판")
    st.write("자리를 선택하면 게임에 입장합니다.")
    cols = st.columns(4)
    for i in range(4):
        if cols[i].button(f"Player {i+1}"):
            st.session_state['my_seat'] = i
            st.rerun()
    st.stop()

# 2. 게임 화면 로드
try:
    df, state = load_data()
except:
    init_game() # 파일 꼬이면 초기화
    df, state = load_data()

my_seat = st.session_state['my_seat']
me = df.iloc[my_seat]

# 자동 새로고침 (내 턴 아니면 2초마다)
if state['turn_idx'] != my_seat and state['phase'] != 'SHOWDOWN':
    time.sleep(2)
    st.rerun()

# [화면 구성]
st.markdown(f"### 👤 나는 : **Player {my_seat+1}** (💰 {me['stack']:,})")

# 커뮤니티 카드 표시
comm_cards = state['community_cards'].split(',')
visible_comm = comm_cards[:state['community_open_idx']]
hidden_comm = ["🂠"] * (5 - state['community_open_idx'])
final_comm_display = " ".join(visible_comm + hidden_comm)

st.markdown(f"""
<div style="text-align:center; padding:20px; background:#222; border-radius:10px; margin-bottom:10px;">
    <h3 style="color:#ffd700;">POT: {state['pot']:,}</h3>
    <h1 style="font-size:40px;">{final_comm_display}</h1>
    <p style="color:#aaa;">{state['msg']}</p>
</div>
""", unsafe_allow_html=True)

# 플레이어들 자리 배치
cols = st.columns(4)
for i in range(4):
    p = df.iloc[i]
    is_turn = (i == state['turn_idx']) and (state['phase'] != 'SHOWDOWN')
    border_color = "red" if is_turn else "#444"
    bg_color = "#333" if is_turn else "#111"
    
    # 카드 보여주기 (내 거만 보임, 쇼다운 때는 다 보임)
    if i == my_seat or state['phase'] == 'SHOWDOWN':
        hand_display = p['hand'].replace(",", " ")
    else:
        hand_display = "🂠 🂠"

    cols[i].markdown(f"""
    <div style="border:2px solid {border_color}; background:{bg_color}; padding:10px; border-radius:5px; text-align:center;">
        <div><b>{p['name']}</b></div>
        <div>💰 {p['stack']}</div>
        <div style="font-size:20px; margin:5px;">{hand_display}</div>
        <div style="color:cyan;">{p['action']}</div>
    </div>
    """, unsafe_allow_html=True)

# 내 컨트롤 패널 (내 턴일 때만)
st.markdown("---")
if state['phase'] == 'SHOWDOWN':
    if st.button("🔄 새 게임 시작 (Reset)"):
        init_game()
        st.rerun()
elif state['turn_idx'] == my_seat:
    st.success("⚡ 당신 차례입니다!")
    c1, c2, c3 = st.columns(3)
    
    if c1.button("Check / Call"):
        # 로직: 배팅액 맞추기 (생략, 단순 진행)
        df.at[my_seat, 'action'] = "Call"
        df.at[my_seat, 'stack'] -= 100 # 참가비 100원 냄 (약식)
        state['pot'] += 100
        next_turn(df, state)
        st.rerun()
        
    if c2.button("Raise 500"):
        df.at[my_seat, 'action'] = "Raise"
        df.at[my_seat, 'stack'] -= 500
        state['pot'] += 500
        next_turn(df, state)
        st.rerun()
        
    if c3.button("Fold"):
        df.at[my_seat, 'action'] = "Fold"
        df.at[my_seat, 'status'] = "folded"
        next_turn(df, state)
        st.rerun()
else:
    st.info(f"⏳ Player {state['turn_idx']+1}님이 고민 중입니다...")
    if st.button("새로고침"):
        st.rerun()