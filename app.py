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
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; }
.action-badge { position: absolute; bottom: -15px; background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px; font-size: 11px; border: 1px solid #000; z-index:100; white-space: nowrap;}
.fold-text { color: #ff5252; font-weight: bold; font-size: 18px; margin-top: 20px; }
.folded-seat { opacity: 0.4; border: 3px solid #333 !important; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 엔진 (안전 저장 V12)
# ==========================================
DATA_FILE = "poker_v12_step.json"

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
# 3. 상세 족보 & 유틸리티 (형님 요청: 누가 어떻게 이겼는지)
# ==========================================
def r_str(r): return DISPLAY_MAP.get(r, r)

def make_card(card):
    if not card or len(card) < 2: return "🂠"
    rank = r_str(card[0])
    suit = card[1]
    color = "red" if suit in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{rank}{suit}</span>"

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
    groups = sorted([(c, r) for r, c in counts.items()], reverse=True)
    
    if is_flush and is_straight: return (8, ranks, "스트레이트 플러시")
    if groups[0][0] == 4: return (7, ranks, f"포카드 ({r_str(RANKS[groups[0][1]])})")
    if groups[0][0] == 3 and groups[1][0] >= 2: return (6, ranks, f"풀하우스 ({r_str(RANKS[groups[0][1]])})")
    if is_flush: return (5, ranks, "플러시")
    if is_straight: return (4, ranks, "스트레이트")
    if groups[0][0] == 3: return (3, ranks, f"트리플 ({r_str(RANKS[groups[0][1]])})")
    if groups[0][0] == 2 and groups[1][0] == 2: return (2, ranks, f"투페어 ({r_str(RANKS[groups[0][1]])} & {r_str(RANKS[groups[1][1]])})")
    if groups[0][0] == 2: return (1, ranks, f"원페어 ({r_str(RANKS[groups[0][1]])})")
    return (0, ranks, f"하이카드 ({r_str(RANKS[groups[0][1]])})")

def get_bot_decision(player, data):
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.15: return "Fold", 0
    if roll < 0.3: return "Raise", max(data['bb']*2, data['current_bet']*2)
    return "Call", to_call

# ==========================================
# 4. 페이즈 전환 로직 (카드 실종 해결)
# ==========================================
def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        winner = active[0]
        winner['stack'] += data['pot']
        data['msg'] = f"🏆 {winner['name']} 승리! (All Fold)"
        data['phase'] = 'GAME_OVER'
        save_data(data); return True

    bet_target = data['current_bet']
    all_acted = all(p['has_acted'] for p in active)
    all_matched = all(p['bet'] == bet_target or p['stack'] == 0 for p in active)
    
    if all_acted and all_matched:
        deck = data['deck']
        next_p = False
        if data['phase'] == 'PREFLOP':
            data['phase'] = 'FLOP'; data['community'] = [deck.pop() for _ in range(3)]; next_p=True
        elif data['phase'] == 'FLOP':
            data['phase'] = 'TURN'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'TURN':
            data['phase'] = 'RIVER'; data['community'].append(deck.pop()); next_p=True
        elif data['phase'] == 'RIVER':
            # 승자 판독 (형님이 원하던 상세 정보)
            best_score = (-1, [])
            best_desc = ""
            winners = []
            
            for p in active:
                score, rks, desc = get_hand_strength_detail(p['hand'] + data['community'])
                if score > best_score[0] or (score == best_score[0] and rks > best_score[1]):
                    best_score = (score, rks); best_desc = desc; winners = [p]
                elif score == best_score[0] and rks == best_score[1]:
                    winners.append(p)
            
            win_names = [w['name'] for w in winners]
            data['msg'] = f"🏆 {', '.join(win_names)} 승리! [{best_desc}]"
            split = data['pot'] // len(winners)
            for w in winners: w['stack'] += split
            data['pot'] = 0
            
            data['phase'] = 'GAME_OVER'; save_data(data); return True
            
        if next_p:
            data['current_bet'] = 0
            for p in data['players']:
                p['bet'] = 0; p['has_acted'] = False; 
                if p['status'] == 'alive': p['action'] = ''
            
            # 포스트플랍은 SB부터
            dealer = data['dealer_idx']
            for i in range(1, 10):
                idx = (dealer + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            save_data(data); return True
    return False

# ==========================================
# 5. 입장 화면
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - 순차 액션")
    u_name = st.text_input("닉네임", value="형님")
    col1, col2 = st.columns(2)
    if col1.button("입장하기", type="primary", use_container_width=True):
        data = load_data()
        target = 4
        if data['players'][4]['is_human']:
            for i in range(9):
                if not data['players'][i]['is_human']: target = i; break
        
        # 재접속 체크
        found = -1
        for i, p in enumerate(data['players']):
            if p['is_human'] and p['name'] == u_name: found = i; break
            
        if found != -1: target = found
        else:
            data['players'][target]['name'] = u_name
            data['players'][target]['is_human'] = True
            data['players'][target]['status'] = 'alive'
            save_data(data)
            
        st.session_state['my_seat'] = target
        st.rerun()

    if col2.button("서버 초기화"):
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        st.rerun()
    st.stop()

# ==========================================
# 6. 메인 게임 루프 (봇 순차 행동 핵심)
# ==========================================
data = load_data()
if st.session_state['my_seat'] >= len(data['players']): del st.session_state['my_seat']; st.rerun()

my_seat = st.session_state['my_seat']
me = data['players'][my_seat]
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# 봇 행동 처리
if curr_idx != my_seat and data['phase'] != 'GAME_OVER':
    if not curr_p['is_human']:
        # 1초 대기 (이게 있어야 순차적으로 보임)
        time.sleep(1)
        
        # 행동 결정
        act, amt = get_bot_decision(curr_p, data)
        actual = min(amt, curr_p['stack'])
        
        curr_p['stack'] -= actual
        curr_p['bet'] += actual
        data['pot'] += actual
        
        # 레이즈 발생 시
        if curr_p['bet'] > data['current_bet']:
            data['current_bet'] = curr_p['bet']
            # 다른 사람들 다시 액션해야 함
            for p in data['players']:
                if p != curr_p and p['status'] == 'alive' and p['stack'] > 0:
                    p['has_acted'] = False
        
        # 액션 기록
        if act == "Raise": curr_p['action'] = f"Raise {curr_p['bet']}"
        elif act == "Call": curr_p['action'] = f"Call {actual}" if actual > 0 else "Check"
        elif act == "Check": curr_p['action'] = "Check"
        elif act == "Fold": curr_p['action'] = "Fold"; curr_p['status'] = 'folded'
        
        curr_p['has_acted'] = True
        
        # 다음 턴 넘기기
        for i in range(1, 10):
            idx = (curr_idx + i) % 9
            if data['players'][idx]['status'] == 'alive':
                data['turn_idx'] = idx; break
        
        check_phase_end(data)
        save_data(data)
        st.rerun() # [핵심] 한 명 행동 후 무조건 새로고침 -> 순차 갱신
    else:
        # 친구 턴이면 대기
        time.sleep(2); st.rerun()

# ==========================================
# 7. 화면 렌더링
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
        active = "active-turn" if i == data['turn_idx'] and data['phase'] != 'GAME_OVER' else ""
        hero = "hero-seat" if i == my_seat else ""
        
        # [폴드 표시 & 카드 오픈]
        if p['status'] == 'folded':
            cards = "<div class='fold-text'>FOLD</div>"
            style_cls = "folded-seat"
        else:
            style_cls = ""
            if i == my_seat or (data['phase'] == 'GAME_OVER' and p['status'] == 'alive'):
                if p['hand']: cards = f"<div style='margin-top:5px;'>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
                else: cards = "<div></div>"
            else:
                cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>"
            
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero} {style_cls}">{role}<div><b>{p["name"]}</b></div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><h2>Pot: {data["pot"]:,}</h2><div>{comm_str}</div><p style="font-size:18px; color:#ffeb3b; font-weight:bold; margin-top:10px;">{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    st.markdown("### 🎮 Control")
    if curr_idx == my_seat and data['phase'] != 'GAME_OVER':
        st.success("📢 형님 차례!")
        to_call = data['current_bet'] - me['bet']
        
        # 체크/콜
        btn = "체크 (Check)" if to_call == 0 else f"콜 (Call {to_call:,})"
        if st.button(btn, use_container_width=True):
            pay = min(to_call, me['stack'])
            me['stack'] -= pay; me['bet'] += pay; data['pot'] += pay
            me['action'] = "Check" if pay == 0 else f"Call {pay}"
            me['has_acted'] = True
            
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            check_phase_end(data)
            save_data(data); st.rerun()

        # 폴드
        if st.button("폴드 (Fold)", type="primary", use_container_width=True):
            me['status'] = 'folded'; me['action'] = "Fold"; me['has_acted'] = True
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            check_phase_end(data)
            save_data(data); st.rerun()

        st.markdown("---")
        # 레이즈
        min_r = max(data['bb']*2, data['current_bet']*2)
        if me['stack'] > min_r:
            val = st.slider("레이즈", int(min_r), int(me['stack']), int(min_r))
            if st.button(f"레이즈 {val}", use_container_width=True):
                pay = val - me['bet']
                me['stack'] -= pay; me['bet'] = val; data['pot'] += pay; data['current_bet'] = val
                me['action'] = f"Raise {val}"; me['has_acted'] = True
                
                # 다른 사람 has_acted 초기화
                for p in data['players']:
                    if p != me and p['status'] == 'alive' and p['stack'] > 0: p['has_acted'] = False
                    
                for i in range(1, 10):
                    idx = (my_seat + i) % 9
                    if data['players'][idx]['status'] == 'alive':
                        data['turn_idx'] = idx; break
                save_data(data); st.rerun()
        
        if st.button("🚨 올인", use_container_width=True):
            amt = me['stack']; me['stack'] = 0; me['bet'] += amt; data['pot'] += amt
            if me['bet'] > data['current_bet']:
                data['current_bet'] = me['bet']
                for p in data['players']:
                    if p != me and p['status'] == 'alive': p['has_acted'] = False
            me['action'] = "All-in"; me['has_acted'] = True
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
        st.info(f"⏳ {curr_p['name']} 턴...")
