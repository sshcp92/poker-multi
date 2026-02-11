import streamlit as st
import pandas as pd
import random
import time

# ==========================================
# 1. 형님 원판 디자인 & 설정 (절대 고정)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

# 형님 원본 데이터 100% 복구
BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800),
    (500, 1000, 1000), (1000, 2000, 2000), (2000, 4000, 4000), (5000, 10000, 10000)
]
LEVEL_DURATION = 600
RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']

# [형님 원판 CSS 100% 복사]
st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 16px; }
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container { position:relative; width:100%; height:650px; margin:0 auto; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
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
# 2. 게임 엔진 (빤짝임 방지용 초고속 로직)
# ==========================================
if 'game_init' not in st.session_state:
    deck = [r+s for r in '23456789TJQKA' for s in ['♠', '♥', '♦', '♣']]
    random.shuffle(deck)
    st.session_state['game_init'] = True
    st.session_state['players'] = [{'name': 'Empty', 'is_joined': False, 'stack': 60000, 'hand': [deck.pop(), deck.pop()], 'bet': 0, 'role': '', 'action': ''} for _ in range(9)]
    st.session_state['pot'] = 0
    st.session_state['comm'] = [deck.pop() for _ in range(5)]
    st.session_state['open'] = 0
    st.session_state['turn'] = 0
    st.session_state['start_time'] = time.time()
    st.session_state['phase'] = 'PREFLOP'

# 유틸리티 함수
def make_card(card):
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

# ==========================================
# 3. 메인 UI (입장 화면)
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 몬스터 토너먼트 - 초고속 FIX")
    u_name = st.text_input("닉네임 입력", value="👑 형님")
    if st.button("즉시 입장하기", type="primary"):
        # 빈자리 찾기
        for i, p in enumerate(st.session_state['players']):
            if not p['is_joined']:
                st.session_state['players'][i]['name'] = u_name
                st.session_state['players'][i]['is_joined'] = True
                st.session_state['my_seat'] = i
                if sum(p['is_joined'] for p in st.session_state['players']) == 1:
                    st.session_state['players'][i]['role'] = 'D'
                st.rerun()
    st.stop()

# ==========================================
# 4. 게임 테이블 (형님 원판 폼 그대로)
# ==========================================
my_idx = st.session_state['my_seat']
elapsed = time.time() - st.session_state['start_time']
lvl_idx = min(len(BLIND_STRUCTURE)-1, int(elapsed // LEVEL_DURATION))
sb, bb, ante = BLIND_STRUCTURE[lvl_idx]
timer_str = f"{int(600 - (elapsed % 600)) // 60:02d}:{int(600 - (elapsed % 600)) % 60:02d}"

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl_idx+1}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb}</div><div>📊 Avg: 60,000</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    html_code = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_display = "".join([make_card(c) for c in st.session_state['comm'][:st.session_state['open']]])
    
    for i, p in enumerate(st.session_state['players']):
        active = "active-turn" if st.session_state['turn'] == i and p['is_joined'] else ""
        hero = "hero-seat" if i == my_idx else ""
        role = f'<div class="role-badge role-{p["role"]}">{p["role"]}</div>' if p['role'] else ""
        cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>" if i == my_idx else "<div>🂠 🂠</div>"
        
        html_code += f'<div class="seat pos-{i} {active} {hero}">{role}<div><b>{p["name"]}</b></div><div>🪙 {p["stack"]:,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'

    html_code += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white; width:100%;"><h2>Pot: {st.session_state["pot"]:,}</h2><div>{comm_display}</div></div></div>'
    st.markdown(html_code, unsafe_allow_html=True)

with col_controls:
    st.markdown("### 🎮 Control")
    if st.button("✅ 체크/콜"):
        st.session_state['pot'] += 200
        st.session_state['turn'] = (st.session_state['turn'] + 1) % 9
        st.rerun()
    if st.button("➡️ 카드 열기 (딜러)"):
        st.session_state['open'] = min(5, st.session_state['open'] + 3 if st.session_state['open']==0 else st.session_state['open']+1)
        st.rerun()
    if st.sidebar.button("💾 판 새로고침"):
        del st.session_state['game_init']
        st.rerun()
