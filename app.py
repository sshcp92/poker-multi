import streamlit as st
import random
import time
import os
import json
import shutil
from collections import Counter
import streamlit.components.v1 as components

# ==========================================
# 1) 설정
# ==========================================
st.set_page_config(layout="wide", page_title="Poker Multi", page_icon="🃏")

# 블라인드
BLIND_STRUCTURE = [
    (100, 200, 0),
    (200, 400, 0),
    (300, 600, 600),
    (400, 800, 800),
    (500, 1000, 1000),
    (1000, 2000, 2000),
    (2000, 4000, 4000),
    (5000, 10000, 10000),
]
LEVEL_DURATION = 600

TURN_TIMEOUT = 30
AUTO_NEXT_HAND_DELAY = 8

# 유령플레이어 제거(강화)
DISCONNECT_TIMEOUT = 45   # 마지막 활동 기준: 이 시간 넘으면 fold + 킥 예약
KICK_AT_HAND_END = True   # True면 핸드 끝날 때 자리 비움, False면 즉시 자리 비움

# 자동 리바인(총 3엔트리: 초기 60k + 70k + 80k)
START_STACK = 60000
REBUY_STACKS = [70000, 80000]  # rebuy_count=0 -> 70k, rebuy_count=1 -> 80k

RANKS = "23456789TJQKA"
SUITS = ["♠", "♥", "♦", "♣"]
DISPLAY_MAP = {"T": "10", "J": "J", "Q": "Q", "K": "K", "A": "A"}

DATA_FILE = "poker_state_v1.json"

# ==========================================
# 2) CSS (회색 최소, 빨강/노랑 강조 + 깜빡임 최소화)
# ==========================================
st.markdown(
    """
<style>
.stApp { background-color:#0f0f0f; }
.stApp > header {visibility: hidden;}
div[data-testid="stStatusWidget"] {visibility: hidden;}
div[data-testid="stToolbar"] {visibility:hidden;}
div[data-testid="stDecoration"] {visibility:hidden;}
div[data-testid="stMarkdownContainer"] p { margin-bottom: 0.2rem; }

/* 상단 HUD */
.hud-wrap {
  width: 100%;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:10px;
  padding: 10px 12px;
  border-radius: 14px;
  border:1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.35);
}
.hud-left { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.hud-pill {
  padding: 6px 10px;
  border-radius: 999px;
  font-weight:900;
  font-size: 12px;
  border:1px solid rgba(255,0,0,0.55);
  color:#ff4d4d;
  background: rgba(0,0,0,0.55);
}
.hud-title {
  padding: 6px 10px;
  border-radius: 999px;
  font-weight:900;
  font-size: 12px;
  border:1px solid rgba(255,255,255,0.16);
  color:#eaeaea;
  background: rgba(0,0,0,0.35);
}
.hud-center {
  flex:1;
  display:flex;
  justify-content:center;
}
.table-timer-box{
  padding: 8px 16px;
  border-radius: 12px;
  background: rgba(0,0,0,0.75);
  border:1px solid rgba(255,255,255,0.14);
  color:#ffeb3b;
  font-weight:1000;
  font-size: 18px;
  letter-spacing: 1px;
  min-width: 110px;
  text-align:center;
}
.hud-right { display:flex; gap:10px; align-items:center; }

/* 게임 보드 */
.game-board-container { position:relative; width:100%; min-height:480px; height: 66vh; margin:0 auto;
  background-color:#141414; border-radius:20px; border:2px solid rgba(255,255,255,0.12); overflow:hidden; }
.poker-table { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width: 92%; height: 76%;
  background: radial-gradient(#6a3f34, #2b1713);
  border: 12px solid #1b0f0c; border-radius: 160px; box-shadow: inset 0 0 30px rgba(0,0,0,0.78); }

.seat { position:absolute; width:98px; height:112px; background:rgba(0,0,0,0.55);
  border:2px solid rgba(255,255,255,0.20); border-radius:12px; color:white;
  text-align:center; font-size:10px; display:flex; flex-direction:column; justify-content:center; align-items:center;
  z-index:10; }
.pos-0 {top:5%; right:20%;} .pos-1 {top:25%; right:3%;} .pos-2 {bottom:25%; right:3%;} .pos-3 {bottom:5%; right:20%;}
.pos-4 {bottom:2%; left:50%; transform:translateX(-50%);}
.pos-5 {bottom:5%; left:20%;} .pos-6 {bottom:25%; left:3%;} .pos-7 {top:25%; left:3%;} .pos-8 {top:5%; left:20%;}

.hero-seat { border:3px solid #ffd700; box-shadow:0 0 14px rgba(255,215,0,0.75); }
.active-turn { border:3px solid #ffeb3b !important; box-shadow:0 0 14px rgba(255,235,59,0.75); }

.winner-seat { border:3px solid #00e676 !important; box-shadow: 0 0 18px rgba(0,230,118,0.90); }
.winner-badge{
  position:absolute; top:-12px; right:-10px;
  background:#00e676; color:black; font-weight:1000;
  border-radius: 999px; padding:2px 8px; font-size:10px;
  border:1px solid rgba(0,0,0,0.7);
}

.card-span {background:white; padding:1px 4px; border-radius:4px; margin:1px;
  font-weight:1000; font-size:18px; color:black; border:1px solid #ddd; display:inline-block;}
.comm-card-span { font-size: 28px !important; padding: 3px 6px !important; }

.role-badge { position: absolute; top: -9px; left: -9px; min-width: 24px; height: 24px; padding: 0 5px;
  border-radius: 12px; color: black; font-weight: 1000; line-height: 22px; border: 1px solid rgba(0,0,0,0.65);
  z-index: 100; font-size: 11px; background:white;}
.role-D { background: #ffeb3b; }
.role-SB { background: #90caf9; }
.role-BB { background: #ef9a9a; }
.role-D-SB { background: linear-gradient(135deg, #ffeb3b 50%, #90caf9 50%); font-size: 10px; }

.action-badge { position: absolute; bottom: -12px; background:#ffeb3b; color:black; font-weight:1000; padding:1px 5px;
  border-radius:4px; font-size: 10px; border: 1px solid rgba(0,0,0,0.75); z-index:100; white-space: nowrap; }

.fold-text { color: #ff5252; font-weight: 1000; font-size: 14px; }
.folded-seat { opacity: 0.38; }

.turn-timer { position: absolute; top: -22px; width: 100%; text-align: center; color: #ffeb3b;
  font-weight:1000; font-size: 12px; background: rgba(0,0,0,0.65); border-radius: 10px; padding: 1px 0; }

.center-msg {
  position:absolute; top:46%; left:50%; transform:translate(-50%,-50%);
  text-align:center; color:white; width:100%;
}
.center-msg h3 { margin: 4px 0; font-weight: 1000; }
.center-pill {
  display:inline-block;
  font-size: 16px; color:#ffeb3b; font-weight:1000;
  background: rgba(0,0,0,0.78);
  padding: 6px 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.14);
}
.showdown-box{
  margin-top:8px;
  padding: 10px 12px;
  border-radius: 14px;
  border:1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.35);
  color:#eaeaea;
}
.showdown-title{ font-weight:1000; color:#00e676; margin-bottom:6px; }
.showdown-line{ margin: 4px 0; font-size: 14px; }
.showdown-hand{ font-weight:1000; color:#ffeb3b; }

.stButton>button { font-size: 14px !important; height: 40px !important; border-radius: 12px !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 3) 저장/로드
# ==========================================
def atomic_save(path: str, data: dict):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    shutil.move(temp, path)


def init_game_data():
    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)

    players = []
    for i in range(9):
        players.append(
            {
                "name": "빈 자리",
                "seat": i + 1,
                "stack": 0,
                "hand": [],
                "bet": 0,
                "status": "standby",  # standby/alive/folded
                "action": "",
                "is_human": False,
                "role": "",
                "has_acted": False,
                "rebuy_count": 0,  # 0~2 (rebuys used)
                "last_active": 0.0,
                "kick_pending": False,
                "is_winner": False,
            }
        )

    return {
        "players": players,
        "pot": 0,
        "deck": deck,
        "community": [],
        "phase": "WAITING",
        "current_bet": 0,
        "turn_idx": 0,
        "dealer_idx": 0,
        "sb": 100,
        "bb": 200,
        "ante": 0,
        "level": 1,
        "start_time": time.time(),
        "msg": "플레이어를 기다리는 중...",
        "turn_start_time": time.time(),
        "game_over_time": 0.0,
        "hand_log": [],
        "showdown": [],
        "max_players_seen": 0,
    }


def load_data():
    for _ in range(5):
        try:
            if not os.path.exists(DATA_FILE):
                d = init_game_data()
                atomic_save(DATA_FILE, d)
                return d
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            time.sleep(0.08)
    return init_game_data()


def save_data(data: dict):
    try:
        atomic_save(DATA_FILE, data)
    except Exception:
        pass


# ==========================================
# 4) 카드/족보
# ==========================================
def r_str(r):
    return DISPLAY_MAP.get(r, r)


def make_card(card):
    if not card or len(card) < 2:
        return "🂠"
    color = "red" if card[1] in ["♥", "♦"] else "black"
    return f"<span class='card-span' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"


def make_comm_card(card):
    if not card or len(card) < 2:
        return "🂠"
    color = "red" if card[1] in ["♥", "♦"] else "black"
    return f"<span class='card-span comm-card-span' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"


def get_hand_strength_detail(cards7):
    if not cards7 or len(cards7) < 5:
        return (-1, [], "No Hand")

    rank_map = {r: i for i, r in enumerate("..23456789TJQKA", 0)}
    ranks = sorted([rank_map[c[0]] for c in cards7], reverse=True)
    suits = [c[1] for c in cards7]

    flush_suit = None
    for s in ["♠", "♥", "♦", "♣"]:
        if suits.count(s) >= 5:
            flush_suit = s
            break
    is_flush = flush_suit is not None
    flush_ranks = (
        sorted([rank_map[c[0]] for c in cards7 if c[1] == flush_suit], reverse=True) if is_flush else []
    )

    def check_straight(unique_ranks):
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i] - unique_ranks[i + 4] == 4:
                return True, unique_ranks[i]
        if set([14, 5, 4, 3, 2]).issubset(set(unique_ranks)):
            return True, 5
        return False, -1

    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight, straight_high = check_straight(unique_ranks)

    is_sf = False
    sf_high = -1
    if is_flush:
        is_sf, sf_high = check_straight(sorted(list(set(flush_ranks)), reverse=True))

    counts = Counter(ranks)
    sorted_counts = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    def r_name(r_val):
        return r_str("..23456789TJQKA"[r_val])

    if is_sf:
        return (8, [sf_high], f"스트레이트 플러시 ({r_name(sf_high)})")
    if sorted_counts[0][1] == 4:
        kicker = [r for r in ranks if r != sorted_counts[0][0]][0]
        return (7, [sorted_counts[0][0], kicker], f"포카드 ({r_name(sorted_counts[0][0])})")
    if sorted_counts[0][1] == 3 and sorted_counts[1][1] >= 2:
        return (6, [sorted_counts[0][0], sorted_counts[1][0]], f"풀하우스 ({r_name(sorted_counts[0][0])}, {r_name(sorted_counts[1][0])})")
    if is_flush:
        return (5, flush_ranks[:5], f"플러시 ({r_name(flush_ranks[0])})")
    if is_straight:
        return (4, [straight_high], f"스트레이트 ({r_name(straight_high)})")
    if sorted_counts[0][1] == 3:
        kickers = sorted([r for r in ranks if r != sorted_counts[0][0]], reverse=True)[:2]
        return (3, [sorted_counts[0][0]] + kickers, f"트리플 ({r_name(sorted_counts[0][0])})")
    if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
        kicker = [r for r in ranks if r != sorted_counts[0][0] and r != sorted_counts[1][0]][0]
        return (2, [sorted_counts[0][0], sorted_counts[1][0], kicker], f"투페어 ({r_name(sorted_counts[0][0])}, {r_name(sorted_counts[1][0])})")
    if sorted_counts[0][1] == 2:
        kickers = sorted([r for r in ranks if r != sorted_counts[0][0]], reverse=True)[:3]
        return (1, [sorted_counts[0][0]] + kickers, f"원페어 ({r_name(sorted_counts[0][0])}) - 킥 {r_name(kickers[0])}")
    return (0, ranks[:5], f"하이카드 ({r_name(ranks[0])}, {r_name(ranks[1])})")


# ==========================================
# 5) 유틸
# ==========================================
def log_action(data, text: str):
    data["hand_log"].append(text)
    if len(data["hand_log"]) > 8:
        data["hand_log"] = data["hand_log"][-8:]


def active_players(data):
    return [p for p in data["players"] if p["name"] != "빈 자리"]


def alive_players(data):
    return [p for p in data["players"] if p["status"] == "alive"]


def find_next_alive(players, start_idx):
    for i in range(1, 10):
        idx = (start_idx + i) % 9
        if players[idx]["status"] == "alive":
            return idx
    return start_idx


def cleanup_kicked_players(data):
    for p in data["players"]:
        if p.get("kick_pending"):
            p.update(
                {
                    "name": "빈 자리",
                    "stack": 0,
                    "hand": [],
                    "bet": 0,
                    "status": "standby",
                    "action": "",
                    "is_human": False,
                    "role": "",
                    "has_acted": False,
                    "rebuy_count": 0,
                    "last_active": 0.0,
                    "kick_pending": False,
                    "is_winner": False,
                }
            )


def update_max_players_seen(data):
    curr = len([p for p in data["players"] if p["name"] != "빈 자리"])
    data["max_players_seen"] = max(int(data.get("max_players_seen", 0)), curr)


# ==========================================
# 6) 다음 핸드 준비
# ==========================================
def reset_for_next_hand(old_data):
    data = old_data
    cleanup_kicked_players(data)

    players = data["players"]
    active_idxs = [i for i, p in enumerate(players) if p["name"] != "빈 자리" and p["stack"] > 0]

    # 2명 미만이면 WAITING
    if len(active_idxs) < 2:
        data["phase"] = "WAITING"
        data["msg"] = "플레이어를 기다리는 중..."
        data["pot"] = 0
        data["community"] = []
        data["hand_log"] = []
        data["showdown"] = []
        save_data(data)
        return data

    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)

    elapsed = time.time() - data["start_time"]
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl - 1]

    # 딜러 이동
    current_d = int(data["dealer_idx"])
    new_dealer_idx = current_d
    for i in range(1, 10):
        nd = (current_d + i) % 9
        if players[nd]["name"] != "빈 자리" and players[nd]["stack"] > 0:
            new_dealer_idx = nd
            break

    # 리셋
    data["pot"] = 0
    data["community"] = []
    data["deck"] = deck
    data["current_bet"] = 0
    data["phase"] = "PREFLOP"
    data["sb"] = sb_amt
    data["bb"] = bb_amt
    data["ante"] = ante_amt
    data["level"] = lvl
    data["dealer_idx"] = new_dealer_idx
    data["turn_start_time"] = time.time()
    data["game_over_time"] = 0.0
    data["hand_log"] = []
    data["showdown"] = []

    # winner 표시 초기화
    for p in players:
        p["is_winner"] = False

    # 카드/상태 세팅 + ante
    for p in players:
        if p["name"] != "빈 자리" and p["stack"] > 0:
            p["status"] = "alive"
            p["hand"] = [deck.pop(), deck.pop()]
            p["bet"] = 0
            p["action"] = ""
            p["has_acted"] = False
            p["role"] = ""
            if ante_amt > 0:
                pay = min(p["stack"], ante_amt)
                p["stack"] -= pay
                data["pot"] += pay
        elif p["name"] != "빈 자리" and p["stack"] <= 0:
            p["status"] = "folded"
            p["hand"] = []
            p["bet"] = 0
            p["action"] = "관전"
            p["has_acted"] = True
            p["role"] = ""
        else:
            p["status"] = "standby"
            p["hand"] = []
            p["bet"] = 0
            p["action"] = ""
            p["has_acted"] = True
            p["role"] = ""

    def next_active(idx):
        for i in range(1, 10):
            j = (idx + i) % 9
            if players[j]["status"] == "alive":
                return j
        return idx

    # 헤즈업(2명): 딜러=SB
    active_alive = [i for i, p in enumerate(players) if p["status"] == "alive"]
    if len(active_alive) == 2:
        sb_idx = new_dealer_idx
        bb_idx = next_active(sb_idx)
        players[sb_idx]["role"] = "D-SB"
        players[bb_idx]["role"] = "BB"
        turn_start_idx = sb_idx
    else:
        sb_idx = next_active(new_dealer_idx)
        bb_idx = next_active(sb_idx)
        players[new_dealer_idx]["role"] = "D"
        players[sb_idx]["role"] = "SB"
        players[bb_idx]["role"] = "BB"
        turn_start_idx = next_active(bb_idx)

    # 블라인드 지불
    if players[sb_idx]["status"] == "alive":
        pay = min(players[sb_idx]["stack"], sb_amt)
        players[sb_idx]["stack"] -= pay
        players[sb_idx]["bet"] = pay
        data["pot"] += pay

    if players[bb_idx]["status"] == "alive":
        pay = min(players[bb_idx]["stack"], bb_amt)
        players[bb_idx]["stack"] -= pay
        players[bb_idx]["bet"] = pay
        data["pot"] += pay

    data["current_bet"] = bb_amt
    data["turn_idx"] = turn_start_idx
    data["msg"] = f"Level {lvl} 시작! (SB {sb_amt}/BB {bb_amt})"
    log_action(data, f"--- NEW HAND (LV {lvl}) ---")

    save_data(data)
    return data


# ==========================================
# 7) 페이즈 종료 체크 / 승부 / 다음 턴
# ==========================================
def pass_turn(data):
    players = data["players"]
    curr = int(data["turn_idx"])

    for i in range(1, 10):
        idx = (curr + i) % 9
        if players[idx]["status"] == "alive" and players[idx]["stack"] > 0:
            data["turn_idx"] = idx
            data["turn_start_time"] = time.time()
            save_data(data)
            return
        if players[idx]["status"] == "alive" and players[idx]["stack"] == 0:
            players[idx]["has_acted"] = True

    data["turn_start_time"] = time.time()
    save_data(data)


def settle_showdown(data, active_alive):
    winners = []
    best_rank = -1
    best_tie = []
    desc = ""

    # showdown 기록 초기화
    data["showdown"] = []

    for p in active_alive:
        rank_val, tie, d_text = get_hand_strength_detail(p["hand"] + data["community"])
        if rank_val > best_rank or (rank_val == best_rank and tie > best_tie):
            best_rank = rank_val
            best_tie = tie
            winners = [p]
            desc = d_text
        elif rank_val == best_rank and tie == best_tie:
            winners.append(p)

    split = data["pot"] // len(winners) if winners else 0
    for w in winners:
        w["stack"] += split
        w["is_winner"] = True

    # showdown 라인 저장(보드 아래)
    for p in active_alive:
        rank_val, tie, d_text = get_hand_strength_detail(p["hand"] + data["community"])
        hand_html = f"{make_card(p['hand'][0])}{make_card(p['hand'][1])}"
        data["showdown"].append(
            {
                "name": p["name"],
                "hand_html": hand_html,
                "desc": d_text,
                "is_winner": any(w["name"] == p["name"] for w in winners),
            }
        )

    winner_names = ", ".join([w["name"] for w in winners]) if winners else "없음"
    data["msg"] = f"WINNER: {winner_names} [{desc}]"
    log_action(data, f"SHOWDOWN: {winner_names} / {desc}")

    data["pot"] = 0
    data["phase"] = "GAME_OVER"
    data["game_over_time"] = time.time()
    save_data(data)


def check_phase_end(data):
    players = data["players"]
    alive = [p for p in players if p["status"] == "alive"]

    # 1명만 남으면 즉시 승리(폴드 승)
    if len(alive) <= 1:
        if len(alive) == 1:
            winner = alive[0]
            winner["stack"] += data["pot"]
            winner["is_winner"] = True
            data["msg"] = f"WINNER: {winner['name']} (전원 폴드)"
            log_action(data, f"WINNER: {winner['name']} (ALL FOLDED)")

            # 폴드승도 보드 아래에 카드 표시(있으면)
            data["showdown"] = []
            if winner.get("hand"):
                data["showdown"].append(
                    {
                        "name": winner["name"],
                        "hand_html": f"{make_card(winner['hand'][0])}{make_card(winner['hand'][1])}",
                        "desc": "전원 폴드 승리",
                        "is_winner": True,
                    }
                )
        data["pot"] = 0
        data["phase"] = "GAME_OVER"
        data["game_over_time"] = time.time()
        save_data(data)
        return True

    target = int(data["current_bet"])
    all_acted = all(p["has_acted"] for p in alive)
    all_matched = all((p["bet"] == target) or (p["stack"] == 0) for p in alive)

    if not (all_acted and all_matched):
        return False

    deck = data["deck"]
    if data["phase"] == "PREFLOP":
        data["phase"] = "FLOP"
        data["community"] = [deck.pop() for _ in range(3)]
        data["msg"] = "FLOP"
        log_action(data, "BOARD: FLOP")
    elif data["phase"] == "FLOP":
        data["phase"] = "TURN"
        data["community"].append(deck.pop())
        data["msg"] = "TURN"
        log_action(data, "BOARD: TURN")
    elif data["phase"] == "TURN":
        data["phase"] = "RIVER"
        data["community"].append(deck.pop())
        data["msg"] = "RIVER"
        log_action(data, "BOARD: RIVER")
    elif data["phase"] == "RIVER":
        settle_showdown(data, alive)
        return True

    # 새 스트리트 시작: bet/acted 리셋 (action은 지우지 않아서 BB 체크가 “보였다가 사라짐” 방지)
    data["current_bet"] = 0
    for p in players:
        p["bet"] = 0
        p["has_acted"] = False

    # 다음 턴: 딜러 다음 살아있는 사람
    dealer = int(data["dealer_idx"])
    nxt = None
    for i in range(1, 10):
        idx = (dealer + i) % 9
        if players[idx]["status"] == "alive" and players[idx]["stack"] > 0:
            nxt = idx
            break
    if nxt is None:
        for i in range(1, 10):
            idx = (dealer + i) % 9
            if players[idx]["status"] == "alive":
                nxt = idx
                break
    if nxt is None:
        nxt = dealer

    data["turn_idx"] = nxt
    data["turn_start_time"] = time.time()
    save_data(data)
    return True


# ==========================================
# 8) 연결 끊김/자동 리바인/아웃 처리
# ==========================================
def apply_disconnects_and_auto_rebuy(data):
    now = time.time()
    players = data["players"]
    changed = False
    turn_changed = False

    # 유령 처리
    for i, p in enumerate(players):
        if p["name"] == "빈 자리":
            continue

        last = float(p.get("last_active", 0.0))
        if last <= 0:
            continue

        if (now - last) > DISCONNECT_TIMEOUT:
            # 핸드 중이면 fold + acted 처리
            if p["status"] == "alive":
                p["status"] = "folded"
                p["has_acted"] = True
                p["action"] = "연결끊김(FOLD)"
                log_action(data, f"{p['name']} disconnected -> FOLD")
                changed = True
                if i == int(data["turn_idx"]):
                    turn_changed = True

            # 자리 비움 예약
            if KICK_AT_HAND_END and data["phase"] != "WAITING":
                p["kick_pending"] = True
                p["action"] = "퇴장(예약)"
            else:
                p["kick_pending"] = True
                changed = True

    # 자동 리바인: stack 0이면 즉시 다음 엔트리 지급(총 3엔트리)
    for p in players:
        if p["name"] == "빈 자리":
            continue

        # 이미 OUT 상태면 skip
        if p.get("kick_pending"):
            continue

        if p["stack"] <= 0:
            # rebuys 남았으면 자동지급
            if int(p.get("rebuy_count", 0)) < len(REBUY_STACKS):
                next_stack = REBUY_STACKS[int(p["rebuy_count"])]
                p["rebuy_count"] = int(p["rebuy_count"]) + 1
                p["stack"] = next_stack
                p["status"] = "folded"
                p["has_acted"] = True
                p["hand"] = []
                p["bet"] = 0
                p["action"] = f"자동리바인({next_stack:,})"
                log_action(data, f"{p['name']} AUTO REBUY -> {next_stack:,}")
                changed = True
            else:
                # 엔트리 소진 -> OUT, 자리 비움 예약
                p["action"] = "OUT"
                p["kick_pending"] = True
                log_action(data, f"{p['name']} OUT (no entries left)")
                changed = True

    if turn_changed:
        pass_turn(data)

    # 핸드가 끝났으면 킥 적용
    if data["phase"] == "GAME_OVER" or data["phase"] == "WAITING":
        cleanup_kicked_players(data)
        changed = True

    if changed:
        save_data(data)
    return changed


# ==========================================
# 9) 입장 처리
# ==========================================
if "my_seat" not in st.session_state:
    st.title("🃏 Poker Multi")
    u_name = st.text_input("닉네임", value="형님")

    c1, c2 = st.columns(2)
    if c1.button("입장하기", type="primary", use_container_width=True):
        data = load_data()

        # 이미 존재하면 그 자리로
        target = -1
        for i, p in enumerate(data["players"]):
            if p["name"] == u_name and p["name"] != "빈 자리":
                target = i
                break

        # 없으면 빈 자리 찾기 (가능하면 중앙 5번)
        if target == -1:
            if data["players"][4]["name"] == "빈 자리":
                target = 4
            else:
                for i in range(9):
                    if data["players"][i]["name"] == "빈 자리":
                        target = i
                        break

        if target != -1:
            data["players"][target] = {
                "name": u_name,
                "seat": target + 1,
                "stack": START_STACK,
                "hand": [],
                "bet": 0,
                "status": "folded",
                "action": "관전 대기",
                "is_human": True,
                "role": "",
                "has_acted": True,
                "rebuy_count": 0,
                "last_active": time.time(),
                "kick_pending": False,
                "is_winner": False,
            }
            update_max_players_seen(data)

            # 대기중인데 2명 이상이면 시작
            active_count = len([p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0])
            if data["phase"] == "WAITING" and active_count >= 2:
                data = reset_for_next_hand(data)
            save_data(data)

            st.session_state["my_seat"] = target
            st.session_state["my_name"] = u_name
            st.rerun()

    if c2.button("서버 초기화", use_container_width=True):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        st.rerun()

    st.stop()

# ==========================================
# 10) 메인 루프
# ==========================================
data = load_data()
my_seat = int(st.session_state.get("my_seat", -1))

# 자리 뺏김/초기화 대응
if my_seat < 0 or my_seat >= 9:
    st.session_state.pop("my_seat", None)
    st.session_state.pop("my_name", None)
    st.rerun()

# 내 활동시간 업데이트
me = data["players"][my_seat]
if me["name"] == st.session_state.get("my_name"):
    me["last_active"] = time.time()
    save_data(data)
else:
    st.session_state.pop("my_seat", None)
    st.session_state.pop("my_name", None)
    st.error("연결이 끊겼거나 자리를 잃었습니다. 다시 입장해주세요.")
    st.stop()

# 연결끊김/자동리바인/아웃 처리
if apply_disconnects_and_auto_rebuy(data):
    data = load_data()

update_max_players_seen(data)

# 서버 타임아웃 처리(턴 시간 초과)
curr_idx = int(data["turn_idx"])
curr_p = data["players"][curr_idx]

if data["phase"] not in ["WAITING", "GAME_OVER"]:
    time_left = max(0, TURN_TIMEOUT - (time.time() - float(data["turn_start_time"])))
    if time_left <= 0:
        if curr_p["status"] == "alive":
            data = load_data()
            curr_p = data["players"][curr_idx]
            curr_p["status"] = "folded"
            curr_p["has_acted"] = True
            curr_p["action"] = "시간초과(FOLD)"
            log_action(data, f"{curr_p['name']} TIMEOUT -> FOLD")
            if not check_phase_end(data):
                pass_turn(data)
            save_data(data)
            data = load_data()

# WAITING
if data["phase"] == "WAITING":
    # 상단 HUD만 보여주고 2초마다만 갱신
    elapsed = time.time() - float(data["start_time"])
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb, bb, ante = BLIND_STRUCTURE[lvl - 1]
    alive_p = [p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0]
    avg_stack = (sum(int(p["stack"]) for p in alive_p) // len(alive_p)) if alive_p else 0

    current_players = len([p for p in data["players"] if p["name"] != "빈 자리"])
    denom = max(int(data.get("max_players_seen", current_players)), current_players) if current_players > 0 else int(data.get("max_players_seen", 0))
    if denom <= 0:
        denom = current_players if current_players > 0 else 0

    remain = int(LEVEL_DURATION - (elapsed % LEVEL_DURATION))
    mm, ss = remain // 60, remain % 60

    hud = f"""
    <div class="hud-wrap">
      <div class="hud-left">
        <span class="hud-title">LV {lvl}</span>
        <span class="hud-title">Players {current_players}/{denom}</span>
        <span class="hud-pill">SB {sb}</span>
        <span class="hud-pill">BB {bb}</span>
        <span class="hud-pill">Ante {ante}</span>
        <span class="hud-pill">Avg {avg_stack:,}</span>
      </div>
      <div class="hud-center">
        <div class="table-timer-box">{mm:02d}:{ss:02d}</div>
      </div>
      <div class="hud-right"></div>
    </div>
    """
    st.markdown(hud, unsafe_allow_html=True)

    st.info("다른 플레이어 입장을 기다리는 중입니다. (최소 2명)")

    # 테이블만 보여주기
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    for i in range(9):
        p = data["players"][i]
        if p["name"] == "빈 자리":
            html += f'<div class="seat pos-{i}" style="opacity:0.18;"><div>빈 자리</div></div>'
        else:
            hero = "hero-seat" if i == my_seat else ""
            html += f'<div class="seat pos-{i} {hero}"><div><b>{p["name"]}</b></div><div>{int(p["stack"]):,}</div></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    # 2초마다 갱신(깜빡임 최소)
    components.html(
        """
        <script>
        setTimeout(()=>{ window.parent.postMessage({type:'streamlit:rerun'}, '*'); }, 2000);
        </script>
        """,
        height=0,
    )
    st.stop()

# GAME_OVER (자동 다음판)
if data["phase"] == "GAME_OVER":
    rem = int(AUTO_NEXT_HAND_DELAY - (time.time() - float(data["game_over_time"])))
    if rem <= 0:
        data = reset_for_next_hand(data)
        st.rerun()

# ==========================================
# 11) HUD 렌더 (상단 한 번만)
# ==========================================
elapsed = time.time() - float(data["start_time"])
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl - 1]

alive_p = [p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0]
avg_stack = (sum(int(p["stack"]) for p in alive_p) // len(alive_p)) if alive_p else 0

current_players = len([p for p in data["players"] if p["name"] != "빈 자리"])
denom = max(int(data.get("max_players_seen", current_players)), current_players)
remain = int(LEVEL_DURATION - (elapsed % LEVEL_DURATION))
mm, ss = remain // 60, remain % 60

hud = f"""
<div class="hud-wrap">
  <div class="hud-left">
    <span class="hud-title">LV {lvl}</span>
    <span class="hud-title">Players {current_players}/{denom}</span>
    <span class="hud-pill">SB {sb}</span>
    <span class="hud-pill">BB {bb}</span>
    <span class="hud-pill">Ante {ante}</span>
    <span class="hud-pill">Avg {avg_stack:,}</span>
  </div>
  <div class="hud-center">
    <div class="table-timer-box">{mm:02d}:{ss:02d}</div>
  </div>
  <div class="hud-right"></div>
</div>
"""
st.markdown(hud, unsafe_allow_html=True)

# ==========================================
# 12) 화면 본체
# ==========================================
col_table, col_controls = st.columns([1.5, 1], gap="large")

with col_table:
    # 커뮤니티 카드
    comm = "".join([make_comm_card(c) for c in data["community"]])

    # 턴 타이머(좌석 위 작은 박스)
    if data["phase"] not in ["WAITING", "GAME_OVER"]:
        turn_left = max(0, TURN_TIMEOUT - (time.time() - float(data["turn_start_time"])))
    else:
        turn_left = 0

    html = '<div class="game-board-container"><div class="poker-table"></div>'

    for i in range(9):
        p = data["players"][i]
        if p["name"] == "빈 자리":
            html += f'<div class="seat pos-{i}" style="opacity:0.18;"><div>빈 자리</div></div>'
            continue

        active = "active-turn" if i == curr_idx and data["phase"] not in ["WAITING", "GAME_OVER"] else ""
        hero = "hero-seat" if i == my_seat else ""
        folded_cls = "folded-seat" if p["status"] == "folded" else ""
        winner_cls = "winner-seat" if p.get("is_winner") else ""
        winner_badge = "<div class='winner-badge'>WINNER</div>" if p.get("is_winner") else ""

        timer_html = ""
        if i == curr_idx and data["phase"] not in ["WAITING", "GAME_OVER"]:
            timer_html = f"<div class='turn-timer'>{int(turn_left)}s</div>"

        # 카드 표시: 내 자리 or 게임오버 때 남은 사람 공개
        cards = "<div style='font-size:16px;'>🂠 🂠</div>"
        if p["status"] == "folded":
            cards = "<div class='fold-text'>FOLD</div>"
        else:
            if i == my_seat or (data["phase"] == "GAME_OVER"):
                if p.get("hand"):
                    cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
                else:
                    cards = ""

        role = p.get("role", "")
        role_cls = "role-D-SB" if role == "D-SB" else f"role-{role}"
        role_div = f"<div class='role-badge {role_cls}'>{role}</div>" if role else ""

        action_text = p.get("action", "")
        if not action_text:
            action_text = " "

        html += (
            f"<div class='seat pos-{i} {active} {hero} {folded_cls} {winner_cls}'>"
            f"{timer_html}{role_div}{winner_badge}"
            f"<div><b>{p['name']}</b></div>"
            f"<div>{int(p['stack']):,}</div>"
            f"{cards}"
            f"<div class='action-badge'>{action_text}</div>"
            f"</div>"
        )

    # 중앙 메시지 + 핸드로그(최근 3개)
    log_lines = data.get("hand_log", [])[-3:]
    log_html = ""
    if log_lines:
        log_html = "<div style='margin-top:6px; font-size:12px; color:#cfcfcf;'>" + "<br/>".join(log_lines) + "</div>"

    msg_html = (
        "<div class='center-msg'>"
        f"<div>{comm}</div>"
        f"<h3>Pot: {int(data['pot']):,}</h3>"
        f"<div class='center-pill'>{data['msg']}</div>"
        f"{log_html}"
        "</div>"
    )
    html += msg_html + "</div>"
    st.markdown(html, unsafe_allow_html=True)

    # 보드 아래: 쇼다운 결과 박스
    if data.get("showdown"):
        sbox = "<div class='showdown-box'>"
        sbox += "<div class='showdown-title'>SHOWDOWN</div>"
        for row in data["showdown"]:
            badge = " ✅" if row.get("is_winner") else ""
            sbox += (
                f"<div class='showdown-line'>"
                f"<span style='font-weight:1000; color:#eaeaea;'>{row['name']}{badge}</span> "
                f"<span style='margin-left:6px;'>{row['hand_html']}</span> "
                f"<span class='showdown-hand' style='margin-left:10px;'>{row['desc']}</span>"
                f"</div>"
            )
        sbox += "</div>"
        st.markdown(sbox, unsafe_allow_html=True)

with col_controls:
    me = data["players"][my_seat]

    # 컨트롤 기본 표시
    if data["phase"] == "GAME_OVER":
        st.info("게임 종료! 다음 판 준비 중...")
    else:
        # 내 카드
        st.markdown("### 내 카드")
        if me.get("hand"):
            st.markdown(f"{make_card(me['hand'][0])}{make_card(me['hand'][1])}", unsafe_allow_html=True)

        # 내 차례 여부
        if curr_idx == my_seat and me["status"] == "alive":
            # 내 차례
            tleft = max(0, TURN_TIMEOUT - (time.time() - float(data["turn_start_time"])))
            st.success(f"내 차례! ({int(tleft)}초)")

            to_call = int(data["current_bet"]) - int(me["bet"])
            to_call = max(0, to_call)

            c1, c2 = st.columns(2)
            check_label = "체크/콜"
            if data["phase"] == "PREFLOP" and to_call == 0 and ("BB" in me.get("role", "") or "SB" in me.get("role", "")):
                check_label = "체크 (옵션)"

            if c1.button(check_label, use_container_width=True):
                data = load_data()
                me = data["players"][my_seat]
                pay = min(to_call, int(me["stack"]))
                me["stack"] = int(me["stack"]) - pay
                me["bet"] = int(me["bet"]) + pay
                data["pot"] = int(data["pot"]) + pay
                me["has_acted"] = True
                me["action"] = "체크" if pay == 0 else f"콜({pay})"
                log_action(data, f"{me['name']}: {me['action']}")

                if not check_phase_end(data):
                    pass_turn(data)
                save_data(data)
                st.rerun()

            if c2.button("폴드", type="primary", use_container_width=True):
                data = load_data()
                me = data["players"][my_seat]
                me["status"] = "folded"
                me["has_acted"] = True
                me["action"] = "폴드"
                log_action(data, f"{me['name']}: FOLD")

                if not check_phase_end(data):
                    pass_turn(data)
                save_data(data)
                st.rerun()

            if st.button("ALL-IN", use_container_width=True):
                data = load_data()
                me = data["players"][my_seat]
                pay = int(me["stack"])
                me["stack"] = 0
                me["bet"] = int(me["bet"]) + pay
                data["pot"] = int(data["pot"]) + pay
                me["has_acted"] = True
                me["action"] = f"올인({pay})"
                log_action(data, f"{me['name']}: ALL-IN({pay})")

                if int(me["bet"]) > int(data["current_bet"]):
                    data["current_bet"] = int(me["bet"])
                    # 레이즈가 생기면 다른 사람 acted 리셋
                    for p in data["players"]:
                        if p is not me and p["status"] == "alive" and p["stack"] > 0:
                            p["has_acted"] = False

                if not check_phase_end(data):
                    pass_turn(data)
                save_data(data)
                st.rerun()

            st.markdown("---")

            # 레이즈 기본값을 "항상 최소 레이즈"로
            # 최소 레이즈 = max( current_bet*2, current_bet + (current_bet - me.bet) ) 같은 단순화 대신
            # 여기서는 사용자가 원하는 "현재 베팅의 2배" 규칙 기반으로 세팅
            min_raise_to = max(200, int(data["current_bet"]) * 2)
            max_raise_to = int(me["stack"]) + int(me["bet"])

            if max_raise_to >= min_raise_to and int(me["stack"]) > to_call:
                step_val = 1000 if sb >= 1000 else 100

                raise_to = st.number_input(
                    "레이즈/베팅 (총액 기준)",
                    min_value=int(min_raise_to),
                    max_value=int(max_raise_to),
                    value=int(min_raise_to),
                    step=int(step_val),
                )

                if st.button("레이즈 확정", use_container_width=True):
                    data = load_data()
                    me = data["players"][my_seat]

                    raise_to = int(raise_to)
                    pay = raise_to - int(me["bet"])
                    pay = max(0, pay)
                    pay = min(pay, int(me["stack"]))

                    me["stack"] = int(me["stack"]) - pay
                    me["bet"] = int(me["bet"]) + pay
                    data["pot"] = int(data["pot"]) + pay
                    data["current_bet"] = int(me["bet"])

                    me["has_acted"] = True
                    me["action"] = f"레이즈({int(me['bet'])})"
                    log_action(data, f"{me['name']}: RAISE({int(me['bet'])})")

                    for p in data["players"]:
                        if p is not me and p["status"] == "alive" and p["stack"] > 0:
                            p["has_acted"] = False

                    if not check_phase_end(data):
                        pass_turn(data)
                    save_data(data)
                    st.rerun()
            else:
                st.info("현재 스택으로 레이즈 불가")

        elif me["status"] == "folded":
            st.warning("관전 중... (다음 액션 대기)")
        else:
            # 상대 턴
            if data["phase"] not in ["WAITING", "GAME_OVER"]:
                tleft = max(0, TURN_TIMEOUT - (time.time() - float(data["turn_start_time"])))
                st.info(f"{curr_p['name']} 대기 중... ({int(tleft)}s)")
            else:
                st.info("대기 중...")

    # 서버 초기화 버튼
    st.markdown("---")
    if st.button("서버 초기화", use_container_width=True):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        st.rerun()

# ==========================================
# 13) 자동 새로고침 (2초)
#     - 1초마다 전체 rerun 하지 않아서 깜빡임 크게 줄어듦
# ==========================================
components.html(
    """
    <script>
    setTimeout(()=>{ window.parent.postMessage({type:'streamlit:rerun'}, '*'); }, 2000);
    </script>
    """,
    height=0,
)
