import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 디자인 & 설정 (형님 원판 100% 고정)
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
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000; z-index:100; white-space: nowrap;}
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진
# ==========================================
DATA_FILE = "poker_v9_real.json" # 파일명 변경 (완전 초기화)

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
    # 0번 딜러
    players[0]['role'] = 'D'; players[1]['role'] = 'SB'; players[2]['role'] = 'BB'
    players[1]['stack'] -= 100; players[1]['bet'] = 100; players[1]['action'] = 'SB'
    players[2]['stack'] -= 200; players[2]['bet'] = 200; players[2]['action'] = 'BB'
    
    return {
        'players': players, 'pot': 300, 'deck': deck, 'community': [],
        'phase': 'PREFLOP', 'current_bet': 200, 
        'turn_idx': 3, # UTG부터 시작
        'dealer_idx': 0, 'sb': 100, 'bb': 200, 'ante': 0, 'level': 1, 'start_time': time.time(),
        'msg': "게임을 시작합니다!"
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
# 3. 봇 지능 & 카드 유틸
# ==========================================
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

def get_bot_decision(player, data):
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    
    # 체크 가능하면 체크
    if to_call == 0: return "Check", 0
    
    # 10% 확률로 폴드
    if roll < 0.1: return "Fold", 0
    
    # 10% 확률로 레이즈 (2배)
    if roll < 0.2:
        raise_amt = data['current_bet'] * 2
        if raise_amt < data['bb'] * 2: raise_amt = data['bb'] * 2
        return "Raise", raise_amt
        
    # 나머지는 콜
    return "Call", to_call

# ==========================================
# 4. [핵심] 턴 및 페이즈 관리 로직 (형님 지적사항 수정)
# ==========================================
def next_turn(data):
    """
    다음 행동할 사람을 찾거나, 페이즈를 종료시키는 함수
    """
    players = data['players']
    active = [p for p in players if p['status'] == 'alive' and p['stack'] > 0]
    
    if len(active) <= 1: # 승자 결정
        winner = active[0]
        winner['stack'] += data['pot']
        data['phase'] = 'GAME_OVER'; data['msg'] = f"🏆 {winner['name']} 승리 (All Fold)"
        save_data(data); return

    # 1. 모든 사람이 행동했는지 확인
    # 2. 모든 사람의 베팅 금액이 같은지 확인 (All-in 제외)
    bet_target = data['current_bet']
    all_acted = all(p['has_acted'] for p in active)
    all_matched = all(p['bet'] == bet_target or p['stack'] == 0 for p in active)
    
    # [수정] 프리플랍에서 BB가 아직 옵션을 안 썼으면(has_acted=False) 안 끝남
    # 봇 초기화 시 SB, BB는 has_acted=False로 둬서 자기 차례 오게 만듦 (이미 위에서 처리함)
    
    if all_acted and all_matched:
        # 페이즈 종료 -> 다음 단계로
        deck = data['deck']
        next_phase = False
        
        if data['phase'] == 'PREFLOP':
            data['phase'] = 'FLOP'; data['community'] = [deck.pop() for _ in range(3)]; next_phase = True
        elif data['phase'] == 'FLOP':
            data['phase'] = 'TURN'; data['community'].append(deck.pop()); next_phase = True
        elif data['phase'] == 'TURN':
            data['phase'] = 'RIVER'; data['community'].append(deck.pop()); next_phase = True
        elif data['phase'] == 'RIVER':
            data['phase'] = 'GAME_OVER'; data['msg'] = "쇼다운!"; save_data(data); return

        if next_phase:
            # 베팅 초기화 (팟은 유지)
            data['current_bet'] = 0
            for p in players:
                p['bet'] = 0; p['has_acted'] = False; 
                if p['status'] == 'alive': p['action'] = ''
            
            # [중요] 포스트플랍은 딜러(SB) 다음부터 시작
            # 딜러가 0번이면 1번(SB)부터 찾음
            start_idx = data['dealer_idx']
            for i in range(1, 10):
                idx = (start_idx + i) % 9
                if players[idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            save_data(data)
            return

    # 페이즈가 안 끝났으면 다음 사람 찾기
    curr = data['turn_idx']
    for i in range(1, 10):
        idx = (curr + i) % 9
        if players[idx]['status'] == 'alive' and players[idx]['stack'] > 0:
            data['turn_idx'] = idx; break
    save_data(data)

# ==========================================
# 5. 입장 화면 (안전 게이트)
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - REAL RULE")
    u_name = st.text_input("닉네임 입력", value="형님")
    col1, col2 = st.columns(2)
    
    if col1.button("입장하기", type="primary", use_container_width=True):
        data = load_data()
        # 재접속 or 4번 자리 뺏기
        target = -1
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name: target = i; break
        
        if target == -1: # 신규
            target = 4
            if data['players'][4]['is_human']: # 4번 차있으면 빈자리
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
        st.success("초기화 완료."); st.rerun()
    st.stop()

# ==========================================
# 6. 메인 게임 루프
# ==========================================
data = load_data()
if st.session_state['my_seat'] >= len(data['players']): del st.session_state['my_seat']; st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# [봇 자동 진행] - 내 턴 아니면 봇 행동
if curr_idx != my_seat and data['phase'] != 'GAME_OVER':
    if not curr_p['is_human']:
        time.sleep(1) # 1초 뜸 들이기 (순차 진행)
        
        act, amt = get_bot_decision(curr_p, data)
        
        # 레이즈면 금액 확인
        if act == "Raise":
            final_bet = amt
        else: # Call or Check
            final_bet = data['current_bet']
            
        to_pay = final_bet - curr_p['bet']
        actual_pay = min(to_pay, curr_p['stack'])
        
        curr_p['stack'] -= actual_pay
        curr_p['bet'] += actual_pay
        data['pot'] += actual_pay
        
        if curr_p['bet'] > data['current_bet']: # 레이즈 발생
            data['current_bet'] = curr_p['bet']
            # 레이즈 했으므로 다른 사람들 has_acted 초기화 (다시 콜 해야 함)
            for p in data['players']:
                if p != curr_p and p['status'] == 'alive' and p['stack'] > 0:
                    p['has_acted'] = False
        
        # 액션 표시 (금액 포함)
        if act == "Raise": curr_p['action'] = f"Raise {curr_p['bet']}"
        elif act == "Call": curr_p['action'] = f"Call {actual_pay}" if actual_pay > 0 else "Check"
        elif act == "Check": curr_p['action'] = "Check"
        elif act == "Fold": curr_p['action'] = "Fold"; curr_p['status'] = 'folded'
        
        curr_p['has_acted'] = True
        save_data(data)
        
        # 턴 넘기기
        next_turn(data)
        st.rerun()
    else:
        # 친구 턴이면 대기
        time.sleep(2); st.rerun()

# ==========================================
# 7. 화면 그리기
# ==========================================
elapsed = time.time() - data['start_time']
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb}</div><div>📊 Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_str = "".join([make_card(c) for c in data['community']])
    
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == data['turn_idx'] else ""
        hero = "hero-seat" if i == my_seat else ""
        
        if i == my_seat or data['phase'] == 'GAME_OVER': # 쇼다운 시 카드 공개
            if p['hand']: cards = f"<div style='margin-top:5px;'>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
            else: cards = "<div></div>"
        else:
            cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>" if p['status'] == 'alive' else ""
            
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        # [수정] 액션 뱃지에 금액 등 디테일 표시
        html += f'<div class="seat pos-{i} {active} {hero}">{role}<div><b>{p["name"]}</b></div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><h2>Pot: {data["pot"]:,}</h2><div>{comm_str}</div><p>{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    st.markdown("### 🎮 Control")
    if curr_idx == my_seat and data['phase'] != 'GAME_OVER':
        st.success("📢 형님 차례!")
        
        # 콜 금액 계산
        to_call = data['current_bet'] - me['bet']
        
        # 1. 체크/콜
        btn_txt = "체크 (Check)" if to_call == 0 else f"콜 (Call {to_call:,})"
        if st.button(btn_txt, use_container_width=True):
            pay = min(to_call, me['stack'])
            me['stack'] -= pay; me['bet'] += pay; data['pot'] += pay
            me['action'] = "Check" if pay == 0 else f"Call {pay}"
            me['has_acted'] = True
            save_data(data)
            next_turn(data)
            st.rerun()

        # 2. 폴드
        if st.button("폴드 (Fold)", type="primary", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "Fold"
            me['has_acted'] = True
            save_data(data)
            next_turn(data)
            st.rerun()

        st.markdown("---")
        
        # 3. 레이즈 (슬라이더 고침)
        # 최소 레이즈: 현재 베팅의 2배 or BB의 2배
        min_raise = max(data['bb'] * 2, data['current_bet'] * 2)
        max_raise = int(me['stack'] + me['bet']) # 내 전재산(이미 건 돈 포함)
        
        if max_raise >= min_raise:
            # 슬라이더는 '총 베팅 금액' 기준
            raise_target = st.slider("레이즈 금액 (Total)", int(min_raise), int(max_raise), int(min_raise))
            
            if st.button(f"레이즈 ({raise_target:,})", use_container_width=True):
                needed = raise_target - me['bet']
                me['stack'] -= needed; me['bet'] = raise_target; data['pot'] += needed
                
                # 레이즈 발생 -> 룰 적용
                data['current_bet'] = raise_target
                me['action'] = f"Raise {raise_target}"
                me['has_acted'] = True
                
                # [중요] 나 빼고 다른 사람들 다시 액션하도록 has_acted 초기화
                for p in data['players']:
                    if p != me and p['status'] == 'alive' and p['stack'] > 0:
                        p['has_acted'] = False
                        
                save_data(data)
                next_turn(data)
                st.rerun()
        else:
             if st.button("🚨 올인 (All-in)", use_container_width=True):
                amt = me['stack']; me['stack'] = 0; me['bet'] += amt; data['pot'] += amt
                if me['bet'] > data['current_bet']:
                    data['current_bet'] = me['bet']
                    for p in data['players']: # 올인 레이즈 시 초기화
                        if p != me and p['status'] == 'alive': p['has_acted'] = False
                me['action'] = "All-in"; me['has_acted'] = True
                save_data(data); next_turn(data); st.rerun()

    elif data['phase'] == 'GAME_OVER':
        if st.button("▶️ 다음 판 (Next Hand)", type="primary", use_container_width=True):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
    else:
        st.info(f"⏳ {curr_p['name']} 턴...")
