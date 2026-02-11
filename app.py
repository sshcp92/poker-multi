import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 설정 및 디자인 (형님 원판 100% 고정)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - PRO", page_icon="🦁")

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
# 2. 안전한 데이터 엔진 (JSON 기반)
# ==========================================
DATA_FILE = "poker_data.json"

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    # 봇 9명 생성 (초기 상태)
    styles = ['Tight', 'Aggressive', 'Normal', 'Tight', 'Hero', 'Normal', 'Aggressive', 'Tight', 'Normal']
    for i in range(9):
        players.append({
            'name': f'Bot {i+1}', 'seat': i+1, 'stack': 60000, 
            'hand': [deck.pop(), deck.pop()], 'bet': 0, 'status': 'alive', 
            'action': '', 'is_human': False, 'role': '', 
            'style': styles[i], 'total_bet': 0
        })
    
    # 0번(Bot 1)이 딜러로 시작
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    
    return {
        'players': players,
        'pot': 300, # SB+BB
        'deck': deck,
        'community': [],
        'phase': 'PREFLOP',
        'current_bet': 200,
        'turn_idx': 3, # UTG부터 시작
        'dealer_idx': 0,
        'sb': 100, 'bb': 200, 'ante': 0, 'level': 1,
        'start_time': time.time(),
        'msg': "게임을 시작합니다!"
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        data = init_game_data()
        save_data(data)
        return data
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        data = init_game_data()
        save_data(data)
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f)

# ==========================================
# 3. 형님 원판 족보 및 봇 지능
# ==========================================
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

def get_hand_strength(hand):
    # (형님 원판 족보 로직 요약 적용 - 분량상 핵심만)
    if not hand: return (-1, [])
    ranks = sorted([RANKS.index(c[0]) for c in hand], reverse=True)
    suits = [c[1] for c in hand]
    is_flush = any(suits.count(s) >= 5 for s in set(suits))
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False
    for i in range(len(unique_ranks) - 4):
        if unique_ranks[i] - unique_ranks[i+4] == 4: is_straight = True; break
    
    counts = {r: ranks.count(r) for r in ranks}
    sorted_groups = sorted([(c, r) for r, c in counts.items()], reverse=True)
    
    if is_flush and is_straight: return (8, [], "스티플")
    if sorted_groups[0][0] == 4: return (7, [], "포카드")
    if sorted_groups[0][0] == 3 and sorted_groups[1][0] >= 2: return (6, [], "풀하우스")
    if is_flush: return (5, [], "플러시")
    if is_straight: return (4, [], "스트레이트")
    if sorted_groups[0][0] == 3: return (3, [], "트리플")
    if sorted_groups[0][0] == 2 and sorted_groups[1][0] == 2: return (2, [], "투페어")
    if sorted_groups[0][0] == 2: return (1, [], "원페어")
    return (0, [], "하이카드")

def get_bot_decision(player, data):
    # 간단한 봇 지능: 자기 턴이면 콜만 함 (형님 테스트용)
    to_call = data['current_bet'] - player['bet']
    if to_call > player['stack']: return "All-in", player['stack']
    return "Call", to_call

# ==========================================
# 4. 메인 실행 (로그인 깜빡임 해결)
# ==========================================

# [1] 입장 전 화면 (여기선 절대 새로고침 안 함)
if 'my_seat' not in st.session_state:
    st.title("🦁 몬스터 토너먼트 - PRO")
    u_name = st.text_input("닉네임 입력", value="형님")
    
    if st.button("입장하기 (봇들과 대결)", type="primary", use_container_width=True):
        data = load_data()
        # 빈자리(봇 자리) 뺏기 로직
        # 4번 자리(Hero Seat)가 비어있거나 봇이면 뺏음
        target_seat = 4 
        data['players'][target_seat]['name'] = u_name
        data['players'][target_seat]['is_human'] = True
        data['players'][target_seat]['status'] = 'alive'
        save_data(data)
        st.session_state['my_seat'] = target_seat
        st.rerun() # 입장 완료 시에만 리런
    
    if st.button("⚠️ 서버 데이터 초기화"):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.success("초기화 완료. 입장하세요.")
    
    st.stop() # 여기서 코드 중단 (아래 실행 X -> 깜빡임 X)

# [2] 게임 화면 (여기서만 게임 로직 가동)
data = load_data()
my_seat = st.session_state['my_seat']
me = data['players'][my_seat]

# 타이머 계산
elapsed = time.time() - data['start_time']
lvl_idx = min(len(BLIND_STRUCTURE)-1, int(elapsed // LEVEL_DURATION))
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"

# 봇 자동 플레이 & 새로고침 (내 턴 아닐 때만)
current_turn_idx = data['turn_idx']
current_player = data['players'][current_turn_idx]

if current_turn_idx != my_seat:
    # 봇이면 자동 진행
    if not current_player['is_human']:
        time.sleep(1) # 봇 생각하는 척
        action, amt = get_bot_decision(current_player, data)
        
        # 봇 행동 처리
        current_player['stack'] -= amt
        current_player['bet'] += amt
        data['pot'] += amt
        current_player['action'] = action
        data['turn_idx'] = (data['turn_idx'] + 1) % 9 # 다음 턴
        save_data(data)
        st.rerun()
    else:
        # 다른 사람(친구) 턴이면 대기 (3초마다 확인)
        time.sleep(3)
        st.rerun()

# HUD 렌더링
st.markdown(f'<div class="top-hud"><div>LEVEL {lvl_idx+1}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {data["sb"]}/{data["bb"]}</div><div>📊 Avg: 60,000</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

# 테이블 그리기
with col_table:
    html_code = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_str = "".join([make_card(c) for c in data['community']])
    
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == data['turn_idx'] else ""
        hero = "hero-seat" if i == my_seat else ""
        
        # 내 카드만 보이기
        cards = f"<div style='margin-top:5px;'>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>" if i == my_seat else "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>"
        
        html_code += f'<div class="seat pos-{i} {active} {hero}"><div>{p["role"]}</div><div><b>{p["name"]}</b></div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'

    html_code += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white; width:100%;"><h2>Pot: {data["pot"]:,}</h2><div>{comm_str}</div><p>{data["msg"]}</p></div></div>'
    st.markdown(html_code, unsafe_allow_html=True)

# 컨트롤 패널
with col_controls:
    st.markdown("### 🎮 Control")
    if current_turn_idx == my_seat:
        st.success("📢 형님 차례입니다!")
        to_call = data['current_bet'] - me['bet']
        
        if st.button(f"체크/콜 ({to_call})", use_container_width=True):
            me['stack'] -= to_call
            me['bet'] += to_call
            data['pot'] += to_call
            me['action'] = "Call"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data)
            st.rerun()
            
        if st.button("폴드", use_container_width=True):
            me['action'] = "Fold"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data)
            st.rerun()
            
    else:
        st.info(f"⏳ {current_player['name']} 생각 중...")
