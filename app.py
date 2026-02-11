import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 설정 및 디자인 (형님 원판 100%)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800),
    (500, 1000, 1000), (1000, 2000, 2000), (2000, 4000, 4000), (5000, 10000, 10000)
]
LEVEL_DURATION = 600
RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 16px; }
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container { position:relative; width:100%; height:650px; margin:0 auto; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
.poker-table { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723); border: 20px solid #281915; border-radius: 250px; box-shadow: inset 0 0 50px rgba(0,0,0,0.8); }
.seat { position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666; border-radius:15px; color:white; text-align:center; font-size:12px; display:flex; flex-direction:column; justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10; }
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; background:#3a3a3a; box-shadow:0 0 25px #ffd700; z-index: 20; transform: translateX(-50%) scale(1.1); }
.active-turn { border:4px solid #ffeb3b !important; box-shadow: 0 0 15px #ffeb3b; }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:26px; color:black; border:1px solid #ccc; line-height: 1.0;}
.role-badge { position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; color: black; font-weight: bold; line-height: 26px; border: 2px solid #333; z-index: 100; font-size: 14px; }
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000; z-index:100;}
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진 (재접속 기능 추가)
# ==========================================
DATA_FILE = "poker_v3.json" # 버전업 (충돌 방지)

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    styles = ['Tight', 'Aggressive', 'Normal', 'Tight', 'Hero', 'Normal', 'Aggressive', 'Tight', 'Normal']
    for i in range(9):
        players.append({
            'name': f'Bot {i+1}', 'seat': i+1, 'stack': 60000, 
            'hand': [deck.pop(), deck.pop()], 'bet': 0, 'status': 'alive', 
            'action': '', 'is_human': False, 'role': '', 
            'style': styles[i]
        })
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3,
        'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 'start_time': time.time(),
        'msg': "게임을 시작합니다!"
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        d = init_game_data(); save_data(d); return d
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            if 'players' not in data: raise ValueError
            return data
    except:
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        d = init_game_data(); save_data(d); return d

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f: json.dump(data, f)

# ==========================================
# 3. 족보 및 봇 로직
# ==========================================
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

def get_bot_decision(player, data):
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.15: return "Fold", 0
    if roll < 0.8: return "Call", to_call
    return "Raise", to_call + data['bb'] * 2

# ==========================================
# 4. 메인 실행 (재접속 기능 탑재)
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - Reconnect")
    u_name = st.text_input("닉네임 입력", value="형님")
    
    col1, col2 = st.columns(2)
    if col1.button("입장하기 (이어하기 가능)", type="primary", use_container_width=True):
        data = load_data()
        
        # [핵심] 이미 있는 닉네임인지 확인 (재접속 로직)
        found_seat = -1
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name:
                found_seat = i
                break
        
        if found_seat != -1:
            # 기존 자리 찾음 -> 바로 복구
            st.session_state['my_seat'] = found_seat
            st.success(f"👋 {u_name}님, 원래 자리로 돌아갑니다!")
            time.sleep(1)
            st.rerun()
        else:
            # 새 유저 -> 4번 자리(Hero)부터 뺏기
            target = 4
            if data['players'][4]['is_human']: 
                for i in range(9):
                    if not data['players'][i]['is_human']: target = i; break
            
            data['players'][target]['name'] = u_name
            data['players'][target]['is_human'] = True
            data['players'][target]['status'] = 'alive'
            save_data(data)
            st.session_state['my_seat'] = target
            st.rerun()

    if col2.button("⚠️ 서버 초기화", use_container_width=True):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.success("초기화 완료! 다시 입장하세요.")
    
    st.stop() 

# ==========================================
# 5. 게임 화면
# ==========================================
data = load_data()

# 데이터 오류 시 강제 로그아웃 (검은 화면 방지)
if st.session_state['my_seat'] >= len(data['players']):
    del st.session_state['my_seat']
    st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# 자동 진행 로직
if curr_idx != my_seat:
    if not curr_p['is_human']:
        time.sleep(1)
        act, amt = get_bot_decision(curr_p, data)
        actual_amt = min(amt, curr_p['stack'])
        curr_p['stack'] -= actual_amt; curr_p['bet'] += actual_amt
        data['pot'] += actual_amt; data['current_bet'] = max(data['current_bet'], curr_p['bet'])
        curr_p['action'] = act
        data['turn_idx'] = (data['turn_idx'] + 1) % 9
        save_data(data)
        st.rerun()
    else:
        # 다른 사람 턴일 때만 리프레시
        time.sleep(2)
        st.rerun()

# HUD
elapsed = time.time() - data['start_time']
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>📊 Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_str = "".join([make_card(c) for c in data['community']])
    
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == data['turn_idx'] else ""
        hero = "hero-seat" if i == my_seat else ""
        
        # 내 카드만 보임
        if i == my_seat:
            cards = f"<div style='margin-top:5px;'>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
        else:
            cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>"
            
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero}">{role}<div><b>{p["name"]}</b></div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><h2>Pot: {data["pot"]:,}</h2><div>{comm_str}</div></div></div>'
    st.markdown(html, unsafe_allow_html=True)

# 형님 원판 컨트롤러
with col_controls:
    st.markdown("### 🎮 Control")
    if curr_idx == my_seat:
        st.success("📢 형님 차례입니다!")
        to_call = data['current_bet'] - me['bet']
        
        if st.button("체크/콜", use_container_width=True):
            me['stack'] -= to_call; me['bet'] += to_call; data['pot'] += to_call
            me['action'] = "Call"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data); st.rerun()

        if st.button("폴드", type="primary", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "Fold"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data); st.rerun()
            
        st.markdown("---")
        min_raise = max(bb, data['current_bet'] * 2)
        if me['stack'] > min_raise:
            raise_amt = st.slider("레이즈 금액", int(min_raise), int(me['stack']), int(min_raise))
            if st.button("레이즈 확정", use_container_width=True):
                added = raise_amt - me['bet']
                me['stack'] -= added; me['bet'] = raise_amt
                data['pot'] += added; data['current_bet'] = raise_amt
                me['action'] = f"Raise {raise_amt}"
                data['turn_idx'] = (data['turn_idx'] + 1) % 9
                save_data(data); st.rerun()
        
        if st.button("🚨 올인", use_container_width=True):
            amt = me['stack']; me['stack'] = 0; me['bet'] += amt
            data['pot'] += amt; data['current_bet'] = max(data['current_bet'], me['bet'])
            me['action'] = "All-in"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data); st.rerun()
    else:
        st.info(f"⏳ {curr_p['name']} 턴...")
        # 딜러 강제 진행 버튼
        if st.button("딜러 카드 깔기 (강제)", use_container_width=True):
            if data['phase'] == 'PREFLOP': data['phase']='FLOP'; data['community']=[data['deck'].pop() for _ in range(3)]
            elif data['phase'] == 'FLOP': data['phase']='TURN'; data['community'].append(data['deck'].pop())
            elif data['phase'] == 'TURN': data['phase']='RIVER'; data['community'].append(data['deck'].pop())
            data['current_bet'] = 0
            for p in data['players']: p['bet'] = 0; p['action'] = ''
            save_data(data); st.rerun()
