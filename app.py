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
    (100, 200, 0), 
    (200, 400, 0), 
    (300, 600, 600), 
    (400, 800, 800),
    (500, 1000, 1000), 
    (1000, 2000, 2000), 
    (2000, 4000, 4000), 
    (5000, 10000, 10000)
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
/* [수정1] D/SB 표시를 위한 스타일 */
.role-badge { position: absolute; top: -8px; left: -8px; min-width: 24px; height: 24px; padding: 0 4px; border-radius: 12px; color: black; font-weight: bold; line-height: 22px; border: 1px solid #333; z-index: 100; font-size: 11px; background:white;}
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.role-D-SB { background: linear-gradient(135deg, #ffeb3b 50%, #90caf9 50%); font-size: 10px; } /* 헤즈업용 */

.action-badge { position: absolute; bottom: -12px; background:#ffeb3b; color:black; font-weight:bold; padding:1px 5px; border-radius:4px; font-size: 10px; border: 1px solid #000; z-index:100; white-space: nowrap; }
.fold-text { color: #ff5252; font-weight: bold; font-size: 14px; }
.folded-seat { opacity: 0.4; }
.turn-timer { position: absolute; top: -20px; width: 100%; text-align: center; color: #ff5252; font-weight: bold; font-size: 12px; }
.stButton>button { font-size: 14px !important; height: 40px !important; }
div[data-baseweb="input"] { background-color: #333; color: white; border: 1px solid #555; }
div[data-baseweb="input"] input { text-align: center; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진
# ==========================================
DATA_FILE = "poker_final_v10.json"

def init_game_data():
    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    players = []
    for i in range(9):
        players.append({
            'name': "빈 자리", 'seat': i+1, 'stack': 0, 
            'hand': [], 'bet': 0, 'status': 'standby', 
            'action': '', 'is_human': False, 'role': '', 'has_acted': False, 'style': 'None',
            'rebuy_count': 0
        })
    return {
        'players': players, 'pot': 0, 'deck': deck, 'community': [],
        'phase': 'WAITING', 'current_bet': 0, 'turn_idx': 0,
        'dealer_idx': 0, 'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 
        'start_time': time.time(), 'msg': "플레이어를 기다리는 중...", 'turn_start_time': time.time(), 'game_over_time': 0
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
    players = old_data['players']
    active_indices = [i for i, p in enumerate(players) if p['name'] != "빈 자리" and p['stack'] > 0]
    
    if len(active_indices) < 2: return init_game_data()

    deck = [r+s for r in RANKS for s in SUITS]; random.shuffle(deck)
    
    # 딜러 이동
    current_d = old_data['dealer_idx']
    for i in range(1, 10):
        next_d = (current_d + i) % 9
        if players[next_d]['name'] != "빈 자리" and players[next_d]['stack'] > 0:
            new_dealer_idx = next_d; break
    
    elapsed = time.time() - old_data['start_time']
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl-1]
    
    current_pot = 0
    for i, p in enumerate(players):
        if p['name'] != "빈 자리" and p['stack'] > 0:
            p['status'] = 'alive'; p['hand'] = [deck.pop(), deck.pop()]
            if ante_amt > 0:
                actual_ante = min(p['stack'], ante_amt)
                p['stack'] -= actual_ante; current_pot += actual_ante
        else:
            p['status'] = 'standby' if p['stack'] == 0 and p['name'] != "빈 자리" else 'folded'
            p['hand'] = []
        p['bet'] = 0; p['action'] = ''; p['has_acted'] = False; p['role'] = ''

    # [수정1] 헤즈업(1:1) vs 다인전 롤 분배
    def find_next_active(idx):
        for i in range(1, 10):
            next_i = (idx + i) % 9
            if players[next_i]['status'] == 'alive': return next_i
        return idx

    if len(active_indices) == 2:
        # 헤즈업: 딜러가 SB, 상대방이 BB
        sb_idx = new_dealer_idx
        bb_idx = find_next_active(sb_idx)
        players[sb_idx]['role'] = 'D-SB' # 딜러이자 스몰
        players[bb_idx]['role'] = 'BB'
        # 헤즈업은 프리플랍에서 SB(딜러)가 먼저 함
        turn_start_idx = sb_idx 
    else:
        # 3명 이상: 딜러 다음이 SB
        sb_idx = find_next_active(new_dealer_idx)
        bb_idx = find_next_active(sb_idx)
        players[new_dealer_idx]['role'] = 'D'
        players[sb_idx]['role'] = 'SB'
        players[bb_idx]['role'] = 'BB'
        # 다인전은 프리플랍에서 BB 다음(UTG)이 먼저 함
        turn_start_idx = find_next_active(bb_idx)

    # 블라인드 베팅
    if players[sb_idx]['status'] == 'alive':
        pay = min(players[sb_idx]['stack'], sb_amt)
        players[sb_idx]['stack'] -= pay; players[sb_idx]['bet'] = pay; players[sb_idx]['has_acted'] = True; current_pot += pay
    if players[bb_idx]['status'] == 'alive':
        pay = min(players[bb_idx]['stack'], bb_amt)
        players[bb_idx]['stack'] -= pay; players[bb_idx]['bet'] = pay; players[bb_idx]['has_acted'] = True; current_pot += pay

    return {
        'players': players, 'pot': current_pot, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': bb_amt, 'turn_idx': turn_start_idx,
        'dealer_idx': new_dealer_idx, 'sb': sb_amt, 'bb': bb_amt, 'ante': ante_amt, 'level': lvl,
        'start_time': old_data['start_time'], 'msg': f"Level {lvl} 시작! (SB {sb_amt}/BB {bb_amt})", 
        'turn_start_time': time.time(), 'game_over_time': 0
    }

# ==========================================
# 3. 유틸리티 (족보 디테일 강화)
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
    
    # [수정2] 족보 텍스트에 키커 정보 추가
    def rank_name(idx): return r_str(RANKS[idx])
    
    if is_flush and is_str: return (8, ranks, f"스트레이트 플러시 ({rank_name(high_s)})")
    if grp[0][0]==4: return (7, ranks, f"포카드 ({rank_name(grp[0][1])})")
    if grp[0][0]==3 and grp[1][0]>=2: return (6, ranks, f"풀하우스 ({rank_name(grp[0][1])})")
    if is_flush: return (5, ranks, f"플러시 ({rank_name(ranks[0])})")
    if is_str: return (4, ranks, f"스트레이트 ({rank_name(high_s)})")
    if grp[0][0]==3: return (3, ranks, f"트리플 ({rank_name(grp[0][1])})")
    if grp[0][0]==2 and grp[1][0]==2: return (2, ranks, f"투페어 ({rank_name(grp[0][1])}, {rank_name(grp[1][1])})")
    if grp[0][0]==2: 
        # 원페어 + 키커
        kicker = [r for r in ranks if r != grp[0][1]][0]
        return (1, ranks, f"원페어 ({rank_name(grp[0][1])}) - 킥 {rank_name(kicker)}")
    # 하이카드 + 차상위 키커
    return (0, ranks, f"하이카드 ({rank_name(ranks[0])}, {rank_name(ranks[1])})")

def get_bot_decision(player, data):
    return "Check", 0 

# ==========================================
# 4. 페이즈 관리
# ==========================================
def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        if len(active) == 1:
            winner = active[0]; winner['stack'] += data['pot']
            data['msg'] = f"🏆 {winner['name']} 승리!"; 
        data['phase'] = 'GAME_OVER'; data['game_over_time'] = time.time(); save_data(data); return True
    
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
        found = False
        for i in range(1, 10):
            idx = (dealer + i) % 9
            if data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] > 0:
                data['turn_idx'] = idx; found = True; break
        if not found: 
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
        elif data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] == 0:
             data['players'][idx]['has_acted'] = True
    data['turn_start_time'] = time.time(); save_data(data)

# ==========================================
# 5. 입장 처리
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
            if data['players'][4]['name'] == "빈 자리": target = 4
            else:
                for i in range(9):
                    if data['players'][i]['name'] == "빈 자리": target = i; break
            if target != -1:
                data = load_data()
                data['players'][target] = {
                    'name': u_name, 'seat': target + 1, 'stack': 60000, 
                    'hand': [], 'bet': 0,
                    'status': 'folded', 'action': '관전 대기 중', 'is_human': True, 
                    'role': '', 'has_acted': True, 'style': 'Hero', 'rebuy_count': 0
                }
                active_count = len([p for p in data['players'] if p['stack'] > 0 and p['name'] != "빈 자리"])
                if data['phase'] == 'WAITING' and active_count >= 2:
                    data = reset_for_next_hand(data)
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
# 6. 메인 로직
# ==========================================
data = load_data()
my_seat = st.session_state.get('my_seat', -1)
if my_seat != -1 and data['players'][my_seat]['name'] != st.session_state.get('my_name'):
    data['players'][my_seat]['name'] = st.session_state['my_name']
    data['players'][my_seat]['is_human'] = True
    save_data(data)

me = data['players'][my_seat]
curr_idx = data['turn_idx']; curr_p = data['players'][curr_idx]

if data['phase'] == 'WAITING':
    st.info("✋ 다른 플레이어 입장을 대기 중입니다... (최소 2명)")
    if st.button("새로고침"): st.rerun()
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    for i in range(9):
        p = data['players'][i]; txt = p['name'] if p['name'] != "빈 자리" else "빈 자리"
        style = "border:3px solid #ffd700;" if p['name'] != "빈 자리" else "opacity:0.3;"
        html += f'<div class="seat pos-{i}" style="{style}"><div>{txt}</div></div>'
    st.markdown(html + '</div>', unsafe_allow_html=True)
    time.sleep(2); st.rerun(); st.stop()

# [수정3] 자동 다음 게임 (타이머 작동)
if data['phase'] == 'GAME_OVER':
    remaining = AUTO_NEXT_HAND_DELAY - (time.time() - data['game_over_time'])
    if remaining <= 0:
        save_data(reset_for_next_hand(data)); st.rerun()

time_left = max(0, TURN_TIMEOUT - (time.time() - data['turn_start_time']))
if data['phase'] != 'GAME_OVER' and time_left <= 0:
    if curr_p['status'] == 'alive':
        data = load_data(); curr_p = data['players'][curr_idx]
        curr_p['status'] = 'folded'; curr_p['action'] = "시간초과"; curr_p['has_acted'] = True
        if not check_phase_end(data): pass_turn(data)
        save_data(data); st.rerun()

elapsed = time.time() - data['start_time']; lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
alive_p = [p for p in data['players'] if p['stack'] > 0 and p['name'] != "빈 자리"]; avg_stack = sum(p['stack'] for p in alive_p) // len(alive_p) if alive_p else 0
st.markdown(f'<div class="top-hud"><div>LV {lvl}</div><div class="hud-time">{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>Avg: {avg_stack:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([1.5, 1])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_comm_card(c) for c in data['community']])
    for i in range(9):
        p = data['players'][i]; active = "active-turn" if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        hero = "hero-seat" if i == my_seat else ""; timer_html = f'<div class="turn-timer">⏰ {int(time_left)}s</div>' if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        if p['name'] == "빈 자리": html += f'<div class="seat pos-{i}" style="opacity:0.2;"><div>빈 자리</div></div>'; continue
        
        cards = "<div style='font-size:16px;'>🂠 🂠</div>"
        if p['status'] == 'folded': cards = "<div class='fold-text'>FOLD</div>"; cls = "folded-seat"
        else:
            cls = ""
            if i == my_seat or (data['phase'] == 'GAME_OVER' and p['status'] == 'alive'):
                cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>" if p['hand'] else ""
        
        # [수정1] 롤 배지 표시
        role = p['role']
        role_cls = "role-D-SB" if role == "D-SB" else f"role-{role}"
        role_div = f"<div class='role-badge {role_cls}'>{role}</div>" if role else ""
        
        html += f'<div class="seat pos-{i} {active} {hero} {cls}">{timer_html}{role_div}<div><b>{p["name"]}</b></div><div>{int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><div>{comm}</div><h3 style="margin:0;">Pot: {data["pot"]:,}</h3><p style="font-size:14px; color:#ffeb3b;">{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    if data['phase'] == 'GAME_OVER':
        # [수정3] 카운트다운 표시 및 자동 리런
        rem = int(AUTO_NEXT_HAND_DELAY - (time.time() - data['game_over_time']))
        st.info(f"게임 종료! {rem}초 후 다음 판 시작...")
        time.sleep(1); st.rerun()
        
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
            st.error(f"파산! 리바인 가능 ({2 - me['rebuy_count']}회 남음)")
            if st.button(f"리바인 ({rebuy_amt}칩)"):
                data = load_data(); me = data['players'][my_seat]
                me['stack'] = rebuy_amt; me['rebuy_count'] += 1; save_data(data); st.rerun()
        else:
            st.warning("관전 중... (다음 판 참여)"); time.sleep(1); st.rerun()
    else:
        st.info(f"👤 {curr_p['name']} 대기 중... ({int(time_left)}s)"); time.sleep(1); st.rerun()
