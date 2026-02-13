import streamlit as st
import random
import time
import os
import json
import sqlite3
import itertools
from contextlib import contextmanager
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트 - FINAL", page_icon="🦁")

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
AUTO_NEXT_HAND_DELAY = 10

# ✅ 올인/잠깐 탭 전환에 튕기지 않게 여유
DISCONNECT_TIMEOUT = 90

RANKS = "23456789TJQKA"
SUITS = ["♠", "♥", "♦", "♣"]
DISPLAY_MAP = {"T": "10", "J": "J", "Q": "Q", "K": "K", "A": "A"}

DB_FILE = "poker_state.db"
GAME_ID = "MAIN"

# ---------------- CSS ----------------
st.markdown(
    """<style>
.stApp {background-color:#121212;}
div[data-testid="stStatusWidget"] {visibility: hidden;}
.stApp > header {visibility: hidden;}

.top-hud { display:flex; justify-content:space-between; align-items:center;
  background:#333; padding:10px 12px; border-radius:12px; margin-bottom:8px;
  border:1px solid #555; color:white; font-weight:800; font-size:13px; gap:10px; }
.hud-left, .hud-mid, .hud-right { display:flex; align-items:center; gap:10px; }
.hud-badge { background:#1f1f1f; border:1px solid #666; padding:6px 10px; border-radius:10px; }
.hud-time { color:#ffeb3b; font-size:18px; font-weight:900; }

.game-board-container { position:relative; width:100%; min-height:450px; height:65vh; margin:0 auto;
  background-color:#1e1e1e; border-radius:20px; border:3px solid #333; overflow:hidden; }
.poker-table { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  width:92%; height:75%; background: radial-gradient(#5d4037, #3e2723);
  border:12px solid #281915; border-radius:150px; box-shadow: inset 0 0 30px rgba(0,0,0,0.8); }

.seat { position:absolute; width:95px; height:110px; background:#2c2c2c; border:2px solid #666; border-radius:12px;
  color:white; text-align:center; font-size:10px; display:flex; flex-direction:column; justify-content:center; align-items:center; z-index:10; }
.pos-0 {top:5%; right:20%;} .pos-1 {top:25%; right:3%;} .pos-2 {bottom:25%; right:3%;} .pos-3 {bottom:5%; right:20%;}
.pos-4 {bottom:2%; left:50%; transform:translateX(-50%);}
.pos-5 {bottom:5%; left:20%;} .pos-6 {bottom:25%; left:3%;} .pos-7 {top:25%; left:3%;} .pos-8 {top:5%; left:20%;}

.hero-seat { border:3px solid #ffd700; background:#3a3a3a; box-shadow:0 0 15px #ffd700; z-index:20; }
.active-turn { border:3px solid #ffeb3b !important; box-shadow:0 0 15px #ffeb3b; }

.card-span {background:white; padding:1px 4px; border-radius:4px; margin:1px; font-weight:bold; font-size:18px; color:black; border:1px solid #ccc; display:inline-block;}
.comm-card-span { font-size:28px !important; padding:3px 6px !important; }

.role-badge { position:absolute; top:-8px; left:-8px; min-width:24px; height:24px; padding:0 4px; border-radius:12px; color:black;
  font-weight:bold; line-height:22px; border:1px solid #333; z-index:100; font-size:11px; background:white; }
.role-D { background:#ffeb3b; } .role-SB { background:#90caf9; } .role-BB { background:#ef9a9a; }
.role-D-SB { background: linear-gradient(135deg, #ffeb3b 50%, #90caf9 50%); font-size:10px; }

.action-badge { position:absolute; bottom:-12px; background:#ffeb3b; color:black; font-weight:bold; padding:1px 5px; border-radius:4px;
  font-size:10px; border:1px solid #000; z-index:100; white-space:nowrap; }
.fold-text { color:#ff5252; font-weight:bold; font-size:14px; }
.folded-seat { opacity:0.4; }
.turn-timer { position:absolute; top:-20px; width:100%; text-align:center; color:#ff5252; font-weight:bold; font-size:12px; }

.winner-seat { border:3px solid #00e676 !important; box-shadow:0 0 18px #00e676 !important; }
.winner-badge { position:absolute; top:-16px; right:-10px; background:#00e676; color:black; font-weight:900; font-size:10px;
  padding:2px 6px; border-radius:10px; border:1px solid #0b3d1a; z-index:120; }

.center-msg { position:absolute; top:45%; left:50%; transform:translate(-50%,-50%); text-align:center; color:white; width:100%; }
.center-msg h3 { margin:0; }
.center-msg .msgline { font-size:18px; color:#ffeb3b; font-weight:bold; background:rgba(0,0,0,0.7); padding:6px 8px; border-radius:6px; display:inline-block; }
.center-msg .showdown { margin-top:10px; font-size:14px; color:#b2ff59; font-weight:900; }
.center-msg .sdrow { margin-top:6px; color:#e0e0e0; font-weight:800; font-size:13px; }
.center-msg .sdrow b { color:#b2ff59; }
</style>""",
    unsafe_allow_html=True,
)

# ---------------- DB helpers ----------------
def db_connect():
    conn = sqlite3.connect(DB_FILE, timeout=5, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def db_init():
    conn = db_connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_state (
            game_id TEXT PRIMARY KEY,
            version INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.close()

@contextmanager
def db_tx():
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.close()

def db_get_state(conn):
    row = conn.execute(
        "SELECT version, state_json FROM game_state WHERE game_id=?", (GAME_ID,)
    ).fetchone()
    if not row:
        s = init_game_data()
        conn.execute(
            "INSERT INTO game_state(game_id, version, state_json, updated_at) VALUES(?,?,?,?)",
            (GAME_ID, 1, json.dumps(s, ensure_ascii=False), time.time()),
        )
        return 1, s
    v, sjson = row
    return v, json.loads(sjson)

def db_set_state(conn, version, state):
    conn.execute(
        "UPDATE game_state SET version=?, state_json=?, updated_at=? WHERE game_id=?",
        (version, json.dumps(state, ensure_ascii=False), time.time(), GAME_ID),
    )

def atomic_update(mutator_fn):
    with db_tx() as conn:
        v, s = db_get_state(conn)
        s2 = mutator_fn(s) or s
        db_set_state(conn, v + 1, s2)
        return v + 1, s2

def load_state_readonly():
    conn = db_connect()
    try:
        row = conn.execute(
            "SELECT state_json FROM game_state WHERE game_id=?", (GAME_ID,)
        ).fetchone()
        if not row:
            with db_tx() as conn2:
                _, s = db_get_state(conn2)
            return s
        return json.loads(row[0])
    finally:
        conn.close()

# ---------------- 카드 표시 ----------------
def r_str(r): return DISPLAY_MAP.get(r, r)

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

# ---------------- 핸드 평가 ----------------
RANK_MAP = {r: i for i, r in enumerate("..23456789TJQKA", 0)}

def eval_5(cards5):
    ranks = sorted([RANK_MAP[c[0]] for c in cards5], reverse=True)
    suits = [c[1] for c in cards5]

    from collections import Counter
    counts = Counter(ranks)
    items = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    is_flush = len(set(suits)) == 1
    uniq = sorted(set(ranks), reverse=True)

    def straight_high(ur):
        if len(ur) != 5:
            return -1
        if ur[0] - ur[4] == 4:
            return ur[0]
        if set([14, 5, 4, 3, 2]) == set(ur):
            return 5
        return -1

    sh = straight_high(uniq)
    is_straight = (sh != -1)

    def r_name(v): return r_str("..23456789TJQKA"[v])

    if is_flush and is_straight:
        return (8, [sh], f"스트레이트 플러시 ({r_name(sh)})")
    if items[0][1] == 4:
        quad = items[0][0]
        kicker = max([r for r in ranks if r != quad])
        return (7, [quad, kicker], f"포카드 ({r_name(quad)})")
    if items[0][1] == 3 and items[1][1] == 2:
        trip = items[0][0]; pair = items[1][0]
        return (6, [trip, pair], f"풀하우스 ({r_name(trip)}, {r_name(pair)})")
    if is_flush:
        return (5, ranks, f"플러시 ({r_name(ranks[0])})")
    if is_straight:
        return (4, [sh], f"스트레이트 ({r_name(sh)})")
    if items[0][1] == 3:
        trip = items[0][0]
        kickers = sorted([r for r in ranks if r != trip], reverse=True)
        return (3, [trip] + kickers, f"트리플 ({r_name(trip)})")
    if items[0][1] == 2 and items[1][1] == 2:
        p1 = items[0][0]; p2 = items[1][0]
        kicker = max([r for r in ranks if r != p1 and r != p2])
        hi, lo = max(p1, p2), min(p1, p2)
        return (2, [hi, lo, kicker], f"투페어 ({r_name(hi)}, {r_name(lo)})")
    if items[0][1] == 2:
        pair = items[0][0]
        kickers = sorted([r for r in ranks if r != pair], reverse=True)
        return (1, [pair] + kickers, f"원페어 ({r_name(pair)})")
    return (0, ranks, f"하이카드 ({r_name(ranks[0])})")

def best_of_7(cards7):
    best = (-1, [], "No Hand")
    for comb in itertools.combinations(cards7, 5):
        rankv, tieb, desc = eval_5(list(comb))
        if rankv > best[0] or (rankv == best[0] and tieb > best[1]):
            best = (rankv, tieb, desc)
    return best

# ---------------- 게임 상태 ----------------
def init_players():
    ps = []
    for i in range(9):
        ps.append({
            "name": "빈 자리",
            "seat": i + 1,
            "stack": 0,
            "hand": [],
            "bet": 0,
            "contrib": 0,
            "status": "standby",
            "action": "",
            "is_human": False,
            "role": "",
            "has_acted": False,
            "rebuy_count": 0,
            "last_active": 0,
        })
    return ps

def new_deck():
    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck

def init_game_data():
    return {
        "players": init_players(),
        "pot": 0,
        "deck": new_deck(),
        "community": [],
        "phase": "WAITING",
        "current_bet": 0,
        "last_raise_size": 0,
        "turn_idx": 0,
        "dealer_idx": 0,
        "sb": 100,
        "bb": 200,
        "ante": 0,
        "level": 1,
        "start_time": time.time(),
        "msg": "플레이어를 기다리는 중...",
        "turn_start_time": time.time(),
        "game_over_time": 0,
        "hand_id": 0,
        "showdown": None,
        "winner_seats": [],
        "last_action_note": "",  # ✅ 직전 액션 표시용
    }

def occupied_players(players):
    # ✅ 자리 점유자(게임 참가자): 이름이 있으면 참가자로 봄
    return [p for p in players if p["name"] != "빈 자리"]

def in_hand_players(players):
    # ✅ 핸드 진행 중 참가자: alive/folded 포함(올인 stack=0도 alive임)
    return [p for p in players if p["name"] != "빈 자리" and p["status"] in ("alive", "folded")]

def find_next_alive(players, idx):
    for i in range(1, 10):
        j = (idx + i) % 9
        if players[j]["status"] == "alive":
            return j
    return idx

def apply_blinds_and_antes(data):
    players = data["players"]
    elapsed = time.time() - data["start_time"]
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl - 1]
    data["level"], data["sb"], data["bb"], data["ante"] = lvl, sb_amt, bb_amt, ante_amt

    data["deck"] = new_deck()
    data["community"] = []
    data["pot"] = 0
    data["current_bet"] = 0
    data["last_raise_size"] = bb_amt
    data["hand_id"] += 1
    data["showdown"] = None
    data["winner_seats"] = []
    data["last_action_note"] = ""

    for p in players:
        p["bet"] = 0
        p["contrib"] = 0
        p["has_acted"] = False
        p["action"] = ""
        p["role"] = ""
        if p["name"] == "빈 자리" or p["stack"] <= 0:
            p["status"] = "standby"
            p["hand"] = []
        else:
            p["status"] = "alive"
            p["hand"] = [data["deck"].pop(), data["deck"].pop()]

    if ante_amt > 0:
        for p in players:
            if p["status"] == "alive":
                pay = min(p["stack"], ante_amt)
                p["stack"] -= pay
                p["contrib"] += pay
                data["pot"] += pay

def assign_positions_and_post_blinds(data):
    players = data["players"]
    alive = [i for i, p in enumerate(players) if p["status"] == "alive"]
    if len(alive) < 2:
        data["phase"] = "WAITING"
        data["msg"] = "플레이어를 기다리는 중..."
        return

    cur_d = data["dealer_idx"]
    for i in range(1, 10):
        nd = (cur_d + i) % 9
        if players[nd]["status"] == "alive":
            data["dealer_idx"] = nd
            break

    def next_alive(i): return find_next_alive(players, i)

    if len(alive) == 2:
        sb_i = data["dealer_idx"]
        bb_i = next_alive(sb_i)
        players[sb_i]["role"] = "D-SB"
        players[bb_i]["role"] = "BB"
        turn_start = sb_i
    else:
        d = data["dealer_idx"]
        sb_i = next_alive(d)
        bb_i = next_alive(sb_i)
        players[d]["role"] = "D"
        players[sb_i]["role"] = "SB"
        players[bb_i]["role"] = "BB"
        turn_start = next_alive(bb_i)

    sb_amt, bb_amt = data["sb"], data["bb"]
    if players[sb_i]["status"] == "alive":
        pay = min(players[sb_i]["stack"], sb_amt)
        players[sb_i]["stack"] -= pay
        players[sb_i]["bet"] += pay
        players[sb_i]["contrib"] += pay
        data["pot"] += pay

    if players[bb_i]["status"] == "alive":
        pay = min(players[bb_i]["stack"], bb_amt)
        players[bb_i]["stack"] -= pay
        players[bb_i]["bet"] += pay
        players[bb_i]["contrib"] += pay
        data["pot"] += pay

    data["current_bet"] = bb_amt
    data["last_raise_size"] = bb_amt
    data["turn_idx"] = turn_start
    data["turn_start_time"] = time.time()
    data["phase"] = "PREFLOP"
    data["msg"] = f"Level {data['level']} 시작! (SB {sb_amt}/BB {bb_amt})"

def reset_for_next_hand(data):
    # ✅ 참가자(자리 점유)가 2명 이상이면 시작
    occ = [p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0]
    if len(occ) < 2:
        data["phase"] = "WAITING"
        data["msg"] = "플레이어를 기다리는 중..."
        return data
    apply_blinds_and_antes(data)
    assign_positions_and_post_blinds(data)
    return data

# ---------------- 사이드팟 ----------------
def build_side_pots(pool):
    contribs = [(i, p["contrib"]) for i, p in pool if p["contrib"] > 0]
    if not contribs:
        return []
    levels = sorted(set([c for _, c in contribs]))
    pots = []
    prev = 0
    for lv in levels:
        layer = lv - prev
        elig = [i for i, c in contribs if c >= lv]
        amt = layer * len(elig)
        if amt > 0:
            pots.append({"amount": amt, "eligible": elig})
        prev = lv
    return pots

def distribute_odd_chips(pot_amount, winners, dealer_idx):
    if not winners:
        return {}
    base = pot_amount // len(winners)
    rem = pot_amount % len(winners)
    res = {w: base for w in winners}
    if rem > 0:
        order = []
        for k in range(1, 10):
            i = (dealer_idx + k) % 9
            if i in winners:
                order.append(i)
            if len(order) == len(winners):
                break
        for t in range(rem):
            res[order[t % len(order)]] += 1
    return res

# ---------------- 페이즈/쇼다운 ----------------
def all_in_or_matched(data):
    active = [p for p in data["players"] if p["status"] == "alive"]
    if len(active) <= 1:
        return True
    target = data["current_bet"]
    all_acted = all(p["has_acted"] or p["stack"] == 0 for p in active)
    all_matched = all((p["bet"] == target) or (p["stack"] == 0) for p in active)
    return all_acted and all_matched

def next_street(data):
    deck = data["deck"]
    if data["phase"] == "PREFLOP":
        data["phase"] = "FLOP"
        data["community"] = [deck.pop(), deck.pop(), deck.pop()]
    elif data["phase"] == "FLOP":
        data["phase"] = "TURN"
        data["community"].append(deck.pop())
    elif data["phase"] == "TURN":
        data["phase"] = "RIVER"
        data["community"].append(deck.pop())

    data["current_bet"] = 0
    data["last_raise_size"] = data["bb"]
    for p in data["players"]:
        p["bet"] = 0
        p["has_acted"] = False

    d = data["dealer_idx"]
    data["turn_idx"] = find_next_alive(data["players"], d)
    data["turn_start_time"] = time.time()

    # ✅ 직전 액션을 메시지에 남겨서 "BB 체크하고 플랍 열림"이 보이게
    note = data.get("last_action_note", "")
    if note:
        data["msg"] = f"{data['phase']} 시작! (이전: {note})"
    else:
        data["msg"] = f"{data['phase']} 시작!"

def pass_turn(data):
    curr = data["turn_idx"]
    players = data["players"]
    for i in range(1, 10):
        idx = (curr + i) % 9
        if players[idx]["status"] == "alive":
            if players[idx]["stack"] == 0:
                players[idx]["has_acted"] = True
                continue
            data["turn_idx"] = idx
            data["turn_start_time"] = time.time()
            return
    data["turn_start_time"] = time.time()

def showdown(data):
    players = data["players"]
    alive = [(i, p) for i, p in enumerate(players) if p["status"] == "alive"]

    if len(alive) == 1:
        wi, wp = alive[0]
        wp["stack"] += data["pot"]
        data["winner_seats"] = [wi]
        data["showdown"] = {
            "winners": [{
                "seat": wi,
                "name": wp["name"],
                "hand": wp["hand"],
                "desc": "전원 폴드 승리",
            }],
            "board": data["community"],
            "pot": data["pot"],
        }
        data["msg"] = f"🏆 {wp['name']} 승리! (전원 폴드)"
        data["pot"] = 0
        data["phase"] = "GAME_OVER"
        data["game_over_time"] = time.time()
        return

    pool = [(i, p) for i, p in enumerate(players) if p["name"] != "빈 자리" and p["contrib"] > 0]
    pots = build_side_pots(pool)
    eval_cache = {i: best_of_7(p["hand"] + data["community"]) for i, p in alive}

    rep = None  # (amount, winners, desc)
    for pot in pots:
        elig_alive = [i for i in pot["eligible"] if players[i]["status"] == "alive"]
        if not elig_alive:
            continue

        best_rank = (-1, [])
        winners = []
        desc = ""
        for i in elig_alive:
            rankv, tieb, dtext = eval_cache[i]
            if rankv > best_rank[0] or (rankv == best_rank[0] and tieb > best_rank[1]):
                best_rank = (rankv, tieb)
                winners = [i]
                desc = dtext
            elif rankv == best_rank[0] and tieb == best_rank[1]:
                winners.append(i)

        dist = distribute_odd_chips(pot["amount"], winners, data["dealer_idx"])
        for wi, amt in dist.items():
            players[wi]["stack"] += amt

        if rep is None or pot["amount"] > rep[0]:
            rep = (pot["amount"], winners, desc)

    if rep:
        winners = rep[1]
        desc = rep[2]
        data["winner_seats"] = winners[:]
        data["showdown"] = {
            "winners": [{
                "seat": i,
                "name": players[i]["name"],
                "hand": players[i]["hand"],
                "desc": desc
            } for i in winners],
            "board": data["community"],
            "pot": data["pot"],
        }
        wn = ", ".join(players[i]["name"] for i in winners)
        data["msg"] = f"🏆 {wn} 승리! [{desc}]"
    else:
        data["winner_seats"] = []
        data["showdown"] = None
        data["msg"] = "🏆 승부 처리 완료"

    data["pot"] = 0
    data["phase"] = "GAME_OVER"
    data["game_over_time"] = time.time()

def check_phase_end_and_advance(data):
    alive = [p for p in data["players"] if p["status"] == "alive"]
    if len(alive) <= 1:
        showdown(data)
        return True

    if all_in_or_matched(data):
        if data["phase"] == "RIVER":
            showdown(data)
            return True

        active_with_stack = [p for p in alive if p["stack"] > 0]
        if len(active_with_stack) == 0:
            while data["phase"] != "RIVER":
                next_street(data)
            showdown(data)
            return True
        else:
            next_street(data)
            return True
    return False

# ---------------- 액션 ----------------
def set_last_action(data, pname, action_text):
    data["last_action_note"] = f"{pname} {action_text}"

def do_fold(data, seat):
    p = data["players"][seat]
    if p["status"] != "alive":
        return
    p["status"] = "folded"
    p["has_acted"] = True
    p["action"] = "폴드"
    set_last_action(data, p["name"], "폴드")

def do_call_or_check(data, seat):
    p = data["players"][seat]
    if p["status"] != "alive":
        return
    to_call = max(0, data["current_bet"] - p["bet"])
    pay = min(to_call, p["stack"])
    p["stack"] -= pay
    p["bet"] += pay
    p["contrib"] += pay
    data["pot"] += pay
    p["has_acted"] = True

    # ✅ BB 옵션 체크는 문구를 구분
    if pay == 0 and data["phase"] == "PREFLOP" and ("BB" in p.get("role", "") or p.get("role") == "BB"):
        p["action"] = "체크(옵션)"
        set_last_action(data, p["name"], "체크(옵션)")
    else:
        p["action"] = "체크" if pay == 0 else "콜"
        set_last_action(data, p["name"], p["action"])

def do_allin(data, seat):
    p = data["players"][seat]
    if p["status"] != "alive":
        return
    pay = p["stack"]
    p["stack"] = 0
    p["bet"] += pay
    p["contrib"] += pay
    data["pot"] += pay
    p["has_acted"] = True
    p["action"] = "올인!"
    set_last_action(data, p["name"], "올인!")

    if p["bet"] > data["current_bet"]:
        raise_size = p["bet"] - data["current_bet"]
        data["last_raise_size"] = max(data["last_raise_size"], raise_size)
        data["current_bet"] = p["bet"]
        for q in data["players"]:
            if q is not p and q["status"] == "alive" and q["stack"] > 0:
                q["has_acted"] = False

def do_raise_to(data, seat, raise_to):
    p = data["players"][seat]
    if p["status"] != "alive":
        return False, "이미 액션 불가 상태"

    if data["current_bet"] == 0:
        min_to = data["bb"]
    else:
        min_to = data["current_bet"] + data["last_raise_size"]

    max_to = p["bet"] + p["stack"]
    if raise_to > max_to:
        return False, "레이즈 금액이 보유 칩을 초과"
    if raise_to < min_to and raise_to != max_to:
        return False, f"최소 레이즈는 {min_to} (올인은 예외)"

    pay = raise_to - p["bet"]
    p["stack"] -= pay
    p["bet"] = raise_to
    p["contrib"] += pay
    data["pot"] += pay

    if raise_to > data["current_bet"]:
        data["last_raise_size"] = max(raise_to - data["current_bet"], data["last_raise_size"])
        data["current_bet"] = raise_to

    p["has_acted"] = True
    p["action"] = f"레이즈({raise_to})"
    set_last_action(data, p["name"], f"레이즈({raise_to})")

    for q in data["players"]:
        if q is not p and q["status"] == "alive" and q["stack"] > 0:
            q["has_acted"] = False

    return True, ""

# ---------------- 끊김 처리 ----------------
def check_disconnection(data):
    now = time.time()
    changed = False
    players = data["players"]

    for i, p in enumerate(players):
        if p["name"] != "빈 자리" and p.get("last_active", 0) > 0:
            if (now - p["last_active"]) > DISCONNECT_TIMEOUT:
                if p["status"] == "alive":
                    p["status"] = "folded"
                    p["has_acted"] = True
                    p["action"] = "연결끊김(폴드)"
                    set_last_action(data, p["name"], "연결끊김(폴드)")
                    changed = True
                    if i == data["turn_idx"]:
                        pass_turn(data)

    # ✅ BUGFIX: 올인(stack=0) 때문에 WAITING으로 튕기지 않게
    # '참가자 자리 점유' 기준으로 2명 미만이면 중단
    occupied = [p for p in players if p["name"] != "빈 자리"]
    if data["phase"] != "WAITING" and len(occupied) < 2:
        data["phase"] = "WAITING"
        data["msg"] = "플레이어 부족으로 게임 중단. 대기 중..."
        changed = True

    return changed

# ---------------- 프론트 카운트다운(깜빡임 완화) ----------------
def render_live_countdown(seconds_left: int):
    seconds_left = max(0, int(seconds_left))
    components.html(
        f"""
        <div id="cd" style="color:#ffeb3b;font-weight:900;font-size:18px;"></div>
        <script>
          let left = {seconds_left};
          function pad(n){{ return String(n).padStart(2,'0'); }}
          function draw(){{
            const m = Math.floor(left/60);
            const s = left%60;
            document.getElementById("cd").innerText = pad(m)+":"+pad(s);
          }}
          draw();
          setInterval(()=>{{ if(left>0) left--; draw(); }}, 1000);
        </script>
        """,
        height=28,
    )

# ---------------- init DB ----------------
db_init()

# ---------------- 입장 ----------------
if "my_seat" not in st.session_state:
    st.title("🦁 AI 몬스터 토너먼트")
    u_name = st.text_input("닉네임", value="형님")
    col1, col2 = st.columns(2)

    if col1.button("입장하기", type="primary"):
        def join_mut(s):
            target = -1
            for i, p in enumerate(s["players"]):
                if p["is_human"] and p["name"] == u_name:
                    target = i
                    break
            if target == -1:
                if s["players"][4]["name"] == "빈 자리":
                    target = 4
                else:
                    for i in range(9):
                        if s["players"][i]["name"] == "빈 자리":
                            target = i
                            break

            if target != -1:
                s["players"][target] = {
                    "name": u_name,
                    "seat": target + 1,
                    "stack": 60000,
                    "hand": [],
                    "bet": 0,
                    "contrib": 0,
                    "status": "folded",
                    "action": "관전 대기 중",
                    "is_human": True,
                    "role": "",
                    "has_acted": True,
                    "rebuy_count": 0,
                    "last_active": time.time(),
                }
                active_stacks = len([p for p in s["players"] if p["name"] != "빈 자리" and p["stack"] > 0])
                if s["phase"] == "WAITING" and active_stacks >= 2:
                    reset_for_next_hand(s)
            return s

        _, state = atomic_update(join_mut)
        seat = -1
        for i, p in enumerate(state["players"]):
            if p["name"] == u_name and p["is_human"]:
                seat = i
                break
        if seat != -1:
            st.session_state["my_seat"] = seat
            st.session_state["my_name"] = u_name
            st.rerun()

    if col2.button("⚠️ 서버 초기화"):
        atomic_update(lambda _s: init_game_data())
        st.rerun()

    st.stop()

# ---------------- 메인 ----------------
data = load_state_readonly()
my_seat = st.session_state.get("my_seat", -1)
my_name = st.session_state.get("my_name", "")

# seat validate
if my_seat == -1 or my_seat >= 9 or data["players"][my_seat]["name"] != my_name:
    found = -1
    for i, p in enumerate(data["players"]):
        if p["name"] == my_name and p["is_human"]:
            found = i
            break
    if found == -1:
        st.error("연결이 끊겼거나 자리 정보가 없어졌습니다. 다시 입장해주세요.")
        if "my_seat" in st.session_state:
            del st.session_state["my_seat"]
        st.stop()
    st.session_state["my_seat"] = found
    my_seat = found

# heartbeat
atomic_update(lambda s: (s["players"].__setitem__(my_seat, {**s["players"][my_seat], "last_active": time.time()}) or s) if 0 <= my_seat < 9 and s["players"][my_seat]["name"] == my_name else s)
data = load_state_readonly()

# disconnection
atomic_update(lambda s: s if not check_disconnection(s) else s)
data = load_state_readonly()

me = data["players"][my_seat]
curr_idx = data["turn_idx"]
curr_p = data["players"][curr_idx]

# ---------------- HUD ----------------
elapsed = time.time() - data["start_time"]
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb, bb, ante = BLIND_STRUCTURE[lvl - 1]
alive_p = [p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0]
avg_stack = (sum(p["stack"] for p in alive_p) // len(alive_p)) if alive_p else 0
remain = int(LEVEL_DURATION - (elapsed % LEVEL_DURATION))

st.markdown('<div class="top-hud">', unsafe_allow_html=True)
st.markdown(f'<div class="hud-left"><div class="hud-badge">LV {lvl}</div></div>', unsafe_allow_html=True)
st.markdown('<div class="hud-mid hud-time">', unsafe_allow_html=True)
render_live_countdown(remain)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="hud-right">'
    f'<div class="hud-badge">SB <b>{sb:,}</b></div>'
    f'<div class="hud-badge">BB <b>{bb:,}</b></div>'
    f'<div class="hud-badge">Ante <b>{ante:,}</b></div>'
    f'<div class="hud-badge">Avg <b>{avg_stack:,}</b></div>'
    f'</div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 턴 타임아웃 ----------------
time_left = max(0, TURN_TIMEOUT - (time.time() - data["turn_start_time"]))
if data["phase"] not in ("WAITING", "GAME_OVER") and time_left <= 0:
    def timeout_mut(s):
        if s["phase"] in ("WAITING", "GAME_OVER"):
            return s
        ci = s["turn_idx"]
        p = s["players"][ci]
        if p["status"] == "alive":
            p["status"] = "folded"
            p["has_acted"] = True
            p["action"] = "시간초과(폴드)"
            set_last_action(s, p["name"], "시간초과(폴드)")
            if not check_phase_end_and_advance(s):
                pass_turn(s)
        return s
    atomic_update(timeout_mut)
    st.rerun()

# ---------------- 메인 렌더(✅ GAME_OVER도 여기서 같이 렌더) ----------------
col_table, col_controls = st.columns([1.5, 1])

winner_seats = set(data.get("winner_seats") or [])
showdown_info = data.get("showdown")

with col_table:
    if data["phase"] == "WAITING":
        st.info("✋ 다른 플레이어 입장을 대기 중입니다... (최소 2명)")

    if data["phase"] == "GAME_OVER":
        rem = int(AUTO_NEXT_HAND_DELAY - (time.time() - data["game_over_time"]))
        st.info(f"게임 종료! {rem}초 후 다음 판 시작...")

        # 승리 효과(핸드당 1회)
        last_fx = st.session_state.get("last_fx_hand_id", None)
        if showdown_info and data.get("hand_id") is not None and last_fx != data["hand_id"]:
            st.session_state["last_fx_hand_id"] = data["hand_id"]
            st.balloons()

    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_comm_card(c) for c in data["community"]])

    for i in range(9):
        p = data["players"][i]
        active = "active-turn" if (i == curr_idx and data["phase"] not in ("WAITING","GAME_OVER")) else ""
        hero = "hero-seat" if i == my_seat else ""
        is_winner = "winner-seat" if i in winner_seats else ""
        timer_html = f'<div class="turn-timer">⏰ {int(time_left)}s</div>' if (i == curr_idx and data["phase"] not in ("WAITING","GAME_OVER")) else ""

        if p["name"] == "빈 자리":
            html += f'<div class="seat pos-{i}" style="opacity:0.2;"><div>빈 자리</div></div>'
            continue

        cards = "<div style='font-size:16px;'>🂠 🂠</div>"
        cls = ""
        if p["status"] == "folded":
            cards = "<div class='fold-text'>FOLD</div>"
            cls = "folded-seat"
        else:
            show_cards = (i == my_seat) or (showdown_info is not None and i in winner_seats)
            if show_cards and p["hand"]:
                cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"

        role = p["role"]
        role_cls = "role-D-SB" if role == "D-SB" else f"role-{role}"
        role_div = f"<div class='role-badge {role_cls}'>{role}</div>" if role else ""
        win_div = "<div class='winner-badge'>WINNER</div>" if i in winner_seats else ""

        html += (
            f'<div class="seat pos-{i} {active} {hero} {cls} {is_winner}">'
            f'{timer_html}{role_div}{win_div}'
            f'<div><b>{p["name"]}</b></div>'
            f'<div>{int(p["stack"]):,}</div>'
            f'{cards}'
            f'<div class="action-badge">{p["action"]}</div>'
            f'</div>'
        )

    showdown_html = ""
    if showdown_info:
        wdesc = showdown_info["winners"][0].get("desc", "")
        showdown_html += f"<div class='showdown'>🏁 SHOWDOWN · {wdesc}</div>"
        for w in showdown_info["winners"]:
            hand_html = ""
            if w.get("hand") and len(w["hand"]) == 2:
                hand_html = f"{make_card(w['hand'][0])}{make_card(w['hand'][1])}"
            showdown_html += f"<div class='sdrow'><b>{w['name']}</b> {hand_html}</div>"

    msg_html = (
        f"<div class='center-msg'>"
        f"<div>{comm}</div>"
        f"<h3>Pot: {data['pot']:,}</h3>"
        f"<p class='msgline'>{data['msg']}</p>"
        f"{showdown_html}"
        f"</div>"
    )
    html += msg_html + "</div>"
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    if me.get("hand"):
        st.markdown("### 내 카드")
        st.markdown(f"{make_card(me['hand'][0])}{make_card(me['hand'][1])}", unsafe_allow_html=True)

    if data["phase"] == "WAITING":
        if st.button("⚠️ 서버 초기화", use_container_width=True):
            atomic_update(lambda _s: init_game_data())
            st.rerun()

    elif data["phase"] == "GAME_OVER":
        if st.button("⚠️ 서버 초기화", use_container_width=True):
            atomic_update(lambda _s: init_game_data())
            st.rerun()

    else:
        if curr_idx == my_seat and me["status"] == "alive":
            st.success(f"내 차례! ({int(time_left)}초)")
            to_call = max(0, data["current_bet"] - me["bet"])

            c1, c2 = st.columns(2)
            label = "체크" if to_call == 0 else f"콜 ({to_call})"

            if c1.button(label, use_container_width=True):
                def act_mut(s):
                    if s["turn_idx"] != my_seat or s["players"][my_seat]["status"] != "alive":
                        return s
                    do_call_or_check(s, my_seat)
                    if not check_phase_end_and_advance(s):
                        pass_turn(s)
                    return s
                atomic_update(act_mut)
                st.rerun()

            if c2.button("폴드", type="primary", use_container_width=True):
                def act_mut(s):
                    if s["turn_idx"] != my_seat or s["players"][my_seat]["status"] != "alive":
                        return s
                    do_fold(s, my_seat)
                    if not check_phase_end_and_advance(s):
                        pass_turn(s)
                    return s
                atomic_update(act_mut)
                st.rerun()

            if st.button("🚨 ALL-IN", use_container_width=True):
                def act_mut(s):
                    if s["turn_idx"] != my_seat or s["players"][my_seat]["status"] != "alive":
                        return s
                    do_allin(s, my_seat)
                    if not check_phase_end_and_advance(s):
                        pass_turn(s)
                    return s
                atomic_update(act_mut)
                st.rerun()

            st.markdown("---")

            if me["stack"] > 0:
                min_to = data["bb"] if data["current_bet"] == 0 else (data["current_bet"] + data["last_raise_size"])
                max_to = me["bet"] + me["stack"]
                step_val = 1000 if sb >= 1000 else 100
                raise_to = st.number_input("레이즈/베팅 (총액 기준)", min_value=int(min_to), max_value=int(max_to), step=step_val)

                if st.button("레이즈 확정", use_container_width=True):
                    def act_mut(s):
                        if s["turn_idx"] != my_seat or s["players"][my_seat]["status"] != "alive":
                            return s
                        ok, msg = do_raise_to(s, my_seat, int(raise_to))
                        if not ok:
                            s["msg"] = f"❗ {msg}"
                            return s
                        if not check_phase_end_and_advance(s):
                            pass_turn(s)
                        return s
                    atomic_update(act_mut)
                    st.rerun()
        else:
            st.info(f"👤 {curr_p['name']} 대기 중... ({int(time_left)}s)")

        if st.button("⚠️ 서버 초기화", use_container_width=True):
            atomic_update(lambda _s: init_game_data())
            st.rerun()

# ---------------- GAME_OVER 다음판 처리 ----------------
if data["phase"] == "GAME_OVER":
    rem = int(AUTO_NEXT_HAND_DELAY - (time.time() - data["game_over_time"]))
    if rem <= 0:
        atomic_update(lambda s: reset_for_next_hand(s))

# ---------------- rerun 주기 ----------------
if data["phase"] == "WAITING":
    sleep_sec = 2.0
elif data["phase"] == "GAME_OVER":
    sleep_sec = 1.0
elif curr_idx == my_seat and me["status"] == "alive":
    sleep_sec = 0.6
else:
    sleep_sec = 2.0

time.sleep(sleep_sec)
st.rerun()
