import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 디자인 (형님 원판 100%)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800)
]
LEVEL_DURATION = 600
RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

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
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000; z-index:100; white-space: nowrap;}
.fold-text { color: #ff5252; font-weight: bold; font-size: 18px; margin-top: 20px; }
.folded-seat { opacity: 0.4; border: 3px solid #333 !important; }
.log-box { position: absolute; top: 60%; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); padding: 5px 15px; border-radius: 20px; color: #fff; font-size: 14px; pointer-events: none; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진
# ==========================================
DATA_FILE = "poker_v14_seq_fix.json"

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
    players[1]['stack'] -= 100; players[1]['bet'] = 100; players[1]['action'] = 'SB 100'; players[1]['has_acted'] = True
    players[2]['stack'] -= 200; players[2]['bet'] = 200; players[2]['action'] = 'BB 200'; players[2]['has_acted'] = True
    
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3,
        'dealer_idx': 0, 'sb': 100, 'bb': 200, 'start_time': time.time(),
        'msg': "게임 시작! UTG 턴입니다.", 'last_log': ""
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
# 3. 유틸리티 & 봇 지능
# ==========================================
def r_str(r): return DISPLAY_MAP.get(r, r)
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"

def get_hand_strength_detail(hand):
    # (형님 원판 족보 로직 유지)
    if not hand: return (-1, "No Hand")
    ranks = sorted([RANKS.index(c[0]) for c in hand], reverse=True)
    suits = [c[1] for c in hand]
    is_flush = any(suits.count(s) >= 5 for s in set(suits))
    unique = sorted(list(set(ranks)), reverse=True)
    is_str = False
    for i in range(len(unique)-4):
        if unique[i]-unique[i+4]==4: is_str=True; break
    if not is_str and set([12,3,2,1,0]).issubset(set(ranks)): is_str=True
    counts = {r: ranks.count(r) for r in ranks}
    grp = sorted([(c, r) for r, c in counts.items()], reverse=True)
    
    if is_flush and is_str: return (8, "스트레이트 플러시")
    if grp[0][0]==4: return (7, "포카드")
    if grp[0][0]==3 and grp[1][0]>=2: return (6, "풀하우스")
    if is_flush: return (5, "플러시")
    if is_str: return (4, "스트레이트")
    if grp[0][0]==3: return (3, "트리플")
    if grp[0][0]==2 and grp[1][0]==2: return (2, "투페어")
    if grp[0][0]==2: return (1, "원페어")
    return (0, "하이카드")

def get_bot_decision(p, data):
    roll = random.random()
    to_call = data['current_bet'] - p['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.1: return "Fold", 0
    if roll < 0.2: return "Raise", max(data['bb']*2, data['current_bet']*2)
    return "Call", to_call

# ==========================================
# 4. [핵심] 페이즈 및 턴 관리
# ==========================================
def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        data['phase'] = 'GAME_OVER'; data['msg'] = f"🏆 {active[0]['name']} 승리!"; save_data(data); return True

    target = data['current_bet']
    all_acted = all(p['has_acted'] for p in active)
    all_matched = all(p['bet'] == target or p['stack'] == 0 for p in active)
    
    if all_acted and all_matched:
        deck = data['deck']
        next_p = False
        if data['phase'] == 'PREFLOP':
            data['phase']='FLOP'; data['community']=[deck.pop() for _ in range(3)]; next_p=True
        elif data['phase'] == 'FLOP':
            data['phase']='TURN'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'TURN':
            data['phase']='RIVER'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'RIVER':
            # 쇼다운
            best_s = -1; winners = []; desc = ""
            for p in active:
                s, d = get_hand_strength_detail(p['hand']+data['community'])
                if s > best_s: best_s=s; winners=[p]; desc=d
                elif s == best_s: winners.append(p)
            names = ",".join([w['name'] for w in winners])
            data['msg'] = f"🏆 {names} 승리! ({desc})"
            split = data['pot'] // len(winners)
            for w in winners: w['stack'] += split
            data['pot'] = 0; data['phase'] = 'GAME_OVER'; save_data(data); return True

        if next_p:
            data['current_bet'] = 0
            for p in data['players']:
                p['bet']=0; p['has_acted']=False; 
                if p['status']=='alive': p['action']=''
            
            # 포스트플랍은 SB(Dealer+1)부터 시작
            dealer = data['dealer_idx']
            for i in range(1, 10):
                idx = (dealer + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            data['msg'] = f"{data['phase']} 시작!"; save_data(data); return True
    return False

def pass_turn(data):
    # 다음 사람 찾기
    curr = data['turn_idx']
    for i in range(1, 10):
        idx = (curr + i) % 9
        if data['players'][idx]['status'] == 'alive' and data['players'][idx]['stack'] > 0:
            data['turn_idx'] = idx; break
    save_data(data)

# ==========================================
# 5. 입장 화면
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - 순차 액션")
    u_name = st.text_input("닉네임", value="형님")
    if st.button("입장하기", type="primary"):
        data = load_data()
        target = -1
        # 재접속 or 빈자리 찾기
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name: target = i; break
        if target == -1:
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
    if st.button("서버 초기화"):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.rerun()
    st.stop()

# ==========================================
# 6. 메인 로직 (단일 행동 -> 리런)
# ==========================================
data = load_data()
if st.session_state['my_seat'] >= len(data['players']): del st.session_state['my_seat']; st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# ---------------------------------------------------------
# 🤖 봇 행동 처리 (내 턴이 아니고, 게임 중일 때)
# ---------------------------------------------------------
if curr_idx != my_seat and data['phase'] != 'GAME_OVER':
    if not curr_p['is_human']:
        # 1. 일단 화면을 먼저 보여줌 (봇이 고민하는 척)
        # 2. 1초 대기
        time.sleep(1) 
        
        # 3. 행동 계산
        act, amt = get_bot_decision(curr_p, data)
        actual = min(amt, curr_p['stack'])
        
        # 4. 상태 반영
        curr_p['stack'] -= actual; curr_p['bet'] += actual
        data['pot'] += actual
        
        # 레이즈 처리
        if curr_p['bet'] > data['current_bet']:
            data['current_bet'] = curr_p['bet']
            for p in data['players']: # 전원 has_acted 리셋
                if p != curr_p and p['status'] == 'alive' and p['stack'] > 0: p['has_acted'] = False
        
        # 로그 및 액션
        act_str = f"{act} {curr_p['bet']}" if act != "Fold" else "Fold"
        if act == "Fold": curr_p['status'] = 'folded'
        curr_p['action'] = act_str
        curr_p['has_acted'] = True
        data['last_log'] = f"📢 {curr_p['name']}: {act_str}"
        
        # 5. 페이즈 체크 OR 턴 넘기기
        if not check_phase_end(data):
            pass_turn(data)
            
        save_data(data)
        st.rerun() # [핵심] 봇 1명 행동 끝나면 무조건 리런!
    else:
        # 친구 턴이면 2초마다 갱신
        time.sleep(2); st.rerun()

# ==========================================
# 7. 화면 그리기
# ==========================================
st.markdown(f'<div class="top-hud"><div>LEVEL 1</div><div class="hud-time">Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_card(c) for c in data['community']])
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        hero = "hero-seat" if i == my_seat else ""
        
        # 카드 표시
        if p['status'] == 'folded': cards = "<div class='fold-text'>FOLD</div>"; cls="folded-seat"
        else:
            cls=""
            if i == my_seat or (data['phase'] == 'GAME_OVER' and p['status'] == 'alive'):
                if p['hand']: cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
                else: cards = ""
            else: cards = "<div style='font-size:20px'>🂠 🂠</div>"
            
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero} {cls}">{role}<div>{p["name"]}</div><div>{int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    
    html += f'<div style="position:absolute; top:55%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><div class="log-box">{data.get("last_log","")}</div><h2>{comm}</h2><p>{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

with col2:
    st.markdown("### Control")
    if curr_idx == my_seat and data['phase'] != 'GAME_OVER':
        st.success("내 차례!")
        to_call = data['current_bet'] - me['bet']
        
        if st.button("Check/Call", use_container_width=True):
            pay = min(to_call, me['stack'])
            me['stack'] -= pay; me['bet'] += pay; data['pot'] += pay
            me['action'] = "Check" if pay == 0 else "Call"
            me['has_acted'] = True
            data['last_log'] = f"📢 {me['name']}: {me['action']}"
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
            
        if st.button("Fold", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "Fold"; me['has_acted'] = True
            data['last_log'] = f"📢 {me['name']}: Fold"
            if not check_phase_end(data): pass_turn(data)
            save_data(data); st.rerun()
            
        min_r = max(200, data['current_bet']*2)
        if me['stack'] > min_r:
            val = st.slider("Raise", int(min_r), int(me['stack']), int(min_r))
            if st.button("Raise Confirm", use_container_width=True):
                pay = val - me['bet']
                me['stack'] -= pay; me['bet'] = val; data['pot'] += pay
                data['current_bet'] = val; me['action'] = f"Raise {val}"; me['has_acted'] = True
                data['last_log'] = f"📢 {me['name']}: Raise {val}"
                for p in data['players']:
                    if p != me and p['status']=='alive' and p['stack']>0: p['has_acted']=False
                if not check_phase_end(data): pass_turn(data)
                save_data(data); st.rerun()
                
    elif data['phase'] == 'GAME_OVER':
        if st.button("Next Hand", type="primary"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
    else:
        st.info(f"{curr_p['name']} 턴...")
