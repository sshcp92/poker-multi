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
# 2. 데이터 엔진 (자동 복구 기능 탑재)
# ==========================================
DATA_FILE = "poker_v6.json"

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    styles = ['Tight', 'Aggressive', 'Normal', 'Tight', 'Hero', 'Normal', 'Aggressive', 'Tight', 'Normal']
    for i in range(9):
        players.append({
            'name': f'Bot {i+1}', 'seat': i+1, 'stack': 60000, 
            'hand': [deck.pop(), deck.pop()], 'bet': 0, 'status': 'alive', 
            'action': '', 'is_human': False, 'role': '', 'has_acted': False,
            'style': styles[i]
        })
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    players[1]['stack'] -= 100; players[1]['bet'] = 100; players[1]['action'] = 'SB 100'
    players[2]['stack'] -= 200; players[2]['bet'] = 200; players[2]['action'] = 'BB 200'
    
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3, 'dealer_idx': 0,
        'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 'start_time': time.time(),
        'msg': "게임을 시작합니다!"
    }

def load_data():
    if not os.path.exists(DATA_FILE): d = init_game_data(); save_data(d); return d
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            # [KeyError 방지] 필수 키가 없으면 강제 복구
            if 'dealer_idx' not in data or 'players' not in data:
                return init_game_data()
            return data
    except:
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        d = init_game_data(); save_data(d); return d

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f: json.dump(data, f)

# ==========================================
# 3. 족보 & 유틸리티 & 게임 로직
# ==========================================
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

def get_bot_decision(player, data):
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.1: return "Fold", 0
    return "Call", to_call

# [카드 실종 방지] 페이즈 넘길 때 무조건 저장
def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        winner = active[0]; winner['stack'] += data['pot']
        data['msg'] = f"🏆 {winner['name']} 승리!"; data['pot'] = 0; data['phase'] = 'GAME_OVER'
        save_data(data); return True # 즉시 저장

    bet_target = data['current_bet']
    all_acted = all(p['action'] != '' for p in active)
    all_matched = all(p['bet'] == bet_target or p['stack'] == 0 for p in active)
    
    if all_acted and all_matched:
        deck = data['deck']
        next_phase = False
        
        if data['phase'] == 'PREFLOP':
            data['phase'] = 'FLOP'; data['community'] = [deck.pop() for _ in range(3)]
            next_phase = True
        elif data['phase'] == 'FLOP':
            data['phase'] = 'TURN'; data['community'].append(deck.pop())
            next_phase = True
        elif data['phase'] == 'TURN':
            data['phase'] = 'RIVER'; data['community'].append(deck.pop())
            next_phase = True
        elif data['phase'] == 'RIVER':
            data['phase'] = 'GAME_OVER'; data['msg'] = "쇼다운! 결과 확인"
            save_data(data); return True
            
        if next_phase:
            data['current_bet'] = 0
            for p in data['players']:
                p['bet'] = 0; p['action'] = '' if p['status'] == 'alive' else p['action']
            
            # Dealer 다음 사람부터 턴
            dealer = data.get('dealer_idx', 0)
            for i in range(1, 10):
                idx = (dealer + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            save_data(data) # [중요] 카드 깔고 즉시 저장
            return True
    return False

# ==========================================
# 4. 로그인 및 입장
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - FINAL FIX")
    u_name = st.text_input("닉네임 입력", value="형님")
    
    col1, col2 = st.columns(2)
    if col1.button("입장하기", type="primary", use_container_width=True):
        data = load_data()
        found = -1
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name: found = i; break
        
        if found != -1: st.session_state['my_seat'] = found
        else:
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

    if col2.button("⚠️ 오류 해결 (서버 리셋)", use_container_width=True):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.success("해결됨. 입장하세요."); st.rerun()
    st.stop()

# ==========================================
# 5. 게임 엔진
# ==========================================
data = load_data()
if st.session_state['my_seat'] >= len(data['players']): del st.session_state['my_seat']; st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# 봇 순차 진행 (화면 렌더링 -> 1초 대기 -> 행동 -> 갱신)
if curr_idx != my_seat and data['phase'] != 'GAME_OVER':
    if not curr_p['is_human']:
        time.sleep(1) # [시각적 딜레이] 봇이 생각하는 척
        act, amt = get_bot_decision(curr_p, data)
        actual = min(amt, curr_p['stack'])
        curr_p['stack'] -= actual; curr_p['bet'] += actual
        data['pot'] += actual; data['current_bet'] = max(data['current_bet'], curr_p['bet'])
        curr_p['action'] = act
        
        # 다음 턴 찾기
        for i in range(1, 10):
            idx = (curr_idx + i) % 9
            if data['players'][idx]['status'] == 'alive':
                data['turn_idx'] = idx; break
        
        check_phase_end(data) # 페이즈 전환 체크
        save_data(data) # 저장
        st.rerun() # 화면 갱신
    else:
        time.sleep(2); st.rerun() # 다른 사람 턴일 때

# ==========================================
# 6. 화면 그리기 (카드 무조건 표시)
# ==========================================
elapsed = time.time() - data['start_time']
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>📊 Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    
    # [커뮤니티 카드 표시 강화]
    comm_cards = data.get('community', [])
    if not comm_cards: comm_display = "<span style='color:#777; font-size:20px;'>Preflop</span>"
    else: comm_display = "".join([make_card(c) for c in comm_cards])
    
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == data['turn_idx'] else ""
        hero = "hero-seat" if i == my_seat else ""
        
        if i == my_seat or data['phase'] == 'GAME_OVER': # 쇼다운 시 패 공개
            if p['hand']: cards = f"<div style='margin-top:5px;'>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
            else: cards = "<div></div>"
        else:
            cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>" if p['status'] == 'alive' else ""
            
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero}">{role}<div><b>{p["name"]}</b></div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><h2>Pot: {data["pot"]:,}</h2><div>{comm_display}</div><p>{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    st.markdown("### 🎮 Control")
    if data['turn_idx'] == my_seat and data['phase'] != 'GAME_OVER':
        st.success("📢 형님 차례입니다!")
        to_call = data['current_bet'] - me['bet']
        
        if st.button("체크/콜", use_container_width=True):
            me['stack'] -= to_call; me['bet'] += to_call; data['pot'] += to_call
            me['action'] = "Call" if to_call > 0 else "Check"
            
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            check_phase_end(data)
            save_data(data); st.rerun()

        if st.button("폴드", type="primary", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "Fold"
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            check_phase_end(data)
            save_data(data); st.rerun()
            
        st.markdown("---")
        min_raise = max(bb, data['current_bet'] * 2)
        if me['stack'] > min_raise:
            raise_amt = st.slider("레이즈", int(min_raise), int(me['stack']), int(min_raise))
            if st.button("레이즈 확정", use_container_width=True):
                added = raise_amt - me['bet']
                me['stack'] -= added; me['bet'] = raise_amt
                data['pot'] += added; data['current_bet'] = raise_amt
                me['action'] = f"Raise {raise_amt}"
                for i in range(1, 10):
                    idx = (my_seat + i) % 9
                    if data['players'][idx]['status'] == 'alive':
                        data['turn_idx'] = idx; break
                save_data(data); st.rerun()
        
        if st.button("🚨 올인", use_container_width=True):
            amt = me['stack']; me['stack'] = 0; me['bet'] += amt
            data['pot'] += amt; data['current_bet'] = max(data['current_bet'], me['bet'])
            me['action'] = "All-in"
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            save_data(data); st.rerun()

    elif data['phase'] == 'GAME_OVER':
        if st.button("▶️ 다음 판 (Next Hand)", type="primary", use_container_width=True):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
    else:
        st.info(f"⏳ {curr_p['name']} 턴... (1초 뒤 진행)")
