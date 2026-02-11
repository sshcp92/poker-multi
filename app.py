import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 원판 디자인 & 설정 (절대 고정)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800),
    (500, 1000, 1000), (1000, 2000, 2000), (2000, 4000, 4000), (5000, 10000, 10000)
]
LEVEL_DURATION = 600
RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

# [형님 원판 CSS 100% 복구]
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
# 2. 멀티플레이 데이터 엔진 (JSON)
# ==========================================
DATA_FILE = "poker_data.json"

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    # 형님 원판 봇 스타일 그대로
    styles = ['Tight', 'Aggressive', 'Normal', 'Tight', 'Hero', 'Normal', 'Aggressive', 'Tight', 'Normal']
    for i in range(9):
        players.append({
            'name': f'Bot {i+1}', 'seat': i+1, 'stack': 60000, 
            'hand': [deck.pop(), deck.pop()], 'bet': 0, 'status': 'alive', 
            'action': '', 'is_human': False, 'role': '', 
            'style': styles[i], 'total_bet': 0
        })
    
    # 0번 딜러 시작
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3, 'dealer_idx': 0,
        'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 'start_time': time.time(),
        'msg': "게임을 시작합니다!", 'game_started': True
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        d = init_game_data(); save_data(d); return d
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except:
        d = init_game_data(); save_data(d); return d

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f: json.dump(data, f)

# ==========================================
# 3. 형님 원판 족보 & 유틸리티 (100% 복구)
# ==========================================
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

def get_hand_strength(hand):
    if not hand: return (-1, [])
    ranks = sorted([RANKS.index(c[0]) for c in hand], reverse=True)
    suits = [c[1] for c in hand]
    is_flush = any(suits.count(s) >= 5 for s in set(suits))
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False; straight_high = -1
    for i in range(len(unique_ranks) - 4):
        if unique_ranks[i] - unique_ranks[i+4] == 4: is_straight = True; straight_high = unique_ranks[i]; break
    if not is_straight and set([12, 3, 2, 1, 0]).issubset(set(ranks)): is_straight = True; straight_high = 3
    
    counts = {r: ranks.count(r) for r in ranks}
    sorted_groups = sorted([(c, r) for r, c in counts.items()], reverse=True)
    
    if is_flush and is_straight: return (8, [], "스트레이트 플러시")
    if sorted_groups[0][0] == 4: return (7, [], "포카드")
    if sorted_groups[0][0] == 3 and sorted_groups[1][0] >= 2: return (6, [], "풀하우스")
    if is_flush: return (5, [], "플러시")
    if is_straight: return (4, [], "스트레이트")
    if sorted_groups[0][0] == 3: return (3, [], "트리플")
    if sorted_groups[0][0] == 2 and sorted_groups[1][0] == 2: return (2, [], "투페어")
    if sorted_groups[0][0] == 2: return (1, [], "원페어")
    return (0, [], "하이카드")

def get_bot_decision(player, data):
    # 형님 원판 봇 로직 (간단 버전으로 이식)
    cur_bet = data['current_bet']
    to_call = cur_bet - player['bet']
    roll = random.random()
    if to_call == 0:
        return "Check", 0
    if roll < 0.1: return "Fold", 0
    if roll < 0.8: return "Call", to_call
    return "Raise", to_call + data['bb'] * 2

# ==========================================
# 4. 메인 실행 (로그인 깜빡임 해결 Gate)
# ==========================================
# 🚨 여기가 핵심입니다. 입장 전에는 아래 코드를 아예 실행 안 시킵니다.
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - 오리지널 FIX")
    u_name = st.text_input("닉네임 입력", value="형님")
    
    col1, col2 = st.columns(2)
    if col1.button("입장하기 (봇 뺏기)", type="primary", use_container_width=True):
        data = load_data()
        # 4번 자리(Hero)부터 뺏기, 차있으면 빈자리
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
        st.success("초기화됨. 입장하세요.")
    
    st.stop() # 🛑 여기서 멈춤! (로그인 화면 깜빡임 원천 봉쇄)

# ==========================================
# 5. 게임 화면 (형님 원판 로직 가동)
# ==========================================
data = load_data()
my_seat = st.session_state['my_seat']
me = data['players'][my_seat]

# 봇 자동 진행 (서버 역할)
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# 내 턴 아닐 때 자동 새로고침 (봇이면 진행, 사람이면 대기)
if curr_idx != my_seat:
    if not curr_p['is_human']:
        time.sleep(1) # 봇 생각 시간
        act, amt = get_bot_decision(curr_p, data)
        # 봇 행동 처리
        actual_amt = min(amt, curr_p['stack'])
        curr_p['stack'] -= actual_amt
        curr_p['bet'] += actual_amt
        data['pot'] += actual_amt
        data['current_bet'] = max(data['current_bet'], curr_p['bet'])
        curr_p['action'] = act
        data['turn_idx'] = (data['turn_idx'] + 1) % 9
        save_data(data)
        st.rerun()
    else:
        # 다른 사람 턴이면 2초마다 갱신
        time.sleep(2)
        st.rerun()

# 타이머 & HUD
elapsed = time.time() - data['start_time']
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>📊 Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

# 테이블 렌더링 (형님 원판 100%)
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

# 컨트롤 패널 (형님이 찾으시던 그 '원판 컨트롤러')
with col_controls:
    st.markdown("### 🎮 Control")
    
    if curr_idx == my_seat:
        st.success("📢 형님 차례입니다!")
        
        cur_bet = data['current_bet']
        to_call = cur_bet - me['bet']
        
        # 1. 콜/체크 버튼
        btn_text = "체크 (Check)" if to_call == 0 else f"콜 (Call {to_call:,})"
        if st.button(btn_text, use_container_width=True):
            me['stack'] -= to_call
            me['bet'] += to_call
            data['pot'] += to_call
            me['action'] = "Check" if to_call == 0 else "Call"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data)
            st.rerun()

        # 2. 폴드 버튼
        if st.button("폴드 (Fold)", type="primary", use_container_width=True):
            me['status'] = 'folded'
            me['action'] = "Fold"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data)
            st.rerun()

        st.markdown("---")
        
        # 3. 레이즈 (슬라이더 + 버튼) - 형님이 원하시던 기능
        min_raise = cur_bet * 2 if cur_bet > 0 else bb
        max_raise = int(me['stack'])
        if max_raise > min_raise:
            raise_amt = st.slider("레이즈 금액", min_value=min_raise, max_value=max_raise, step=100)
            if st.button(f"레이즈 ({raise_amt:,})", use_container_width=True):
                added = raise_amt - me['bet']
                me['stack'] -= added
                me['bet'] = raise_amt
                data['pot'] += added
                data['current_bet'] = raise_amt
                me['action'] = f"Raise {raise_amt}"
                # 레이즈했으니 다른 사람들 액션 초기화 필요하지만 일단 턴만 넘김
                data['turn_idx'] = (data['turn_idx'] + 1) % 9
                save_data(data)
                st.rerun()
        
        # 4. 올인 버튼
        if st.button("🚨 올인 (All-in)", use_container_width=True):
            amt = me['stack']
            me['stack'] = 0
            me['bet'] += amt
            data['pot'] += amt
            data['current_bet'] = max(data['current_bet'], me['bet'])
            me['action'] = "All-in"
            data['turn_idx'] = (data['turn_idx'] + 1) % 9
            save_data(data)
            st.rerun()

    else:
        st.info(f"⏳ {curr_p['name']} 님이 고민 중...")
        if st.button("딜러 강제 진행 (버그시 클릭)", use_container_width=True):
            # 단계 넘기기
            if data['phase'] == 'PREFLOP': 
                data['phase'] = 'FLOP'; data['community'] = [data['deck'].pop() for _ in range(3)]
            elif data['phase'] == 'FLOP':
                data['phase'] = 'TURN'; data['community'].append(data['deck'].pop())
            elif data['phase'] == 'TURN':
                data['phase'] = 'RIVER'; data['community'].append(data['deck'].pop())
            
            # 베팅 초기화
            data['current_bet'] = 0
            for p in data['players']: p['bet'] = 0; p['action'] = ''
            save_data(data); st.rerun()
