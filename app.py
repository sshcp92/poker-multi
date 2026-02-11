import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 설정 & 디자인 (베이스 유지)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - FULL", page_icon="🦁")

BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 50), (300, 600, 100), (400, 800, 100),
    (500, 1000, 200), (1000, 2000, 300), (2000, 4000, 500), (5000, 10000, 1000)
]
LEVEL_DURATION = 600
TURN_TIMEOUT = 30 

RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 16px; }
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container { position:relative; width:100%; height:650px; margin:0 auto; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
.poker-table { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723); border: 20px solid #281915; border-radius: 250px; box-shadow: inset 0 0 50px rgba(0,0,0,0.8); }
.seat { position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666; border-radius:15px; color:white; text-align:center; font-size:12px; display:flex; flex-direction:column; justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; background:#3a3a3a; box-shadow:0 0 25px #ffd700; z-index: 20; transform: translateX(-50%) scale(1.1); }
.active-turn { border:4px solid #ffeb3b !important; box-shadow: 0 0 20px #ffeb3b; transform: scale(1.05); transition: 0.3s; }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:26px; color:black; border:1px solid #ccc; line-height: 1.0; display:inline-block;}
.role-badge { position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; color: black; font-weight: bold; line-height: 26px; border: 2px solid #333; z-index: 100; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.5); }
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 12px; border: 1px solid #000; z-index:100; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.5); }
.fold-text { color: #ff5252; font-weight: bold; font-size: 20px; margin-top: 30px; text-shadow: 1px 1px 2px black; }
.folded-seat { opacity: 0.5; border: 3px solid #444 !important; }
.comm-card-span { font-size: 42px !important; padding: 4px 8px !important; }
.turn-timer { position: absolute; top: -25px; width: 100%; text-align: center; color: #ff5252; font-weight: bold; font-size: 16px; text-shadow: 1px 1px 2px black; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진
# ==========================================
DATA_FILE = "poker_full_v2_timer.json"

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    bot_names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India"]
    styles = ['Tight', 'Aggressive', 'Normal', 'Tight', 'Hero', 'Normal', 'Aggressive', 'Tight', 'Normal']
    
    for i in range(9):
        players.append({
            'name': bot_names[i], 'seat': i+1, 'stack': 100000, 
            'hand': [deck.pop(), deck.pop()], 'bet': 0, 'status': 'alive', 
            'action': '', 'is_human': False, 'role': '', 'has_acted': False,
            'style': styles[i]
        })
    
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    players[1]['stack']-=100; players[1]['bet']=100; players[1]['action']='SB 100'; players[1]['has_acted']=True
    players[2]['stack']-=200; players[2]['bet']=200; players[2]['action']='BB 200'; players[2]['has_acted']=True
    
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3,
        'dealer_idx': 0, 'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 
        'start_time': time.time(), 'msg': "게임을 시작합니다!",
        'turn_start_time': time.time()
    }

def load_data():
    if not os.path.exists(DATA_FILE): d = init_game_data(); save_data(d); return d
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except:
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        d = init_game_data(); save_data(d); return d

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f: json.dump(data, f)

# ==========================================
# 3. 족보 계산 & 유틸리티
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
    suits = [c[1] for c in hand]
    is_flush = any(suits.count(s) >= 5 for s in set(suits))
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False; high_s = -1
    for i in range(len(unique_ranks) - 4):
        if unique_ranks[i] - unique_ranks[i+4] == 4: is_straight = True; high_s = unique_ranks[i]; break
    if not is_straight and set([12, 3, 2, 1, 0]).issubset(set(ranks)): is_straight = True; high_s = 3
    counts = {r: ranks.count(r) for r in ranks}
    sorted_groups = sorted([(c, r) for r, c in counts.items()], reverse=True)
    if is_flush and is_straight: return (8, ranks, "스트레이트 플러시")
    if sorted_groups[0][0] == 4: return (7, ranks, f"포카드 ({r_str(RANKS[sorted_groups[0][1]])})")
    if sorted_groups[0][0] == 3 and sorted_groups[1][0] >= 2: return (6, ranks, f"풀하우스 ({r_str(RANKS[sorted_groups[0][1]])})")
    if is_flush: return (5, ranks, "플러시")
    if is_straight: return (4, ranks, "스트레이트")
    if sorted_groups[0][0] == 3: return (3, ranks, f"트리플 ({r_str(RANKS[sorted_groups[0][1]])})")
    if sorted_groups[0][0] == 2 and sorted_groups[1][0] == 2: return (2, ranks, f"투페어 ({r_str(RANKS[sorted_groups[0][1]])} & {r_str(RANKS[sorted_groups[1][1]])})")
    if sorted_groups[0][0] == 2: return (1, ranks, f"원페어 ({r_str(RANKS[sorted_groups[0][1]])})")
    return (0, ranks, f"하이카드 ({r_str(RANKS[sorted_groups[0][1]])})")

def get_bot_decision(player, data):
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    fold_thresh = 0.2 if player['style'] == 'Tight' else 0.1
    if roll < fold_thresh: return "Fold", 0
    raise_thresh = 0.7 if player['style'] == 'Aggressive' else 0.85
    if roll > raise_thresh:
        raise_amt = max(data['bb']*2, data['current_bet']*2)
        return "Raise", raise_amt
    return "Call", to_call

# ==========================================
# 4. 페이즈 관리
# ==========================================
def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        winner = active[0]; winner['stack'] += data['pot']
        data['msg'] = f"🏆 {winner['name']} 승리! (All Fold)"
        data['phase'] = 'GAME_OVER'; save_data(data); return True

    bet_target = data['current_bet']
    all_acted = all(p['has_acted'] for p in active)
    all_matched = all(p['bet'] == bet_target or p['stack'] == 0 for p in active)
    
    if all_acted and all_matched:
        deck = data['deck']
        next_p = False
        if data['phase'] == 'PREFLOP': data['phase']='FLOP'; data['community']=[deck.pop() for _ in range(3)]; next_p=True
        elif data['phase'] == 'FLOP': data['phase']='TURN'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'TURN': data['phase']='RIVER'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'RIVER':
            best_s = -1; winners = []; desc = ""
            for p in active:
                s, r, d = get_hand_strength_detail(p['hand']+data['community'])
                if s > best_s: best_s=s; winners=[p]; desc=d
                elif s == best_s: winners.append(p)
            names = ", ".join([w['name'] for w in winners]); data['msg'] = f"🏆 {names} 승리! [{desc}]"
            split = data['pot'] // len(winners)
            for w in winners: w['stack'] += split
            data['pot'] = 0; data['phase'] = 'GAME_OVER'; save_data(data); return True
            
        if next_p:
            data['current_bet'] = 0
            for p in data['players']:
                p['bet']=0; p['has_acted']=False
                if p['status']=='alive': p['action']=''
            dealer = data['dealer_idx']
            for i in range(1, 10):
                idx = (dealer + i) % 9
                if data['players'][idx]['status'] == 'alive': data['turn_idx'] = idx; break
            data['msg'] = f"{data['phase']} 시작!"; data['turn_start_time'] = time.time(); save_data(data); return True
    return False

def pass_turn(data):
    curr = data['turn_idx']
    for i in range(1, 10):
        idx = (curr + i) % 9
        if data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] > 0:
            data['turn_idx'] = idx; break
    data['turn_start_time'] = time.time()
    save_data(data)

# ==========================================
# 5. 입장 처리
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 (Full Version)")
    u_name = st.text_input("닉네임", value="형님")
    col1, col2 = st.columns(2)
    if col1.button("입장하기", type="primary"):
        data = load_data()
        target = -1
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name: target = i; break
        if target == -1:
            target = 4
            if data['players'][4]['is_human']:
                for i in range(9): 
                    if not data['players'][i]['is_human']: target = i; break
            data['players'][target]['name'] = u_name; data['players'][target]['is_human'] = True; data['players'][target]['status'] = 'alive'
            save_data(data)
        st.session_state['my_seat'] = target
        st.rerun()
    if col2.button("서버 초기화 (오류 시 클릭)"):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.rerun()
    st.stop()

# ==========================================
# 6. 메인 실행 & 렌더링
# ==========================================
data = load_data()
if st.session_state['my_seat'] >= len(data['players']): del st.session_state['my_seat']; st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

time_left = max(0, TURN_TIMEOUT - (time.time() - data['turn_start_time']))

if data['phase'] != 'GAME_OVER' and time_left <= 0:
    curr_p['status'] = 'folded'; curr_p['action'] = "시간초과 폴드"; curr_p['has_acted'] = True
    if not check_phase_end(data): pass_turn(data)
    save_data(data); st.rerun()

# --- 화면 그리기 ---
elapsed = time.time() - data['start_time']
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"
alive_players = [p for p in data['players'] if p['stack'] > 0]
avg_stack = sum(p['stack'] for p in alive_players) // len(alive_players) if alive_players else 0

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">{timer_str}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>평균 스택 (Avg Stack) : {avg_stack:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_comm_card(c) for c in data['community']])
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        hero = "hero-seat" if i == my_seat else ""
        timer_html = f'<div class="turn-timer">⏰ {int(time_left)}초</div>' if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        if p['status'] == 'folded': cards = "<div class='fold-text'>FOLD</div>"; cls="folded-seat"
        else:
            cls=""
            if i == my_seat or (data['phase'] == 'GAME_OVER' and p['status'] == 'alive'):
                if p['hand']: cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
                else: cards = ""
            else: cards = "<div style='font-size:24px; margin-top:10px;'>🂠 🂠</div>"
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero} {cls}">{timer_html}{role}<div>{p["name"]}</div><div>{int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    html += f'<div style="position:absolute; top:48%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><div style="margin-bottom:15px;">{comm}</div><h2 style="margin:0;">Pot: {data["pot"]:,}</h2><p style="font-size:18px; color:#ffeb3b; font-weight:bold; margin-top:5px;">{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    st.markdown("### Control")
    if data['phase'] == 'GAME_OVER':
        if st.button("다음 게임 시작", type="primary"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()

    elif curr_idx == my_seat:
        st.success(f"형님 차례! (남은 시간: {int(time_left)}초)")
        to_call = data['current_bet'] - me['bet']
        if st.button("체크" if to_call == 0 else f"콜 ({to_call:,})", use_container_width=True):
            pay = min(to_call, me['stack']); me['stack'] -= pay; me['bet'] += pay; data['pot'] += pay
            me['action'] = "체크" if pay == 0 else f"콜 ({pay})"; me['has_acted'] = True
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        if st.button("폴드", type="primary", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "폴드"; me['has_acted'] = True
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        st.markdown("---")
        min_r = max(200, data['current_bet']*2)
        if me['stack'] > min_r:
            val = st.slider("레이즈 금액", int(min_r), int(me['stack']), int(min_r))
            if st.button("레이즈 확정", use_container_width=True):
                pay = val - me['bet']; me['stack'] -= pay; me['bet'] = val; data['pot'] += pay
                data['current_bet'] = val; me['action'] = f"레이즈 ({val})"; me['has_acted'] = True
                for p in data['players']:
                    if p != me and p['status']=='alive' and p['stack']>0: p['has_acted']=False
                if not check_phase_end(data): pass_turn(data)
                save_data(data); st.rerun()
        if st.button("올인 (All-in)", use_container_width=True):
            amt = me['stack']; me['stack'] = 0; me['bet'] += amt; data['pot'] += amt
            if me['bet'] > data['current_bet']:
                data['current_bet'] = me['bet']
                for p in data['players']:
                    if p != me and p['status']=='alive': p['has_acted']=False
            me['action'] = "올인"; me['has_acted'] = True
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        time.sleep(1); st.rerun()
    else:
        if not curr_p['is_human']:
            time.sleep(1)
            act, amt = get_bot_decision(curr_p, data)
            actual = min(amt, curr_p['stack']); curr_p['stack'] -= actual; curr_p['bet'] += actual; data['pot'] += actual
            if curr_p['bet'] > data['current_bet']:
                data['current_bet'] = curr_p['bet']
                for p in data['players']:
                    if p != curr_p and p['status']=='alive' and p['stack']>0: p['has_acted']=False
            act_str = f"{act} ({curr_p['bet']})" if act != "Fold" else "폴드"
            if act == "Call" and actual == 0: act_str = "체크"
            if act == "Fold": curr_p['status'] = 'folded'
            curr_p['action'] = act_str; curr_p['has_acted'] = True
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
        else:
            st.info(f"👤 {curr_p['name']} 님의 턴입니다. (남은 시간: {int(time_left)}초)")
            time.sleep(1); st.rerun()
