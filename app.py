import streamlit as st
import random
import time
import os
import json
import shutil

# ==========================================
# 1. 설정 & 디자인 (모바일 최적화 고정)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - FINAL", page_icon="🦁")

BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800),
    (500, 1000, 1000), (1000, 2000, 2000), (2000, 4000, 4000), (5000, 10000, 10000)
]
LEVEL_DURATION = 600
TURN_TIMEOUT = 30 
AUTO_NEXT_HAND_DELAY = 10 

RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 8px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 13px; }
.hud-time { color: #ffeb3b; font-size: 16px; }
.game-board-container { position:relative; width:100%; min-height:450px; height: 65vh; margin:0 auto; background-color:#1e1e1e; border-radius:20px; border:3px solid #333; overflow: hidden; }
.poker-table { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width: 92%; height: 75%; background: radial-gradient(#5d4037, #3e2723); border: 12px solid #281915; border-radius: 150px; box-shadow: inset 0 0 30px rgba(0,0,0,0.8); }
.seat { position:absolute; width:95px; height:105px; background:#2c2c2c; border:2px solid #666; border-radius:12px; color:white; text-align:center; font-size:10px; display:flex; flex-direction:column; justify-content:center; align-items:center; z-index:10; }
.pos-0 {top:5%; right:20%;} .pos-1 {top:25%; right:3%;} .pos-2 {bottom:25%; right:3%;} .pos-3 {bottom:5%; right:20%;} 
.pos-4 {bottom:2%; left:50%; transform:translateX(-50%);} 
.pos-5 {bottom:5%; left:20%;} .pos-6 {bottom:25%; left:3%;} .pos-7 {top:25%; left:3%;} .pos-8 {top:5%; left:20%;}
.hero-seat { border:3px solid #ffd700; background:#3a3a3a; box-shadow:0 0 15px #ffd700; z-index: 20; }
.active-turn { border:3px solid #ffeb3b !important; box-shadow: 0 0 15px #ffeb3b; }
.card-span {background:white; padding:1px 4px; border-radius:4px; margin:1px; font-weight:bold; font-size:18px; color:black; border:1px solid #ccc; display:inline-block;}
.comm-card-span { font-size: 28px !important; padding: 3px 6px !important; }
.role-badge { position: absolute; top: -8px; left: -8px; width: 24px; height: 24px; border-radius: 50%; color: black; font-weight: bold; line-height: 22px; border: 1px solid #333; z-index: 100; font-size: 11px; }
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.action-badge { position: absolute; bottom: -12px; background:#ffeb3b; color:black; font-weight:bold; padding:1px 5px; border-radius:4px; font-size: 10px; border: 1px solid #000; z-index:100; white-space: nowrap; }
.fold-text { color: #ff5252; font-weight: bold; font-size: 14px; }
.folded-seat { opacity: 0.4; }
.turn-timer { position: absolute; top: -20px; width: 100%; text-align: center; color: #ff5252; font-weight: bold; font-size: 12px; }
.stButton>button { font-size: 14px !important; height: 40px !important; }
div[data-baseweb="input"] { background-color: #333; color: white; border: 1px solid #555; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진 (안전성 강화 V7)
# ==========================================
DATA_FILE = "poker_final_v7.json"

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    bot_names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India"]
    styles = ['Tight', 'Aggressive', 'Normal', 'Tight', 'Hero', 'Normal', 'Aggressive', 'Tight', 'Normal']
    for i in range(9):
        players.append({
            'name': bot_names[i], 'seat': i+1, 'stack': 60000, 
            'hand': [deck.pop(), deck.pop()], 'bet': 0, 'status': 'alive', 
            'action': '', 'is_human': False, 'role': '', 'has_acted': False, 'style': styles[i],
            'rebuy_count': 0
        })
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    players[1]['stack']-=100; players[1]['bet']=100; players[1]['action']='SB 100'; players[1]['has_acted']=True
    players[2]['stack']-=200; players[2]['bet']=200; players[2]['action']='BB 200'; players[2]['has_acted']=True
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3,
        'dealer_idx': 0, 'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 
        'start_time': time.time(), 'msg': "게임을 시작합니다!", 'turn_start_time': time.time(), 'game_over_time': 0
    }

def load_data():
    for _ in range(5):
        try:
            if not os.path.exists(DATA_FILE): d = init_game_data(); save_data(d); return d
            with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
        except: time.sleep(0.1)
    return init_game_data()

def save_data(data):
    try:
        temp = DATA_FILE + ".tmp"
        with open(temp, "w", encoding='utf-8') as f: json.dump(data, f)
        shutil.move(temp, DATA_FILE)
    except: pass

def reset_for_next_hand(old_data):
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    new_dealer_idx = (old_data['dealer_idx'] + 1) % 9
    players = old_data['players']
    elapsed = time.time() - old_data['start_time']
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl-1]
    
    current_pot = 0
    for i, p in enumerate(players):
        p['status'] = 'alive' if p['stack'] > 0 else 'folded'
        p['hand'] = [deck.pop(), deck.pop()] if p['status'] == 'alive' else []
        p['bet'] = 0; p['action'] = ''; p['has_acted'] = False; p['role'] = ''
        if p['status'] == 'alive' and ante_amt > 0:
            actual_ante = min(p['stack'], ante_amt)
            p['stack'] -= actual_ante
            current_pot += actual_ante

    sb_idx = (new_dealer_idx + 1) % 9; bb_idx = (new_dealer_idx + 2) % 9
    players[new_dealer_idx]['role'] = 'D'
    players[sb_idx]['role'] = 'SB'; players[bb_idx]['role'] = 'BB'
    
    if players[sb_idx]['status'] == 'alive':
        pay = min(players[sb_idx]['stack'], sb_amt)
        players[sb_idx]['stack'] -= pay; players[sb_idx]['bet'] = pay; players[sb_idx]['has_acted'] = True; current_pot += pay
    if players[bb_idx]['status'] == 'alive':
        pay = min(players[bb_idx]['stack'], bb_amt)
        players[bb_idx]['stack'] -= pay; players[bb_idx]['bet'] = pay; players[bb_idx]['has_acted'] = True; current_pot += pay

    return {
        'players': players, 'pot': current_pot, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': bb_amt, 'turn_idx': (bb_idx + 1) % 9,
        'dealer_idx': new_dealer_idx, 'sb': sb_amt, 'bb': bb_amt, 'ante': ante_amt, 'level': lvl,
        'start_time': old_data['start_time'], 'msg': f"새 게임 시작! (Level {lvl})", 'turn_start_time': time.time(), 'game_over_time': 0
    }

# ==========================================
# 3. 유틸리티 (족보 계산)
# ==========================================
def r_str(r): return DISPLAY_MAP.get(r, r)
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"
def make_comm_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span comm-card-span' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"

def get_hand_strength_detail(hand):
    if not hand: return (-1, [], "No Hand")
    ranks = sorted([RANKS.index(c[0]) for c in hand], reverse=True)
    unique = sorted(list(set(ranks)), reverse=True)
    is_str = False; high_s = -1
    for i in range(len(unique)-4):
        if unique[i]-unique[i+4]==4: is_str=True; high_s=unique[i]; break
    if not is_str and set([12,3,2,1,0]).issubset(set(ranks)): is_str=True; high_s=3
    suits = [c[1] for c in hand]; is_flush = any(suits.count(s) >= 5 for s in set(suits))
    counts = {r: ranks.count(r) for r in ranks}; grp = sorted([(c, r) for r, c in counts.items()], reverse=True)
    if is_flush and is_str: return (8, ranks, "스트레이트 플러시")
    if grp[0][0]==4: return (7, ranks, "포카드")
    if grp[0][0]==3 and grp[1][0]>=2: return (6, ranks, "풀하우스")
    if is_flush: return (5, ranks, "플러시")
    if is_str: return (4, ranks, "스트레이트")
    if grp[0][0]==3: return (3, ranks, "트리플")
    if grp[0][0]==2 and grp[1][0]==2: return (2, ranks, "투페어")
    if grp[0][0]==2: return (1, ranks, "원페어")
    return (0, ranks, "하이카드")

def get_bot_decision(player, data):
    roll = random.random(); to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.15: return "Fold", 0
    if roll > 0.85: return "Raise", max(data['bb']*2, data['current_bet']*2)
    return "Call", to_call

# ==========================================
# 4. 페이즈 관리
# ==========================================
def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        winner = active[0]; winner['stack'] += data['pot']
        data['msg'] = f"🏆 {winner['name']} 승리!"; data['phase'] = 'GAME_OVER'; data['game_over_time'] = time.time(); save_data(data); return True
    
    target = data['current_bet']
    all_acted = all(p['has_acted'] for p in active)
    all_matched = all(p['bet'] == target or p['stack'] == 0 for p in active)
    
    if all_acted and all_matched:
        deck = data['deck']
        if data['phase'] == 'PREFLOP': data['phase']='FLOP'; data['community']=[deck.pop() for _ in range(3)]
        elif data['phase'] == 'FLOP': data['phase']='TURN'; data['community'].append(deck.pop())
        elif data['phase'] == 'TURN': data['phase']='RIVER'; data['community'].append(deck.pop())
        elif data['phase'] == 'RIVER':
            best_s = -1; winners = []; desc = ""
            for p in active:
                s, r, d = get_hand_strength_detail(p['hand']+data['community'])
                if s > best_s: best_s=s; winners=[p]; desc=d
                elif s == best_s: winners.append(p)
            data['msg'] = f"🏆 {', '.join([w['name'] for w in winners])} 승리! [{desc}]"
            split = data['pot'] // len(winners)
            for w in winners: w['stack'] += split
            data['pot'] = 0; data['phase'] = 'GAME_OVER'; data['game_over_time'] = time.time(); save_data(data); return True
        
        data['current_bet'] = 0
        for p in data['players']: 
            p['bet']=0; p['has_acted']=False
            if p['status']=='alive': p['action']=''
        dealer = data['dealer_idx']
        for i in range(1, 10):
            idx = (dealer + i) % 9
            if data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] > 0:
                data['turn_idx'] = idx; break
        data['turn_start_time'] = time.time(); save_data(data); return True
    return False

def pass_turn(data):
    curr = data['turn_idx']
    for i in range(1, 10):
        idx = (curr + i) % 9
        if data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] > 0:
            data['turn_idx'] = idx; break
        elif data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] == 0:
             data['players'][idx]['has_acted'] = True
    data['turn_start_time'] = time.time(); save_data(data)

# ==========================================
# 5. 입장 처리 (버튼 복구)
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트")
    u_name = st.text_input("닉네임", value="형님")
    col1, col2 = st.columns(2)
    
    if col1.button("입장하기", type="primary"):
        data = load_data(); target = -1
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name: target = i; break
        if target == -1:
            if not data['players'][4]['is_human']: target = 4
            else:
                for i in range(9):
                    if not data['players'][i]['is_human']: target = i; break
            if target != -1:
                data = load_data()
                data['players'][target] = {
                    'name': u_name, 'seat': target + 1, 'stack': 60000, 
                    'hand': [data['deck'].pop(), data['deck'].pop()], 'bet': 0,
                    'status': 'folded' if (data['phase'] != 'PREFLOP' or len(data['community']) > 0 or data['current_bet'] > 200) else 'alive',
                    'action': '관전 대기 중', 'is_human': True, 'role': data['players'][target]['role'], 
                    'has_acted': True, 'style': 'Hero', 'rebuy_count': 0
                }
                save_data(data)
        if target != -1:
            st.session_state['my_seat'] = target
            st.session_state['my_name'] = u_name
            st.rerun()
            
    if col2.button("⚠️ 서버 초기화"):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.rerun()
    st.stop()

# ==========================================
# 6. 메인 실행 & 렌더링
# ==========================================
data = load_data()
my_seat = st.session_state.get('my_seat', -1)
if my_seat != -1 and data['players'][my_seat]['name'] != st.session_state.get('my_name'):
    data['players'][my_seat]['name'] = st.session_state['my_name']
    data['players'][my_seat]['is_human'] = True
    save_data(data)

me = data['players'][my_seat]
curr_idx = data['turn_idx']; curr_p = data['players'][curr_idx]

# 자동 다음 게임
if data['phase'] == 'GAME_OVER' and time.time() - data['game_over_time'] > AUTO_NEXT_HAND_DELAY:
    save_data(reset_for_next_hand(data)); st.rerun()

# 타임아웃
time_left = max(0, TURN_TIMEOUT - (time.time() - data['turn_start_time']))
if data['phase'] != 'GAME_OVER' and time_left <= 0:
    if curr_p['status'] == 'alive':
        data = load_data(); curr_p = data['players'][curr_idx]
        curr_p['status'] = 'folded'; curr_p['action'] = "시간초과"; curr_p['has_acted'] = True
        if not check_phase_end(data): pass_turn(data)
        save_data(data); st.rerun()

# HUD
elapsed = time.time() - data['start_time']; lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
alive_p = [p for p in data['players'] if p['stack'] > 0]; avg_stack = sum(p['stack'] for p in alive_p) // len(alive_p) if alive_p else 0
st.markdown(f'<div class="top-hud"><div>LV {lvl}</div><div class="hud-time">{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>Avg: {avg_stack:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([1.5, 1])

# 테이블
with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_comm_card(c) for c in data['community']])
    for i in range(9):
        p = data['players'][i]; active = "active-turn" if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        hero = "hero-seat" if i == my_seat else ""; timer_html = f'<div class="turn-timer">⏰ {int(time_left)}s</div>' if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        if p['status'] == 'folded': cards = "<div class='fold-text'>FOLD</div>"; cls = "folded-seat"
        else:
            cls = ""
            if i == my_seat or (data['phase'] == 'GAME_OVER' and p['status'] == 'alive'):
                cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>" if p['hand'] else ""
            else: cards = "<div style='font-size:16px;'>🂠 🂠</div>"
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero} {cls}">{timer_html}{role}<div><b>{p["name"]}</b></div><div>{int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><div>{comm}</div><h3 style="margin:0;">Pot: {data["pot"]:,}</h3><p style="font-size:14px; color:#ffeb3b;">{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

# 컨트롤러
with col_controls:
    if data['phase'] == 'GAME_OVER':
        st.info(f"게임 종료! {int(AUTO_NEXT_HAND_DELAY - (time.time() - data['game_over_time']))}초 후 다음 판 시작...")
        if st.button("즉시 시작"): save_data(reset_for_next_hand(load_data())); st.rerun()
            
    elif curr_idx == my_seat and me['status'] == 'alive':
        st.success(f"내 차례! ({int(time_left)}초)"); to_call = data['current_bet'] - me['bet']
        c1, c2 = st.columns(2)
        if c1.button("체크/콜", use_container_width=True):
            data = load_data(); me = data['players'][my_seat]; pay = min(to_call, me['stack']); me['stack'] -= pay; me['bet'] += pay; data['pot'] += pay; me['has_acted'] = True; me['action'] = "콜"
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        if c2.button("폴드", type="primary", use_container_width=True):
            data = load_data(); me = data['players'][my_seat]; me['status'] = 'folded'; me['has_acted'] = True; me['action'] = "폴드"
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        if st.button("🚨 ALL-IN", use_container_width=True):
            data = load_data(); me = data['players'][my_seat]; pay = me['stack']; me['stack'] = 0; me['bet'] += pay; data['pot'] += pay; me['has_acted'] = True; me['action'] = "올인!"
            if me['bet'] > data['current_bet']: data['current_bet'] = me['bet']
            for p in data['players']:
                if p != me and p['status'] == 'alive' and p['stack'] > 0: p['has_acted'] = False
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        st.markdown("---")
        min_r = max(200, data['current_bet']*2)
        if me['stack'] > to_call:
            step_val = 1000 if sb >= 1000 else 100
            raise_val = st.number_input("레이즈 금액", min_value=int(min_r), max_value=int(me['stack'] + me['bet']), step=step_val)
            if st.button("레이즈 확정", use_container_width=True):
                data = load_data(); me = data['players'][my_seat]
                pay = raise_val - me['bet']; me['stack'] -= pay; me['bet'] = raise_val; data['pot'] += pay; data['current_bet'] = raise_val; me['has_acted'] = True; me['action'] = f"레이즈({raise_val})"
                for p in data['players']:
                    if p != me and p['status'] == 'alive' and p['stack'] > 0: p['has_acted'] = False
                if not check_phase_end(data): pass_turn(data)
                save_data(data); st.rerun()
        time.sleep(1); st.rerun()
        
    elif me['status'] == 'folded' and data['phase'] != 'GAME_OVER':
        if me['stack'] == 0 and me['rebuy_count'] < 2:
            rebuy_amt = 70000 if me['rebuy_count'] == 0 else 80000
            st.error(f"파산했습니다! (남은 리바인: {2 - me['rebuy_count']}회)")
            if st.button(f"리바인 ({rebuy_amt}칩)"):
                data = load_data(); me = data['players'][my_seat]
                me['stack'] = rebuy_amt; me['rebuy_count'] += 1; save_data(data); st.rerun()
        else:
            st.warning("관전 중... (다음 판 참여)"); time.sleep(1); st.rerun()
            
    else:
        if not curr_p['is_human']:
            time.sleep(1); data = load_data(); curr_p = data['players'][curr_idx]
            act, amt = get_bot_decision(curr_p, data); actual = min(amt, curr_p['stack'])
            curr_p['stack'] -= actual; curr_p['bet'] += actual; data['pot'] += actual
            if curr_p['bet'] > data['current_bet']:
                data['current_bet'] = curr_p['bet']
                for p in data['players']:
                    if p != curr_p and p['status'] == 'alive' and p['stack'] > 0: p['has_acted'] = False
            curr_p['action'] = f"{act}"; curr_p['has_acted'] = True
            if act == "Fold": curr_p['status'] = 'folded'
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        else:
            st.info(f"👤 {curr_p['name']} 대기 중... ({int(time_left)}s)"); time.sleep(1); st.rerun()
