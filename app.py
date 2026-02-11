import streamlit as st
import pandas as pd
import random
import time
import os

# 디자인 설정 (형님 원판)
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - 멀티", page_icon="🦁")

# 형님 로직 그대로
BLIND_STRUCTURE = [(100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800)]
LEVEL_DURATION = 600

# CSS 스타일 (형님 원판)
st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 16px; }
.game-board-container { position:relative; width:100%; height:650px; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
.poker-table { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723); border: 20px solid #281915; border-radius: 250px; }
.seat { position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666; border-radius:15px; color:white; text-align:center; display:flex; flex-direction:column; justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10; }
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; box-shadow:0 0 25px #ffd700; z-index: 20; }
.active-turn { border:4px solid #ffeb3b !important; }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:26px; color:black; border:1px solid #ccc;}
</style>""", unsafe_allow_html=True)

DB_FILE = "poker_db.csv"
STATE_FILE = "state.txt"

def init_game():
    ranks = '23456789TJQKA'
    suits = ['♠', '♥', '♦', '♣']
    deck = [r+s for r in ranks for s in suits]; random.shuffle(deck)
    players = []
    for i in range(9):
        players.append({'name': 'Empty', 'seat': i+1, 'stack': 60000, 'hand': f"{deck.pop()},{deck.pop()}", 'bet': 0, 'status': 'waiting', 'action': '', 'is_joined': False, 'role': '', 'buyin': 1})
    pd.DataFrame(players).to_csv(DB_FILE, index=False)
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        comm = ",".join([deck.pop() for _ in range(5)])
        f.write(f"0|200|0|PREFLOP|{comm}|0|Ready|100|200|0|0|1|{time.time()}")
    # 초기화 시 세션도 날려버림
    if 'my_seat' in st.session_state: del st.session_state['my_seat']

def load_data():
    try:
        df = pd.read_csv(DB_FILE).fillna('')
        with open(STATE_FILE, "r", encoding='utf-8') as f:
            s = f.read().split('|')
            state = {'pot':int(s[0]), 'cur_bet':int(s[1]), 'turn':int(s[2]), 'phase':s[3], 'comm':s[4], 'open':int(s[5]), 'msg':s[6], 'sb':s[7], 'bb':s[8], 'ante':s[9], 'dealer_idx':int(s[10]), 'level':int(s[11]), 'start_time':float(s[12])}
        return df, state
    except:
        init_game(); return load_data()

df, state = load_data()

# [입장 로직 보강]
if 'my_seat' not in st.session_state:
    st.title("🦁 몬스터 토너먼트")
    u_name = st.text_input("닉네임 입력", value="형님")
    if st.button("입장하기"):
        # 여기서 빈자리 체크 로직을 더 강력하게!
        empty_seats = df[df['is_joined'] == False].index.tolist()
        if not empty_seats:
            st.warning("자리가 꽉 찼습니다. 초기화를 한 번 눌러주세요!")
        else:
            idx = random.choice(empty_seats)
            df.at[idx, 'name'] = u_name
            df.at[idx, 'is_joined'] = True
            df.to_csv(DB_FILE, index=False)
            st.session_state['my_seat'] = idx
            st.rerun()
    
    if st.button("🆘 긴급! 서버 초기화 (안넘어갈 때 클릭)"):
        init_game()
        st.success("데이터가 초기화되었습니다. 다시 입장하세요!")
        st.rerun()
    st.stop()

# (이후 테이블 렌더링 코드는 동일...)
st.write(f"현재 내 자리: {st.session_state['my_seat'] + 1}번")
if st.sidebar.button("💾 판 갈기 (전체 리셋)"):
    init_game()
    st.rerun()
