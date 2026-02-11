import streamlit as st
import random
import time
import os
import json

# ==========================================
# 1. 설정 & 디자인 (형님 원판 100%)
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
# 2. 데이터 엔진 (순차 진행용 파일)
# ==========================================
DATA_FILE = "poker_v8_seq.json"

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
            if 'players' not in data: return init_game_data()
            return data
    except:
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        d = init_game_data(); save_data(d); return d

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f: json.dump(data, f)

# ==========================================
# 3. 봇 & 게임 로직 (단일 행동 처리)
# ==========================================
def make_card(card):
    if not card or len(card) < 2: return "🂠"
    color = "red" if card[1] in ['♥', '♦'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

def get_bot_decision(player, data):
    roll = random.random()
    to_call = data['current_bet'] - player['bet']
    if to_call == 0: return "Check", 0
    if roll < 0.15: return "Fold", 0
    return "Call", to_call

def proceed_game_logic(data):
    """
    한 명의 플레이어(봇)만 처리하고 저장 후 종료하는 함수.
    이게 실행되면 반드시 UI가 갱신됨.
    """
    curr_idx = data['turn_idx']
    curr_p = data['players'][curr_idx]
    
    # 1. 봇 행동 계산
    act, amt = get_bot_decision(curr_p, data)
    actual_amt = min(amt, curr_p['stack'])
    
    # 2. 상태 업데이트
    curr_p['stack'] -= actual_amt
    curr_p['bet'] += actual_amt
    data['pot'] += actual_amt
    data['current_bet'] = max(data['current_bet'], curr_p['bet'])
    curr_p['action'] = act
    curr_p['has_acted'] = True
    
    # 3. 다음 턴 지정 (죽은 사람 건너뛰기)
    next_idx = curr_idx
    for i in range(1, 10):
        next_idx = (curr_idx + i) % 9
        if data['players'][next_idx]['status'] == 'alive':
            data['turn_idx'] = next_idx
            break
            
    # 4. 페이즈 종료 체크
    check_phase_end(data)
    
    # 5. 저장
    save_data(data)

def check_phase_end(data):
    active = [p for p in data['players'] if p['status'] == 'alive']
    if len(active) <= 1:
        data['phase'] = 'GAME_OVER'; data['msg'] = f"🏆 {active[0]['name']} 승리!"
        return

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
            data['phase'] = 'GAME_OVER'; data['msg'] = "쇼다운!"; return
            
        if next_p:
            data['current_bet'] = 0
            for p in data['players']:
                p['bet'] = 0; p['has_acted'] = False; p['action'] = ''
            
            dealer = data['dealer_idx']
            for i in range(1, 10):
                idx = (dealer + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break

# ==========================================
# 4. 메인 실행
# ==========================================
if 'my_seat' not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트 - FINAL")
    u_name = st.text_input("닉네임 입력", value="형님")
    if st.button("입장하기", type="primary", use_container_width=True):
        data = load_data()
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
    st.stop()

# 게임 데이터 로드
data = load_data()
my_seat = st.session_state['my_seat']
curr_idx = data['turn_idx']
curr_p = data['players'][curr_idx]

# 타이머 & HUD
elapsed = time.time() - data['start_time']
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl-1]
timer_str = f"{int(600-(elapsed%600))//60:02d}:{int(600-(elapsed%600))%60:02d}"

st.markdown(f'<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>📊 Pot: {data["pot"]:,}</div></div>', unsafe_allow_html=True)

# 테이블 렌더링
col_table, col_controls = st.columns([3, 1])
with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm_str = "".join([make_card(c) for c in data['community']])
    for i in range(9):
        p = data['players'][i]
        active = "active-turn" if i == curr_idx else ""
        hero = "hero-seat" if i == my_seat else ""
        if i == my_seat: cards = f"<div style='margin-top:5px;'>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
        else: cards = "<div style='margin-top:10px; font-size:24px;'>🂠 🂠</div>"
        role = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        html += f'<div class="seat pos-{i} {active} {hero}">{role}<div><b>{p["name"]}</b></div><div>🪙 {int(p["stack"]):,}</div>{cards}<div class="action-badge">{p["action"]}</div></div>'
    html += f'<div style="position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white;"><h2>Pot: {data["pot"]:,}</h2><div>{comm_str}</div><p>{data["msg"]}</p></div></div>'
    st.markdown(html, unsafe_allow_html=True)

# 컨트롤러 & 자동 진행
with col_controls:
    st.markdown("### 🎮 Control")
    
    # 1. 봇 턴일 때 (자동 진행)
    if curr_idx != my_seat and data['phase'] != 'GAME_OVER':
        if not curr_p['is_human']:
            st.info(f"⏳ {curr_p['name']} 생각 중...")
            time.sleep(1) # [중요] 1초 딜레이 -> 형님 눈에 보임
            proceed_game_logic(data) # 봇 행동 처리 & 저장
            st.rerun() # [중요] 화면 즉시 갱신 -> 다음 봇 보여줌
        else:
            st.info(f"⏳ {curr_p['name']} (친구) 대기 중...")
            time.sleep(2)
            st.rerun()

    # 2. 형님 턴일 때 (버튼 입력)
    elif curr_idx == my_seat and data['phase'] != 'GAME_OVER':
        st.success("📢 형님 차례!")
        to_call = data['current_bet'] - data['players'][my_seat]['bet']
        
        if st.button("체크/콜", use_container_width=True):
            me = data['players'][my_seat]
            me['stack'] -= to_call; me['bet'] += to_call; data['pot'] += to_call
            me['action'] = "Call" if to_call > 0 else "Check"
            me['has_acted'] = True
            
            # 다음 턴 찾기
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            check_phase_end(data)
            save_data(data); st.rerun()

        if st.button("폴드", type="primary", use_container_width=True):
            data['players'][my_seat]['status'] = 'folded'
            data['players'][my_seat]['action'] = 'Fold'
            data['players'][my_seat]['has_acted'] = True
            
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            check_phase_end(data)
            save_data(data); st.rerun()
            
        st.markdown("---")
        if st.button("🚨 올인", use_container_width=True):
            me = data['players'][my_seat]
            amt = me['stack']; me['stack'] = 0; me['bet'] += amt; data['pot'] += amt
            data['current_bet'] = max(data['current_bet'], me['bet'])
            me['action'] = "All-in"; me['has_acted'] = True
            
            for i in range(1, 10):
                idx = (my_seat + i) % 9
                if data['players'][idx]['status'] == 'alive':
                    data['turn_idx'] = idx; break
            
            check_phase_end(data)
            save_data(data); st.rerun()

    # 3. 게임 오버일 때
    elif data['phase'] == 'GAME_OVER':
        if st.button("▶️ 다음 판 진행", type="primary", use_container_width=True):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
