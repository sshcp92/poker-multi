import streamlit as st
import random
import time
import os
import json
from datetime import datetime

# ==========================================
# 1. 파일 기반 데이터 관리 (멀티플레이 핵심)
# ==========================================
DATA_FILE = "poker_data.json"

def load_game_data():
    """게임 데이터를 파일에서 불러옵니다."""
    if not os.path.exists(DATA_FILE):
        return init_game_data()
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return init_game_data()

def save_game_data(data):
    """게임 데이터를 파일에 저장합니다."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_game_data():
    """초기 게임 데이터를 생성합니다."""
    start_stack = 60000
    # 9개의 빈 좌석 생성
    players = []
    for i in range(1, 10):
        players.append({
            'name': 'Empty', 'seat': i, 'stack': start_stack, 'hand': [], 
            'status': 'waiting', 'bet': 0, 'total_bet_hand': 0, 
            'action': '', 'role': '', 'has_acted': False, 'buyin_count': 1,
            'is_human': False # 사람이 들어오면 True로 변경
        })
    
    data = {
        'players': players,
        'pot': 0,
        'deck': [],
        'community': [],
        'phase': 'PREFLOP',
        'current_bet': 0,
        'turn_idx': 0, # 현재 행동해야 할 플레이어 인덱스
        'dealer_idx': 0,
        'sb_amount': 100,
        'bb_amount': 200,
        'ante_amount': 0,
        'level': 1,
        'message': "게임을 시작하려면 2명 이상 입장 후 '게임 시작'을 눌러주세요.",
        'game_started': False,
        'start_time': time.time(),
        'showdown_phase': False,
        'last_update': time.time()
    }
    save_game_data(data)
    return data

# ==========================================
# 2. 설정 및 초기화
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

# 블라인드 구조 (형님 코드 그대로)
BLIND_STRUCTURE = [
    (100, 200, 0), (200, 400, 0), (300, 600, 600), (400, 800, 800),
    (500, 1000, 1000), (1000, 2000, 2000), (2000, 4000, 4000), (5000, 10000, 10000)
]
LEVEL_DURATION = 600
RANKS = '23456789TJQKA'
SUITS = ['\u2660', '\u2665', '\u2666', '\u2663']
DISPLAY_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}

# ==========================================
# 3. 유틸리티 함수 (형님 코드 그대로)
# ==========================================
def new_deck():
    deck = [r+s for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck

def get_current_info(data):
    elapsed = time.time() - data['start_time']
    lvl_idx = int(elapsed // LEVEL_DURATION)
    if lvl_idx >= len(BLIND_STRUCTURE): lvl_idx = len(BLIND_STRUCTURE) - 1
    sb, bb, ante = BLIND_STRUCTURE[lvl_idx]
    
    # 타이머 문자열 계산
    next_level_time = (lvl_idx + 1) * LEVEL_DURATION
    time_left = max(0, int(next_level_time - elapsed))
    mins, secs = divmod(time_left, 60)
    timer_str = f"{mins:02d}:{secs:02d}"
    
    active_players = [p for p in data['players'] if p['status'] != 'spectator' and p['is_human']]
    total_chips = sum(p['stack'] for p in data['players'])
    avg_stack = total_chips // len(active_players) if active_players else 0
    return sb, bb, ante, lvl_idx + 1, timer_str, avg_stack

def make_card(card):
    if not card: return "🂠"
    color = "red" if card[1] in ['\u2665', '\u2666'] else "black"
    return f"<span class='card-span' style='color:{color}'>{card}</span>"

# 족보 계산 로직 (형님 코드 그대로 유지)
def get_hand_strength(hand):
    if not hand: return (-1, [])
    ranks = sorted([RANKS.index(c[0]) for c in hand], reverse=True)
    suits = [c[1] for c in hand]
    suit_counts = {s: suits.count(s) for s in set(suits)}
    flush_suit = next((s for s, c in suit_counts.items() if c >= 5), None)
    is_flush = (flush_suit is not None)
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False; straight_high = -1
    for i in range(len(unique_ranks) - 4):
        if unique_ranks[i] - unique_ranks[i+4] == 4:
            is_straight = True; straight_high = unique_ranks[i]; break
    if not is_straight and set([12, 3, 2, 1, 0]).issubset(set(ranks)):
        is_straight = True; straight_high = 3
    counts = {r: ranks.count(r) for r in ranks}
    sorted_groups = sorted([(c, r) for r, c in counts.items()], reverse=True)
    
    if is_flush and is_straight:
        flush_cards = sorted([RANKS.index(c[0]) for c in hand if c[1] == flush_suit], reverse=True)
        f_unique = sorted(list(set(flush_cards)), reverse=True)
        sf_high = -1; found_sf = False
        for i in range(len(f_unique) - 4):
            if f_unique[i] - f_unique[i+4] == 4:
                sf_high = f_unique[i]; found_sf = True; break
        if not found_sf and set([12, 3, 2, 1, 0]).issubset(set(f_unique)):
            sf_high = 3; found_sf = True
        if found_sf:
            if sf_high == 12: return (9, [12], "로얄 스트레이트 플러시")
            return (8, [sf_high], "스트레이트 플러시") # Display map 제거 for simplicity
    if sorted_groups[0][0] == 4:
        quad = sorted_groups[0][1]
        kicker = sorted([r for r in ranks if r != quad], reverse=True)[0]
        return (7, [quad, kicker], "포카드")
    if sorted_groups[0][0] == 3 and sorted_groups[1][0] >= 2:
        trip = sorted_groups[0][1]; pair = sorted_groups[1][1]
        return (6, [trip, pair], "풀하우스")
    if is_flush:
        flush_ranks = sorted([RANKS.index(c[0]) for c in hand if c[1] == flush_suit], reverse=True)[:5]
        return (5, flush_ranks, "플러시")
    if is_straight: return (4, [straight_high], "스트레이트")
    if sorted_groups[0][0] == 3:
        trip = sorted_groups[0][1]
        kickers = sorted([r for r in ranks if r != trip], reverse=True)[:2]
        return (3, [trip] + kickers, "트리플")
    if sorted_groups[0][0] == 2 and sorted_groups[1][0] == 2:
        p1 = sorted_groups[0][1]; p2 = sorted_groups[1][1]
        kicker = sorted([r for r in ranks if r != p1 and r != p2], reverse=True)[0]
        return (2, [p1, p2, kicker], "투페어")
    if sorted_groups[0][0] == 2:
        pair = sorted_groups[0][1]
        kickers = sorted([r for r in ranks if r != pair], reverse=True)[:3]
        return (1, [pair] + kickers, "원페어")
    return (0, ranks[:5], "하이카드")

# ==========================================
# 4. 게임 로직 (멀티플레이용으로 수정)
# ==========================================
def next_turn(data):
    # 다음 행동할 사람 찾기
    players = data['players']
    active_players = [i for i, p in enumerate(players) if p['status'] == 'alive' and p['stack'] > 0]
    
    # 1명만 남았으면 승리 처리
    alive_count = len([p for p in players if p['status'] == 'alive'])
    if alive_count <= 1:
        winner = [p for p in players if p['status'] == 'alive'][0]
        winner['stack'] += data['pot']
        data['message'] = f"🏆 {winner['name']} 승리! (All Fold)"
        data['phase'] = 'GAME_OVER'
        data['pot'] = 0
        save_game_data(data)
        return

    # 베팅이 끝났는지 확인
    current_bet = data['current_bet']
    all_matched = True
    for idx in active_players:
        p = players[idx]
        if not p['has_acted'] or (p['bet'] < current_bet and p['stack'] > 0):
            all_matched = False
            break
            
    if all_matched:
        proceed_to_next_street(data)
        return

    # 다음 턴 넘기기
    current_idx = data['turn_idx']
    for _ in range(9):
        current_idx = (current_idx + 1) % 9
        p = players[current_idx]
        if p['status'] == 'alive' and p['stack'] > 0:
            data['turn_idx'] = current_idx
            save_game_data(data)
            return

def proceed_to_next_street(data):
    phase = data['phase']
    deck = data['deck']
    
    # 덱이 없으면 새로 생성 (안전장치)
    if not deck: 
        data['deck'] = new_deck()
        deck = data['deck']

    if phase == 'PREFLOP':
        data['phase'] = 'FLOP'
        data['community'] = [deck.pop() for _ in range(3)]
    elif phase == 'FLOP':
        data['phase'] = 'TURN'
        data['community'].append(deck.pop())
    elif phase == 'TURN':
        data['phase'] = 'RIVER'
        data['community'].append(deck.pop())
    elif phase == 'RIVER':
        determine_winner(data)
        return

    # 베팅 초기화
    data['current_bet'] = 0
    for p in data['players']:
        p['bet'] = 0
        p['has_acted'] = False
        if p['status'] == 'alive':
            p['action'] = ''
    
    # 턴 초기화 (SB 다음부터)
    # 실제로는 딜러 다음 살아있는 사람부터
    dealer = data['dealer_idx']
    next_player = dealer
    for _ in range(9):
        next_player = (next_player + 1) % 9
        p = data['players'][next_player]
        if p['status'] == 'alive' and p['stack'] > 0:
            data['turn_idx'] = next_player
            break
            
    save_game_data(data)

def determine_winner(data):
    # (형님 코드의 승자 판별 로직을 간소화하여 적용 - 분량상 핵심만 유지)
    players = data['players']
    active_players = [p for p in players if p['status'] == 'alive']
    
    if not active_players: return

    best_score = (-1, [])
    winners = []
    
    for p in active_players:
        score = get_hand_strength(p['hand'] + data['community'])
        if score > best_score:
            best_score = score
            winners = [p]
        elif score == best_score:
            winners.append(p)
            
    win_amount = data['pot'] // len(winners)
    winner_names = []
    for w in winners:
        w['stack'] += win_amount
        winner_names.append(w['name'])
    
    data['message'] = f"승자: {', '.join(winner_names)} ({best_score[2]})"
    data['phase'] = 'GAME_OVER'
    data['pot'] = 0
    data['showdown_phase'] = True
    save_game_data(data)

def start_new_hand(data):
    data['deck'] = new_deck()
    data['community'] = []
    data['pot'] = 0
    data['phase'] = 'PREFLOP'
    data['message'] = "새로운 핸드 시작"
    data['showdown_phase'] = False
    
    # 딜러 이동
    data['dealer_idx'] = (data['dealer_idx'] + 1) % 9
    
    # 블라인드 정보 갱신
    sb, bb, ante, lvl, _, _ = get_current_info(data)
    data['current_bet'] = bb
    
    players = data['players']
    
    # 핸드 분배 및 블라인드 처리
    # (간소화를 위해 참가자 전원에게 카드 분배)
    alive_players_idx = []
    for i, p in enumerate(players):
        if p['is_human']:
            p['status'] = 'alive'
            p['hand'] = [data['deck'].pop(), data['deck'].pop()]
            p['bet'] = 0
            p['total_bet_hand'] = 0
            p['action'] = ''
            p['has_acted'] = False
            p['role'] = ''
            alive_players_idx.append(i)
        else:
            p['status'] = 'waiting'
            p['hand'] = []

    if len(alive_players_idx) < 2:
        data['message'] = "플레이어가 2명 이상이어야 시작할 수 있습니다."
        save_game_data(data)
        return

    # SB, BB, UTG 설정 로직 (간단하게 dealer 다음 사람부터)
    # 실제 구현시에는 alive_players_idx 리스트를 순회하며 dealer 다음 사람 찾기
    
    # 일단 저장
    save_game_data(data)


# ==========================================
# 5. UI 및 메인 실행
# ==========================================

# 1. 닉네임 입력 및 입장 화면
if 'nickname' not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #ffd700;'>🦁 AI 몬스터 토너먼트 (멀티)</h1>", unsafe_allow_html=True)
    nickname = st.text_input("닉네임을 입력하세요", placeholder="형님")
    if st.button("입장하기", type="primary", use_container_width=True):
        if nickname:
            data = load_game_data()
            # 빈자리 찾기
            seat_found = False
            for i, p in enumerate(data['players']):
                if not p['is_human']: # 빈자리(사람이 아닌 자리)
                    p['name'] = nickname
                    p['is_human'] = True
                    p['status'] = 'alive'
                    save_game_data(data)
                    st.session_state['nickname'] = nickname
                    st.session_state['my_seat_idx'] = i
                    seat_found = True
                    st.rerun()
                    break
            if not seat_found:
                st.error("빈 자리가 없습니다!")
    st.stop() # 닉네임 없으면 여기서 멈춤

# 2. 게임 데이터 로드 및 자동 새로고침
data = load_game_data()
my_seat_idx = st.session_state['my_seat_idx']
me = data['players'][my_seat_idx]

# 자동 새로고침 (내 턴이 아니면 3초마다)
if data['turn_idx'] != my_seat_idx and data['phase'] != 'GAME_OVER' and data['game_started']:
    time.sleep(3) 
    st.rerun()

# 3. CSS 적용 (형님 코드 100% 복사)
st.markdown("""<style>
.stApp {background-color:#121212;}
.top-hud {
    display: flex; justify-content: space-around; align-items: center;
    background: #333; padding: 10px; border-radius: 10px; margin-bottom: 5px;
    border: 1px solid #555; color: white; font-weight: bold; font-size: 16px;
}
.hud-time { color: #ffeb3b; font-size: 20px; }
.game-board-container {
    position:relative; width:100%; height:650px;
    margin:0 auto; background-color:#1e1e1e; border-radius:30px; border:4px solid #333;
    overflow: hidden; 
}
.poker-table {
    position:absolute; top:45%; left:50%; transform:translate(-50%,-50%);
    width: 90%; height: 460px;
    background: radial-gradient(#5d4037, #3e2723);
    border: 20px solid #281915; border-radius: 250px;
    box-shadow: inset 0 0 50px rgba(0,0,0,0.8), 0 10px 30px rgba(0,0,0,0.5);
}
.seat {
    position:absolute; width:140px; height:160px;
    background:#2c2c2c; border:3px solid #666;
    border-radius:15px;
    color:white; text-align:center; font-size:12px;
    display:flex; flex-direction:column; justify-content:flex-start;
    padding-top: 10px; align-items:center; z-index:10;
    box-shadow: 3px 3px 15px rgba(0,0,0,0.6);
    overflow: visible !important;
}
.card-container { display: flex; justify-content: center; align-items: center; gap: 4px; margin-top: 5px; }
.hero-folded { filter: grayscale(100%) brightness(40%); opacity: 0.7; }
.seat-num { font-size: 10px; color: #aaa; margin-bottom: 2px; }
.bet-chip {color:#42a5f5; font-weight:bold; font-size:13px; text-shadow: 1px 1px 2px black;}
.buyin-badge {color:#ffcc80; font-size:10px; margin-bottom: 2px;}
.pos-0 {top:30px; right:25%;} .pos-1 {top:110px; right:5%;} .pos-2 {bottom:110px; right:5%;} .pos-3 {bottom:30px; right:25%;} .pos-4 {bottom:30px; left:50%; transform:translateX(-50%);} .pos-5 {bottom:30px; left:25%;} .pos-6 {bottom:110px; left:5%;} .pos-7 {top:110px; left:5%;} .pos-8 {top:30px; left:25%;}
.hero-seat { border:4px solid #ffd700; background:#3a3a3a; box-shadow:0 0 25px #ffd700; transform: translateX(-50%) scale(1.3); z-index: 20; }
.action-badge {
    position: absolute; bottom: -15px; left: 50%; transform: translateX(-50%);
    background:#ffeb3b; color:black; font-weight:bold; padding:2px 8px; border-radius:4px;
    z-index: 100; white-space: nowrap; box-shadow: 1px 1px 3px rgba(0,0,0,0.5); border: 1px solid #000; font-size: 11px;
}
.role-badge {
    position: absolute; top: -10px; left: -10px; width: 24px; height: 24px; border-radius: 50%;
    background: white; color: black; font-weight: bold; line-height: 22px; border: 2px solid #333; z-index: 100; box-shadow: 1px 1px 2px black;
}
.role-D { background: #ffeb3b; } .role-SB { background: #90caf9; } .role-BB { background: #ef9a9a; } 
.center-hud {position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;width:100%;color:#ddd; text-shadow: 1px 1px 3px black;}
.card-span {background:white;padding:2px 6px;border-radius:4px;margin:1px;font-weight:bold;font-size:28px;border:1px solid #ccc; line-height: 1.0;}
.control-title { font-size: 18px; font-weight: bold; color: #ddd; margin-bottom: 20px; text-align: center; }
@media screen and (max-width: 1000px) {
    .seat { width: 85px; height: 110px; font-size: 9px; padding-top: 5px; }
    .card-span { font-size: 16px; padding: 1px 3px; }
    .bet-chip { font-size: 10px; }
    .buyin-badge { font-size: 8px; }
    .seat-num { font-size: 8px; }
    .poker-table { height: 350px; border-width: 10px; }
    .game-board-container { height: 500px; }
    .hero-seat { transform: translateX(-50%) scale(1.1); }
    .pos-0 { right: 15%; } .pos-3 { right: 15%; } .pos-5 { left: 15%; } .pos-8 { left: 15%; }
    .top-hud { font-size: 12px; }
}
</style>""", unsafe_allow_html=True)

# 4. 상단 HUD
sb, bb, ante, lvl, timer_str, avg_stack = get_current_info(data)
st.markdown(f"""<div class="top-hud"><div>LEVEL {lvl}</div><div class="hud-time">⏱️ {timer_str}</div><div>🟡 {sb}/{bb} (A{ante})</div><div>📊 Avg: {avg_stack:,}</div></div>""", unsafe_allow_html=True)

col_table, col_controls = st.columns([3, 1])

# 5. 테이블 렌더링
with col_table:
    if st.button("🔄 새로고침 (수동)", use_container_width=True): st.rerun()
    
    # 내 좌석이 가운데(4번) 오도록 리스트 회전 (시각적 처리)
    # 실제 데이터 인덱스는 그대로 두고, 화면에 그리는 순서만 변경
    # 형님 코드의 로직상 4번이 Hero 자리이므로, 내 my_seat_idx가 화면상 4번에 오게 매핑
    
    # 편의상 그냥 렌더링 (형님 요청: 폼 그대로)
    
    pot_display = f"{data['pot']:,}"
    comm = data['community']
    comm_str = "".join([make_card(c) for c in comm]) if comm else "<span style='color:#999; font-size:24px;'>Waiting...</span>"
    
    html_code = '<div class="game-board-container">'
    html_code += f'<div class="poker-table"><div class="center-hud"><div style="font-size:22px;color:#a5d6a7;font-weight:bold;margin-bottom:10px;">Pot: {pot_display}</div><div style="margin:20px 0;">{comm_str}</div><div style="font-size:14px;color:#aaa;">{data["phase"]}</div><div style="color:#ffcc80; font-weight:bold; font-size:16px; margin-top:5px;">{data["message"]}</div></div></div>'

    # 좌석 렌더링
    # 내 자리(my_seat_idx)가 화면의 4번 위치(중앙 하단)에 오도록 회전
    # 화면 0 1 2 3 [4] 5 6 7 8
    # 데이터 0 1 2 3  4  5 6 7 8 (만약 내가 0번이면, 0번 데이터를 4번 위치에 그려야 함)
    # shift = 4 - my_seat_idx
    
    for i in range(9):
        # 화면상 위치 i (0~8)
        # 실제 데이터 인덱스 data_idx
        # 내가(my_seat_idx) 화면의 4번에 있어야 함.
        # i=4 일때 data_idx = my_seat_idx
        # data_idx = (i + my_seat_idx - 4) % 9
        
        data_idx = (i + my_seat_idx - 4) % 9
        p = data['players'][data_idx]
        
        seat_cls = f"pos-{i}"
        extra_cls = ""
        if i == 4: extra_cls += " hero-seat" # 화면상 중앙
        if data_idx == data['turn_idx'] and data['phase'] != 'GAME_OVER': extra_cls += " active-turn"
        
        status_txt = "<div style='color:red; font-size:10px; font-weight:bold;'>SPECTATOR</div>" if p['status'] == 'spectator' else ""
        if not p['is_human']: status_txt = "<div style='color:#777; font-size:10px;'>빈 자리</div>"

        role_html = f"<div class='role-badge role-{p['role']}'>{p['role']}</div>" if p['role'] else ""
        act_badge = f"<div class='action-badge'>{p['action']}</div>" if p['action'] else ""
        
        bet_val = f"{p['bet']:,}"
        stack_val = f"{p['stack']:,}"
        bet_display = f"<div class='bet-chip'>Bet: {bet_val}</div>" if p['bet'] > 0 else "<div class='bet-chip' style='visibility:hidden;'>-</div>"
        
        # 카드 처리
        cards_html = ""
        if p['status'] == 'folded':
             cards_html = "<div class='card-container' style='color:#777; font-size:12px;'>❌ Folded</div>"
        elif p['status'] == 'alive':
            if data_idx == my_seat_idx or data['showdown_phase']: # 내 카드거나 쇼다운
                if p['hand']:
                    c1 = make_card(p['hand'][0])
                    c2 = make_card(p['hand'][1])
                    cards_html = f"<div class='card-container'>{c1}{c2}</div>"
            else:
                cards_html = f"<div class='card-container' style='font-size:24px;'>🂠 🂠</div>"
        
        html_code += f'<div class="seat {seat_cls} {extra_cls}">{role_html}<div class="seat-num">SEAT {p["seat"]}</div><div style="font-size:12px;"><strong>{p["name"]}</strong></div><div style="font-size:12px;">🪙{stack_val}</div>{cards_html}{bet_display}{status_txt}{act_badge}</div>'

    html_code += '</div>'
    st.markdown(html_code, unsafe_allow_html=True)

# 6. 컨트롤 패널
with col_controls:
    st.markdown('<div class="control-title">🎮 Control Panel</div>', unsafe_allow_html=True)
    
    if data['phase'] == 'GAME_OVER':
        if st.button("▶️ 다음 판 진행 (Next Hand)", type="primary", use_container_width=True):
            start_new_hand(data)
            st.rerun()
    elif not data['game_started']:
        if st.button("🚀 게임 시작", type="primary", use_container_width=True):
            data['game_started'] = True
            start_new_hand(data)
            st.rerun()
    elif data['turn_idx'] == my_seat_idx: # 내 차례
        me = data['players'][my_seat_idx]
        current_bet = data['current_bet']
        to_call = current_bet - me['bet']
        
        # 버튼들
        if to_call == 0:
            if st.button("체크 (Check)", use_container_width=True):
                me['action'] = "Check"
                me['has_acted'] = True
                save_game_data(data) # 저장
                next_turn(data) # 턴 넘기기
                st.rerun()
        else:
             if st.button(f"콜 (Call {to_call:,})", use_container_width=True):
                me['stack'] -= to_call
                me['bet'] += to_call
                me['total_bet_hand'] += to_call
                data['pot'] += to_call
                me['action'] = "Call"
                me['has_acted'] = True
                save_game_data(data)
                next_turn(data)
                st.rerun()
                
        if st.button("폴드 (Fold)", type="primary", use_container_width=True):
            me['status'] = 'folded'
            me['action'] = "Fold"
            save_game_data(data)
            next_turn(data)
            st.rerun()
            
        # 레이즈 UI (간소화)
        raise_amt = st.number_input("레이즈 금액", min_value=int(current_bet * 2) if current_bet > 0 else bb, max_value=int(me['stack']), step=100)
        if st.button("레이즈 (Raise)", use_container_width=True):
            total = int(raise_amt)
            added = total - me['bet']
            if added <= me['stack']:
                me['stack'] -= added
                me['bet'] = total
                me['total_bet_hand'] += added
                data['pot'] += added
                data['current_bet'] = max(data['current_bet'], total)
                me['action'] = f"Raise {total}"
                me['has_acted'] = True
                # 다른 사람들 has_acted 초기화 필요 (레이즈 나왔으므로)
                for p in data['players']:
                    if p != me and p['status'] == 'alive':
                        p['has_acted'] = False
                save_game_data(data)
                next_turn(data)
                st.rerun()

    else:
        st.info(f"⏳ {data['players'][data['turn_idx']]['name']} 님 차례입니다...")
        
    if st.button("⚠️ 게임 데이터 초기화 (Reset)", use_container_width=True):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        st.session_state.clear()
        st.rerun()
