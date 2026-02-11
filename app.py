import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 설정 및 디자인 (형님 원판 100% 고정)
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

BLIND_STRUCTURE = [(100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800)]
RANKS = '23456789TJQKA'
SUITS = ['♠', '♥', '♦', '♣']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud { display: flex; justify-content: space-around; align-items: center; background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #555; color: white; font-weight: bold; font-size: 16px; }
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container { position:relative; width:100%; height:650px; margin:0 auto; background-color:#1e1e1e; border-radius:30px; border:4px solid #333; overflow: hidden; }
.poker-table { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); width: 90%; height: 460px; background: radial-gradient(#5d4037, #3e2723); border: 20px solid #281915; border-radius: 250px; box-shadow: inset 0 0 50px rgba(0,0,0,0.8); }
.seat { position:absolute; width:140px; height:160px; background:#2c2c2c; border:3px solid #666; border-radius:15px; color:white; text-align:center; font-size:12px; display:flex; flex-direction:column; justify-content:flex-start; padding-top: 10px; align-items:center; z-index:10; transition: all 0.3s; }
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; background:#3a3a3a; box-shadow:0 0 25px #ffd700; z-index: 20; transform: translateX(-50%) scale(1.1); }
.active-turn { border:4px solid #ffeb3b !important; box-shadow: 0 0 20px #ffeb3b; transform: scale(1.05); }
.card-span {background:white; padding:2px 6px; border-radius:4px; margin:1px; font-weight:bold; font-size:26px; color:black; border:1px solid #ccc; line-height: 1.0;}
.role-badge { position: absolute; top: -10px; left: -10px; width: 30px; height: 30px; border-radius: 50%; color: black; font-weight: bold; line-height: 26px; border: 2px solid #333; z-index: 100; font-size: 14px; }
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000; z-index:100; white-space: nowrap;}
.fold-text { color: #ff5252; font-weight: bold; font-size: 18px; margin-top: 20px; }
.folded-seat { opacity: 0.4; border: 3px solid #333 !important; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진 (v16_slow)
# ==========================================
DATA_FILE = "poker_v16_slow.json"

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
    players[1]['stack']-=100; players[1]['bet']=100; players[1]['action']='SB 100'; players[1]['has_acted']=True
    players[2]['stack']-=200; players[2]['bet']=200; players[2]['action']='BB 200'; players[2]['has_acted']=True
    
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 'turn_idx': 3, 
        'dealer_idx': 0, 'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 
        'msg': "게임을 시작합니다!", 'last_act_time': time.time()
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
# 3. 유틸리티
# ==========================================
def r_str(r): return DISPLAY_MAP.get(r, r)
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"

def get_bot_decision(player, data):
    # 봇은 단순하게 Call 위주, 가끔 Raise
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.1: return "Fold", 0
    if roll < 0.2: return "Raise", max(data['bb']*2, data['current_bet']*2)
    return "Call", to_call

# ==========================================
# 4. 페이즈 및 턴 관리 (순차 보장 핵심)
# ==========================================
def next_turn(data):
    # 다음 살아있는 사람 찾기 (무조건 +1)
    curr = data['turn_idx']
    found_next = False
    for i in range(1, 10):
        idx = (curr + i) % 9
        if data['players'][idx]['status'] == 'alive':
            data['turn_idx'] = idx; found_next = True; break
    
    if not found_next: return # 혼자 남음 (승리 처리 로직에서 걸러짐)

    # 페이즈 종료 조건 체크
    active = [p for p in data['players'] if p['status'] == 'alive']
    bet_target = data['current_bet']
    all_acted = all(p['has_acted'] for p in active)
    all_matched = all(p['bet'] == bet_target or p['stack'] == 0 for p in active)
    
    if all_acted and all_matched:
        # 페이즈 전환
        deck = data['deck']
        next_p = False
        if data['phase'] == 'PREFLOP':
            data['phase']='FLOP'; data['community']=[deck.pop() for _ in range(3)]; next_p=True
        elif data['phase'] == 'FLOP':
            data['phase']='TURN'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'TURN':
            data['phase']='RIVER'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'RIVER':
            data['phase']='GAME_OVER'; data['msg']="쇼다운 결과 확인"; save_data(data); return

        if next_p:
            data['current_bet'] = 0
            for p in data['players']:
                p['bet']=0; p['has_acted']=False; 
                if p['status']=='alive': p['action']=''
            
            # 다음 페이즈 턴은 Dealer 다음부터
            dealer = data['dealer_idx']
            for i in range(1, 10):
                idx = (dealer + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            data['msg'] = f"{data['phase']} 시작!"
            save_data(data)

# ==========================================
# 5. 입장 및 초기화
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - SLOW")
    u_name = st.text_input("닉네임", value="형님")
    col1, col2 = st.columns(2)
    if col1.button("입장하기", type="primary"):
        data = load_data()
        target = 4
        if data['players'][4]['is_human']: # 4번 차있으면 빈자리
            for i in range(9): 
                if not data['players'][i]['is_human']: target = i; break
        data['players'][target]['name'] = u_name
        data['players'][target]['is_human'] = True
        data['players'][target]['status'] = 'alive'
        save_data(data); st.session_state['my_seat'] = target; st.rerun()
    if col2.button("서버 초기화"):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.rerun()
    st.stop()

# ==========================================
# 6. 메인 로직 (여기서 화면 그리고 -> 대기 -> 봇 행동 -> 리런)
# ==========================================
data = load_data()
if st.session_state['my_seat'] >= len(data['players']): del st.session_state['my_seat']; st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# --- [화면 렌더링 먼저] ---
st.markdown(f'<div class="top-hud"><div>{data["phase"]}</div><div class="hud-time">Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_card(c) for c in data['community']])
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == curr_idx and data['phase'] != 'GAME_OVER' else ""
        hero = "hero-seat" if i == my_seat else ""
        
        # 폴드 & 핸드 표시
        if p['status'] == 'folded': cards = "<div class='fold-text'>FOLD</div>"; cls="folded-seat"
        else:
            cls=""
            if i == my_seat or (data['phase'] == 'GAME_OVER' and p['status'] == 'alive'):
                if p['hand']: cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
                else: cards = ""
            else: cards = "<div style='font-size:20px'>🂠 🂠</div>"
            
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero} {cls}">{role}<div>{p["name"]}</div><div>{int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    
    html += f'<div style="position:absolute; top:55%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><h2>{comm}</h2><p>{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

# --- [컨트롤러 & 봇 행동 로직] ---
with col2:
    st.markdown("### Control")
    
    # 1. 게임 오버
    if data['phase'] == 'GAME_OVER':
        if st.button("다음 판 진행", type="primary"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
            
    # 2. 형님 차례
    elif curr_idx == my_seat:
        st.success("형님 차례입니다!")
        to_call = data['current_bet'] - me['bet']
        
        # 버튼들
        btn_txt = "체크" if to_call == 0 else f"콜 ({to_call})"
        if st.button(btn_txt, use_container_width=True):
            pay = min(to_call, me['stack'])
            me['stack'] -= pay; me['bet'] += pay; data['pot'] += pay
            me['action'] = "체크" if pay == 0 else f"콜 ({pay})"
            me['has_acted'] = True
            save_data(data); next_turn(data); st.rerun()

        if st.button("폴드", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "폴드"; me['has_acted'] = True
            save_data(data); next_turn(data); st.rerun()
            
        min_r = max(200, data['current_bet']*2)
        if me['stack'] > min_r:
            val = st.slider("레이즈", int(min_r), int(me['stack']), int(min_r))
            if st.button("레이즈 확정", use_container_width=True):
                pay = val - me['bet']
                me['stack'] -= pay; me['bet'] = val; data['pot'] += pay
                data['current_bet'] = val; me['action'] = f"레이즈 ({val})"; me['has_acted'] = True
                # 레이즈 시 다른 사람 리셋
                for p in data['players']:
                    if p != me and p['status']=='alive' and p['stack']>0: p['has_acted']=False
                save_data(data); next_turn(data); st.rerun()
                
        if st.button("올인", use_container_width=True):
            amt = me['stack']; me['stack'] = 0; me['bet'] += amt; data['pot'] += amt
            if me['bet'] > data['current_bet']:
                data['current_bet'] = me['bet']
                for p in data['players']:
                    if p != me and p['status']=='alive': p['has_acted']=False
            me['action'] = "올인"; me['has_acted'] = True
            save_data(data); next_turn(data); st.rerun()

    # 3. 봇 차례 (자동 진행)
    else:
        if not curr_p['is_human']:
            st.info(f"🤖 {curr_p['name']} 생각 중...")
            
            # [핵심] 화면 그려진 후 여기서 1.5초 대기
            time.sleep(1.5)
            
            # 봇 행동 계산
            act, amt = get_bot_decision(curr_p, data)
            actual = min(amt, curr_p['stack'])
            
            curr_p['stack'] -= actual; curr_p['bet'] += actual
            data['pot'] += actual
            
            if curr_p['bet'] > data['current_bet']:
                data['current_bet'] = curr_p['bet']
                for p in data['players']:
                    if p != curr_p and p['status']=='alive' and p['stack']>0: p['has_acted']=False
            
            act_str = f"{act} ({curr_p['bet']})" if act != "Fold" else "폴드"
            if act == "Call" and actual == 0: act_str = "체크"
            
            curr_p['action'] = act_str
            if act == "Fold": curr_p['status'] = 'folded'
            curr_p['has_acted'] = True
            
            # 저장 후 턴 넘기고 리런
            save_data(data)
            next_turn(data)
            st.rerun()
        else:
            st.info(f"👤 {curr_p['name']} (친구) 대기 중...")
            time.sleep(2)
            st.rerun()
