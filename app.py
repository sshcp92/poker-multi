import streamlit as st
import random
import time
import json
from typing import Dict, Any, List, Tuple, Optional

# =========================
# 0. Page
# =========================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

# =========================
# 1. Supabase
# =========================
SUPABASE_URL = (st.secrets.get("SUPABASE_URL", "") or "").strip()
SUPABASE_ANON_KEY = (st.secrets.get("SUPABASE_ANON_KEY", "") or "").strip()

_supabase = None
_supabase_err = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        _supabase = None
        _supabase_err = str(e)


def sb_room_get(room_code: str) -> Optional[Dict[str, Any]]:
    if _supabase is None:
        return None
    try:
        res = (
            _supabase.table("poker_rooms")
            .select("room_code,state,updated_at")
            .eq("room_code", room_code)
            .execute()
        )
        if res.data and len(res.data) > 0:
            row = res.data[0]
            return row.get("state")
        return None
    except Exception:
        # 네트워크/정책/테이블 문제 등 어떤 이유든 앱 전체 다운 방지
        return None


def sb_room_upsert(room_code: str, state: Dict[str, Any]) -> bool:
    if _supabase is None:
        return False
    try:
        payload = {"room_code": room_code, "state": state}
        _supabase.table("poker_rooms").upsert(payload).execute()
        return True
    except Exception:
        return False


# =========================
# 2. Game config
# =========================
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
AUTO_NEXT_HAND_DELAY = 4

DISCONNECT_TIMEOUT = 20  # 초: 이 시간동안 last_active 갱신 없으면 강퇴(좌석 비움)

START_STACK = 60000
REBUY_STACKS = [60000, 70000, 80000]  # 총 3엔트리 (첫입장 포함)

RANKS = "23456789TJQKA"
SUITS = ["♠", "♥", "♦", "♣"]
DISPLAY_MAP = {"T": "10", "J": "J", "Q": "Q", "K": "K", "A": "A"}


# =========================
# 3. CSS (가독성/색/빈막대 제거)
# =========================
st.markdown(
        """
<style>
/* ===== base ===== */
.stApp { background:#0f0f10; color:#fff; }
.stApp > header { visibility:hidden; }
div[data-testid="stStatusWidget"]{visibility:hidden;}
div[data-testid="stDecoration"] {display:none;} /* 상단 빈 막대 제거 */
footer {visibility:hidden;}

/* ===== Sidebar 가독성 Fix ===== */
section[data-testid="stSidebar"]{
  background:#0f0f10 !important;
  border-right:1px solid #222 !important;
}
section[data-testid="stSidebar"] *{
  color:#ffffff !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea{
  background:#151515 !important;
  color:#ffffff !important;
  border:1px solid #333 !important;
}
section[data-testid="stSidebar"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder{
  color:#bdbdbd !important;
}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{
  color:#e0e0e0 !important;
}

/* ===== Streamlit 위젯 글씨/버튼 가독성 ===== */
.stButton > button { 
  color:#000 !important; 
  font-weight:900 !important; 
}
.stTextInput input, .stNumberInput input{
  color:#fff !important;
}
div[data-baseweb="input"] input{
  color:#fff !important;
}
label, .stMarkdown, .stCaption, .stText{
  color:#fff !important;
}

/* ===== HUD ===== */
.hud-wrap{
  display:flex; align-items:center; justify-content:space-between;
  gap:12px; padding:10px 12px; border-radius:16px;
  border:1px solid #2a2a2a; background: rgba(0,0,0,0.35);
  margin-bottom: 10px;
}
.hud-left{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.pill{
  padding:6px 10px; border-radius:999px; font-weight:800; font-size:12px;
  border:1px solid rgba(255,0,0,0.6);
  background: rgba(255,0,0,0.12);
  color:#ff4d4d;
}
.pill-white{
  border:1px solid #2a2a2a; background:rgba(255,255,255,0.06);
  color:#fff;
}
.timer-box{
  min-width:120px; text-align:center;
  padding:8px 12px; border-radius:14px;
  border:1px solid rgba(255,235,59,0.35);
  background: rgba(0,0,0,0.55);
  color:#ffeb3b; font-weight:900; font-size:18px;
}

/* ===== Table board ===== */
.game-board-container{
  position:relative; width:100%;
  min-height:520px; height: 72vh;
  background:#151515; border-radius:22px;
  border:2px solid #262626; overflow:hidden;
}
.poker-table{
  position:absolute; top:50%; left:50%;
  transform:translate(-50%,-50%);
  width: 92%; height: 75%;
  background: radial-gradient(#5d4037, #2b1a17);
  border: 12px solid #1b0f0e;
  border-radius: 160px;
  box-shadow: inset 0 0 30px rgba(0,0,0,0.85);
}
.seat{
  position:absolute; width:105px; height:115px;
  background:#0f0f10; border:2px solid #3a3a3a;
  border-radius:14px; color:white;
  text-align:center; font-size:10px;
  display:flex; flex-direction:column;
  justify-content:center; align-items:center;
  z-index:10;
}
.pos-0 {top:5%; right:20%;}
.pos-1 {top:25%; right:3%;}
.pos-2 {bottom:25%; right:3%;}
.pos-3 {bottom:5%; right:20%;}
.pos-4 {bottom:2%; left:50%; transform:translateX(-50%);}
.pos-5 {bottom:5%; left:20%;}
.pos-6 {bottom:25%; left:3%;}
.pos-7 {top:25%; left:3%;}
.pos-8 {top:5%; left:20%;}

.hero-seat{ border:3px solid #ffeb3b; box-shadow:0 0 18px rgba(255,235,59,0.55); }
.active-turn{ border:3px solid #ffeb3b !important; box-shadow:0 0 18px rgba(255,235,59,0.55); }

.winner-seat{
  border:3px solid #00e676 !important;
  box-shadow:0 0 22px rgba(0,230,118,0.7);
  animation: winnerPulse 0.9s ease-in-out infinite alternate;
}
@keyframes winnerPulse { from { transform: scale(1.0); } to { transform: scale(1.03); } }

.role-badge{
  position:absolute; top:-9px; left:-9px;
  min-width:28px; height:28px;
  padding:0 6px; border-radius:999px;
  color:#000; font-weight:900; line-height:26px;
  border:1px solid #111;
  z-index:50; font-size:11px;
  background:#fff;
}
.role-D { background:#ffeb3b; }
.role-SB { background:#90caf9; }
.role-BB { background:#ef9a9a; }
.role-D-SB { background: linear-gradient(135deg, #ffeb3b 50%, #90caf9 50%); font-size:10px; }

.action-badge{
  position:absolute; bottom:-12px;
  background:#ffeb3b; color:#000;
  font-weight:900; padding:2px 6px;
  border-radius:6px; font-size:10px;
  border:1px solid #000;
  z-index:50; white-space: nowrap;
}
.turn-timer{
  position:absolute; top:-24px;
  width:100%; text-align:center;
  color:#ffeb3b; font-weight:900; font-size:12px;
  z-index:60;
}
.card-span{
  background:white; padding:2px 6px; border-radius:6px;
  margin:1px; font-weight:900; font-size:18px;
  color:black; border:1px solid #ccc; display:inline-block;
}
.comm-card-span{ font-size:30px !important; padding:4px 8px !important; }

.fold-text{ color:#ff5252; font-weight:900; font-size:14px; }
.folded-seat{ opacity:0.45; }

.center-msg{
  position:absolute; top:48%; left:50%;
  transform:translate(-50%,-50%);
  text-align:center; color:white; width:100%;
}
.center-msg h3{ margin:6px 0; font-size:22px; }
.center-msg .phase{
  display:inline-block;
  padding:6px 10px;
  background:rgba(0,0,0,0.65);
  border:1px solid rgba(255,235,59,0.22);
  border-radius:10px;
  color:#ffeb3b;
  font-weight:900;
}
.showdown-box{
  margin-top:10px;
  font-size:14px;
  color:#fff;
}
.showdown-line{
  margin:6px auto;
  width: fit-content;
  padding:6px 10px;
  border-radius:12px;
  background: rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.12);
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# 4. Helpers (cards / hand eval)
# =========================
def r_str(r: str) -> str:
    return DISPLAY_MAP.get(r, r)


def make_card(card: str, big: bool = False) -> str:
    if not card or len(card) < 2:
        return "🂠"
    color = "red" if card[1] in ["♥", "♦"] else "black"
    cls = "card-span comm-card-span" if big else "card-span"
    return f"<span class='{cls}' style='color:{color}'>{r_str(card[0])}{card[1]}</span>"


def new_deck() -> List[str]:
    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck


def init_players() -> List[Dict[str, Any]]:
    players = []
    for i in range(9):
        players.append(
            dict(
                name="빈 자리",
                seat=i + 1,
                stack=0,
                hand=[],
                bet=0,
                status="standby",  # standby/alive/folded
                action="",
                is_human=False,
                role="",
                has_acted=False,
                rebuy_count=0,  # 0,1,2 (총3엔트리)
                last_active=0.0,
            )
        )
    return players


def init_room_state(room_code: str) -> Dict[str, Any]:
    return dict(
        room_code=room_code,
        players=init_players(),
        pot=0,
        deck=new_deck(),
        community=[],
        phase="WAITING",  # WAITING/PREFLOP/FLOP/TURN/RIVER/GAME_OVER
        current_bet=0,
        turn_idx=0,
        dealer_idx=0,
        level=1,
        started_at=0.0,  # 게임 시작 시각 (WAITING이면 0)
        hand_started_at=0.0,
        turn_started_at=0.0,
        game_over_at=0.0,
        msg="플레이어를 기다리는 중... (최소 2명)",
        showdown=[],
        winners=[],
    )


def get_hand_strength_detail(cards: List[str]) -> Tuple[int, List[int], str]:
    if not cards or len(cards) < 5:
        return (-1, [], "No Hand")

    rank_map = {r: i for i, r in enumerate("..23456789TJQKA", 0)}
    ranks = sorted([rank_map[c[0]] for c in cards], reverse=True)
    suits = [c[1] for c in cards]

    flush_suit = None
    for s in ["♠", "♥", "♦", "♣"]:
        if suits.count(s) >= 5:
            flush_suit = s
            break
    is_flush = flush_suit is not None
    flush_ranks = (
        sorted([rank_map[c[0]] for c in cards if c[1] == flush_suit], reverse=True) if is_flush else []
    )

    def check_straight(unique_ranks: List[int]) -> Tuple[bool, int]:
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
        is_sf, sf_high = check_straight(flush_ranks)

    from collections import Counter
    counts = Counter(ranks)
    sorted_counts = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    def r_name(v: int) -> str:
        return r_str("..23456789TJQKA"[v])

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


# =========================
# 5. State I/O
# =========================
def load_room(room_code: str) -> Dict[str, Any]:
    state = sb_room_get(room_code)
    if state is None:
        state = init_room_state(room_code)
        sb_room_upsert(room_code, state)
    return state


def save_room(room_code: str, state: Dict[str, Any]) -> None:
    sb_room_upsert(room_code, state)


# =========================
# 6. Game flow
# =========================
def active_player_indices(players: List[Dict[str, Any]]) -> List[int]:
    return [i for i, p in enumerate(players) if p["name"] != "빈 자리" and p["stack"] > 0]


def find_next_alive(players: List[Dict[str, Any]], start_idx: int) -> int:
    for k in range(1, 10):
        j = (start_idx + k) % 9
        if players[j]["status"] == "alive":
            return j
    return start_idx


def apply_blinds_and_deal(state: Dict[str, Any]) -> Dict[str, Any]:
    players = state["players"]
    alive_idxs = active_player_indices(players)
    if len(alive_idxs) < 2:
        state["phase"] = "WAITING"
        state["started_at"] = 0.0
        state["msg"] = "플레이어를 기다리는 중... (최소 2명)"
        return state

    now = time.time()
    elapsed = max(0, now - state["started_at"])
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl - 1]
    state["level"] = lvl

    deck = new_deck()
    pot = 0

    cur_d = state["dealer_idx"]
    new_d = cur_d
    for k in range(1, 10):
        j = (cur_d + k) % 9
        if players[j]["name"] != "빈 자리" and players[j]["stack"] > 0:
            new_d = j
            break
    state["dealer_idx"] = new_d

    for p in players:
        if p["name"] != "빈 자리" and p["stack"] > 0:
            p["status"] = "alive"
            p["hand"] = [deck.pop(), deck.pop()]
            if ante_amt > 0:
                a = min(p["stack"], ante_amt)
                p["stack"] -= a
                pot += a
        else:
            p["status"] = "standby"
            p["hand"] = []
        p["bet"] = 0
        p["action"] = ""
        p["has_acted"] = False
        p["role"] = ""

    def next_active(idx: int) -> int:
        for k in range(1, 10):
            j = (idx + k) % 9
            if players[j]["status"] == "alive":
                return j
        return idx

    if len(alive_idxs) == 2:
        sb_idx = new_d
        bb_idx = next_active(sb_idx)
        players[sb_idx]["role"] = "D-SB"
        players[bb_idx]["role"] = "BB"
        turn_start = sb_idx
    else:
        sb_idx = next_active(new_d)
        bb_idx = next_active(sb_idx)
        players[new_d]["role"] = "D"
        players[sb_idx]["role"] = "SB"
        players[bb_idx]["role"] = "BB"
        turn_start = next_active(bb_idx)

    if players[sb_idx]["status"] == "alive":
        pay = min(players[sb_idx]["stack"], sb_amt)
        players[sb_idx]["stack"] -= pay
        players[sb_idx]["bet"] = pay
        pot += pay

    if players[bb_idx]["status"] == "alive":
        pay = min(players[bb_idx]["stack"], bb_amt)
        players[bb_idx]["stack"] -= pay
        players[bb_idx]["bet"] = pay
        pot += pay

    state.update(
        pot=pot,
        deck=deck,
        community=[],
        phase="PREFLOP",
        current_bet=bb_amt,
        turn_idx=turn_start,
        hand_started_at=now,
        turn_started_at=now,
        game_over_at=0.0,
        msg=f"Level {lvl} 시작! (SB {sb_amt}/BB {bb_amt})",
        showdown=[],
        winners=[],
    )
    return state


def start_if_ready(state: Dict[str, Any]) -> Dict[str, Any]:
    alive_idxs = active_player_indices(state["players"])
    if state["phase"] == "WAITING" and len(alive_idxs) >= 2:
        state["started_at"] = time.time()
        state = apply_blinds_and_deal(state)
    return state


def kick_disconnected(state: Dict[str, Any]) -> Dict[str, Any]:
    now = time.time()
    players = state["players"]
    changed = False

    for i, p in enumerate(players):
        if p["name"] == "빈 자리":
            continue
        last = float(p.get("last_active", 0.0))
        if last > 0 and (now - last) > DISCONNECT_TIMEOUT:
            players[i] = dict(
                name="빈 자리",
                seat=i + 1,
                stack=0,
                hand=[],
                bet=0,
                status="standby",
                action="",
                is_human=False,
                role="",
                has_acted=False,
                rebuy_count=0,
                last_active=0.0,
            )
            changed = True

    if changed:
        alive_idxs = active_player_indices(players)
        if len(alive_idxs) < 2:
            state["phase"] = "WAITING"
            state["started_at"] = 0.0
            state["msg"] = "플레이어 퇴장으로 게임 중단. 대기 중... (최소 2명)"
            state["current_bet"] = 0
            state["pot"] = 0
            state["community"] = []
            state["showdown"] = []
            state["winners"] = []
    return state


def pass_turn(state: Dict[str, Any]) -> None:
    players = state["players"]
    curr = state["turn_idx"]
    for k in range(1, 10):
        j = (curr + k) % 9
        if players[j]["status"] == "alive" and players[j]["stack"] > 0:
            state["turn_idx"] = j
            state["turn_started_at"] = time.time()
            return
        if players[j]["status"] == "alive" and players[j]["stack"] == 0:
            players[j]["has_acted"] = True
    state["turn_started_at"] = time.time()


def end_hand_all_fold(state: Dict[str, Any]) -> Dict[str, Any]:
    alive = [p for p in state["players"] if p["status"] == "alive"]
    if len(alive) == 1:
        winner = alive[0]
        winner["stack"] += state["pot"]
        state["pot"] = 0
        state["winners"] = [state["players"].index(winner)]
        state["showdown"] = [{"name": winner["name"], "hole": winner["hand"], "desc": "전원 폴드"}]
        state["msg"] = f"🏆 {winner['name']} 승리! (전원 폴드)"
        state["phase"] = "GAME_OVER"
        state["game_over_at"] = time.time()
    return state


def showdown_and_end(state: Dict[str, Any]) -> Dict[str, Any]:
    players = state["players"]
    alive_idxs = [i for i, p in enumerate(players) if p["status"] == "alive"]

    best_rank = -1
    best_tb: List[int] = []
    winners: List[int] = []
    showdown_lines = []

    for i in alive_idxs:
        p = players[i]
        rank_val, tb, desc = get_hand_strength_detail(p["hand"] + state["community"])
        showdown_lines.append({"name": p["name"], "hole": p["hand"], "desc": desc, "rank": rank_val, "tb": tb})

        if rank_val > best_rank or (rank_val == best_rank and tb > best_tb):
            best_rank = rank_val
            best_tb = tb
            winners = [i]
        elif rank_val == best_rank and tb == best_tb:
            winners.append(i)

    split = state["pot"] // max(1, len(winners))
    for i in winners:
        players[i]["stack"] += split

    state["pot"] = 0
    state["winners"] = winners

    winner_names = ", ".join(players[i]["name"] for i in winners)
    win_desc = ""
    for line in showdown_lines:
        if line["name"] == players[winners[0]]["name"]:
            win_desc = line["desc"]
            break

    state["showdown"] = [{"name": x["name"], "hole": x["hole"], "desc": x["desc"]} for x in showdown_lines]
    state["msg"] = f"🏆 {winner_names} 승리! [{win_desc}]"
    state["phase"] = "GAME_OVER"
    state["game_over_at"] = time.time()
    return state


def check_phase_end(state: Dict[str, Any]) -> Dict[str, Any]:
    players = state["players"]
    alive = [p for p in players if p["status"] == "alive"]
    if len(alive) <= 1:
        return end_hand_all_fold(state)

    target = state["current_bet"]
    active = [p for p in players if p["status"] == "alive"]
    all_acted = all(p["has_acted"] for p in active)
    all_matched = all((p["bet"] == target) or (p["stack"] == 0) for p in active)

    if not (all_acted and all_matched):
        return state

    deck = state["deck"]
    if state["phase"] == "PREFLOP":
        state["phase"] = "FLOP"
        state["community"] = [deck.pop(), deck.pop(), deck.pop()]
    elif state["phase"] == "FLOP":
        state["phase"] = "TURN"
        state["community"].append(deck.pop())
    elif state["phase"] == "TURN":
        state["phase"] = "RIVER"
        state["community"].append(deck.pop())
    elif state["phase"] == "RIVER":
        return showdown_and_end(state)

    state["current_bet"] = 0
    for p in players:
        p["bet"] = 0
        p["has_acted"] = False
        if p["status"] == "alive":
            p["action"] = ""

    dealer = state["dealer_idx"]
    state["turn_idx"] = find_next_alive(players, dealer)
    state["turn_started_at"] = time.time()
    state["msg"] = f"{state['phase']} 시작!"
    return state


def force_timeout_fold(state: Dict[str, Any]) -> Dict[str, Any]:
    players = state["players"]
    idx = state["turn_idx"]
    p = players[idx]
    if p["status"] == "alive":
        p["status"] = "folded"
        p["has_acted"] = True
        p["action"] = "시간초과"
        state = check_phase_end(state)
        if state["phase"] != "GAME_OVER":
            pass_turn(state)
    return state


def auto_rebuy_if_bust(player: Dict[str, Any]) -> bool:
    if player["stack"] > 0:
        return False
    if player["rebuy_count"] >= 2:
        return False
    player["rebuy_count"] += 1
    player["stack"] = REBUY_STACKS[player["rebuy_count"]]
    player["status"] = "folded"
    player["action"] = f"자동 리바인 ({player['stack']:,})"
    player["has_acted"] = True
    return True


# =========================
# 7. Sidebar: room + join + refresh
# =========================
st.sidebar.markdown("### 방 설정")
room_code = st.sidebar.text_input("방코드", value=st.session_state.get("room_code", "np"))
nickname = st.sidebar.text_input("닉네임", value=st.session_state.get("nickname", "형님"))

st.sidebar.caption("친구들끼리 같은 방코드로 들어오면 같은 게임을 봅니다.")

if st.sidebar.button("입장/재입장", type="primary"):
    st.session_state["room_code"] = room_code.strip()
    st.session_state["nickname"] = nickname.strip()
    st.session_state.pop("my_seat", None)
    st.rerun()

auto_refresh = st.sidebar.toggle("자동 새로고침(권장)", value=True)
st.sidebar.caption("※ 자동 새로고침이 너무 빠르면 버튼 클릭이 씹힐 수 있어요. 그럴 땐 끄고 해보세요.")

if st.sidebar.button("🔄 지금 새로고침", use_container_width=True):
    st.rerun()

if not room_code.strip() or not nickname.strip():
    st.stop()

room_code = room_code.strip()
nickname = nickname.strip()
st.session_state["room_code"] = room_code
st.session_state["nickname"] = nickname

if _supabase is None:
    st.error("Supabase 연결이 안 잡혔어. Streamlit Secrets에 SUPABASE_URL / SUPABASE_ANON_KEY 넣었는지 확인해줘.")
    if _supabase_err:
        st.caption(f"(supabase init err) {_supabase_err}")
    st.stop()

# =========================
# 8. Join seat
# =========================
def ensure_join(state: Dict[str, Any], nickname: str) -> int:
    players = state["players"]
    for i, p in enumerate(players):
        if p["name"] == nickname:
            p["is_human"] = True
            return i

    target = -1
    if players[4]["name"] == "빈 자리":
        target = 4
    else:
        for i in range(9):
            if players[i]["name"] == "빈 자리":
                target = i
                break

    if target != -1:
        players[target].update(
            name=nickname,
            stack=REBUY_STACKS[0],
            hand=[],
            bet=0,
            status="folded",
            action="관전 대기 중",
            is_human=True,
            role="",
            has_acted=True,
            rebuy_count=0,
            last_active=time.time(),
        )
    return target


state = load_room(room_code)

if "my_seat" not in st.session_state:
    seat = ensure_join(state, nickname)
    st.session_state["my_seat"] = seat
    save_room(room_code, state)
    st.rerun()

my_seat = int(st.session_state.get("my_seat", -1))
players = state["players"]

if my_seat < 0 or my_seat >= 9 or players[my_seat]["name"] != nickname:
    seat = ensure_join(state, nickname)
    st.session_state["my_seat"] = seat
    save_room(room_code, state)
    st.rerun()

players[my_seat]["last_active"] = time.time()

# =========================
# 9. Kick disconnected + start game if ready
# =========================
state = kick_disconnected(state)
state = start_if_ready(state)
save_room(room_code, state)

# =========================
# 10. Timers
# =========================
now = time.time()

if state["phase"] == "WAITING":
    level_left = 0
else:
    elapsed = now - state["started_at"]
    level_left = int(LEVEL_DURATION - (elapsed % LEVEL_DURATION))
    state["level"] = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)

if state["phase"] not in ["WAITING", "GAME_OVER"]:
    time_left = max(0, TURN_TIMEOUT - (now - state["turn_started_at"]))
    if time_left <= 0:
        state = load_room(room_code)
        state = force_timeout_fold(state)
        save_room(room_code, state)
        st.rerun()
else:
    time_left = TURN_TIMEOUT

if state["phase"] == "GAME_OVER":
    rem = int(AUTO_NEXT_HAND_DELAY - (now - state["game_over_at"]))
    if rem <= 0:
        state = load_room(room_code)
        state = apply_blinds_and_deal(state)
        save_room(room_code, state)
        st.rerun()

# =========================
# 11. HUD
# =========================
lvl = state["level"]
sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl - 1]

alive = [p for p in state["players"] if p["name"] != "빈 자리" and p["stack"] > 0]
avg_stack = (sum(p["stack"] for p in alive) // len(alive)) if alive else 0

players_in_room = len([p for p in state["players"] if p["name"] != "빈 자리"])
max_seats = 9
players_label = f"Players {players_in_room}/{max_seats}"

timer_text = "--:--" if state["phase"] == "WAITING" else f"{level_left//60:02d}:{level_left%60:02d}"

hud_html = f"""
<div class="hud-wrap">
  <div class="hud-left">
    <span class="pill pill-white">LV {lvl}</span>
    <span class="pill pill-white">{players_label}</span>
    <span class="pill">SB {sb_amt:,}</span>
    <span class="pill">BB {bb_amt:,}</span>
    <span class="pill">Ante {ante_amt:,}</span>
    <span class="pill">Avg {avg_stack:,}</span>
  </div>
  <div class="timer-box">{timer_text}</div>
</div>
"""
st.markdown(hud_html, unsafe_allow_html=True)

# =========================
# 12. Main layout
# =========================
col_table, col_controls = st.columns([1.65, 1])

winner_set = set(state.get("winners") or [])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    comm = "".join([make_card(c, big=True) for c in state["community"]])

    curr_idx = state["turn_idx"]
    for i in range(9):
        p = state["players"][i]
        if p["name"] == "빈 자리":
            html += f'<div class="seat pos-{i}" style="opacity:0.18;"><div>빈 자리</div></div>'
            continue

        active_cls = "active-turn" if (i == curr_idx and state["phase"] not in ["WAITING", "GAME_OVER"]) else ""
        hero_cls = "hero-seat" if i == my_seat else ""
        folded_cls = "folded-seat" if p["status"] == "folded" else ""
        winner_cls = "winner-seat" if (state["phase"] == "GAME_OVER" and i in winner_set) else ""

        timer_html = ""
        if i == curr_idx and state["phase"] not in ["WAITING", "GAME_OVER"]:
            timer_html = f"<div class='turn-timer'>{int(time_left)}s</div>"

        cards = "<div style='font-size:16px;'>🂠 🂠</div>"
        if p["status"] == "folded":
            cards = "<div class='fold-text'>FOLD</div>"
        else:
            if i == my_seat or state["phase"] == "GAME_OVER":
                if p["hand"]:
                    cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"
                else:
                    cards = ""

        role = p.get("role", "")
        role_cls = "role-D-SB" if role == "D-SB" else f"role-{role}"
        role_div = f"<div class='role-badge {role_cls}'>{role}</div>" if role else ""

        action = p.get("action", "")
        html += (
            f'<div class="seat pos-{i} {active_cls} {hero_cls} {folded_cls} {winner_cls}">'
            f"{timer_html}{role_div}"
            f"<div><b>{p['name']}</b></div>"
            f"<div>{int(p['stack']):,}</div>"
            f"{cards}"
            f"<div class='action-badge'>{action}</div>"
            "</div>"
        )

    showdown_html = ""
    if state["phase"] == "GAME_OVER" and state.get("showdown"):
        lines = []
        for line in state["showdown"]:
            hole = "".join([make_card(c) for c in line["hole"]]) if line.get("hole") else ""
            lines.append(
                f"<div class='showdown-line'><b>{line['name']}</b> {hole} "
                f"<span style='color:#ffeb3b;font-weight:900;'>→ {line['desc']}</span></div>"
            )
        confetti = "🎉" * 10
        showdown_html = f"""
        <div class="showdown-box">
          <div style="font-size:18px; font-weight:900; color:#00e676; margin-bottom:4px;">{confetti}</div>
          {''.join(lines)}
        </div>
        """

    msg_html = (
        f"<div class='center-msg'>"
        f"<div>{comm}</div>"
        f"<h3>Pot: {state['pot']:,}</h3>"
        f"<div class='phase'>{state['msg']}</div>"
        f"{showdown_html}"
        f"</div>"
    )
    html += msg_html + "</div>"
    st.markdown(html, unsafe_allow_html=True)

with col_controls:
    me = state["players"][my_seat]

    if st.button("⚠️ 서버 초기화(이 방)", use_container_width=True):
        state = init_room_state(room_code)
        save_room(room_code, state)
        st.rerun()

    st.markdown("### 내 카드")
    if me.get("hand"):
        st.markdown("".join([make_card(c) for c in me["hand"]]), unsafe_allow_html=True)
    else:
        st.caption("아직 핸드 없음")

    if state["phase"] == "WAITING":
        st.info("✋ 다른 플레이어 입장을 기다리는 중입니다. (최소 2명)")
    else:
        auto_rebuy_if_bust(me)

        curr_idx = state["turn_idx"]
        curr_p = state["players"][curr_idx]

        if state["phase"] != "GAME_OVER" and curr_idx == my_seat and me["status"] == "alive":
            to_call = max(0, state["current_bet"] - me["bet"])
            st.success(f"내 차례! ({int(time_left)}초)")

            check_label = "체크" if to_call == 0 else f"콜 ({to_call:,})"
            if st.button(check_label, use_container_width=True):
                state = load_room(room_code)
                me = state["players"][my_seat]
                to_call = max(0, state["current_bet"] - me["bet"])
                pay = min(to_call, me["stack"])
                me["stack"] -= pay
                me["bet"] += pay
                state["pot"] += pay
                me["has_acted"] = True
                me["action"] = "체크" if pay == 0 else f"콜({pay:,})"
                state = check_phase_end(state)
                if state["phase"] != "GAME_OVER":
                    pass_turn(state)
                save_room(room_code, state)
                st.rerun()

            c1, c2 = st.columns(2)
            if c1.button("폴드", type="primary", use_container_width=True):
                state = load_room(room_code)
                me = state["players"][my_seat]
                me["status"] = "folded"
                me["has_acted"] = True
                me["action"] = "폴드"
                state = check_phase_end(state)
                if state["phase"] != "GAME_OVER":
                    pass_turn(state)
                save_room(room_code, state)
                st.rerun()

            if c2.button("🚨 ALL-IN", use_container_width=True):
                state = load_room(room_code)
                me = state["players"][my_seat]
                pay = me["stack"]
                me["stack"] = 0
                me["bet"] += pay
                state["pot"] += pay
                me["has_acted"] = True
                me["action"] = f"올인({pay:,})"
                if me["bet"] > state["current_bet"]:
                    state["current_bet"] = me["bet"]
                    for p in state["players"]:
                        if p is not me and p["status"] == "alive" and p["stack"] > 0:
                            p["has_acted"] = False
                state = check_phase_end(state)
                if state["phase"] != "GAME_OVER":
                    pass_turn(state)
                save_room(room_code, state)
                st.rerun()

            st.markdown("---")

            min_raise = max(bb_amt, state["current_bet"] * 2)
            max_total = me["stack"] + me["bet"]
            default_val = min(min_raise, max_total)

            step_val = 1000 if sb_amt >= 1000 else 100

            raise_to = st.number_input(
                "레이즈(총액 기준)",
                min_value=int(default_val if default_val <= max_total else max_total),
                max_value=int(max_total),
                value=int(default_val),
                step=int(step_val),
            )

            if st.button("레이즈 확정", use_container_width=True):
                state = load_room(room_code)
                me = state["players"][my_seat]
                raise_to = int(raise_to)
                pay = raise_to - me["bet"]
                pay = min(pay, me["stack"])
                me["stack"] -= pay
                me["bet"] += pay
                state["pot"] += pay
                state["current_bet"] = max(state["current_bet"], me["bet"])
                me["has_acted"] = True
                me["action"] = f"레이즈({me['bet']:,})"
                for p in state["players"]:
                    if p is not me and p["status"] == "alive" and p["stack"] > 0:
                        p["has_acted"] = False
                state = check_phase_end(state)
                if state["phase"] != "GAME_OVER":
                    pass_turn(state)
                save_room(room_code, state)
                st.rerun()

        else:
            if state["phase"] == "GAME_OVER":
                st.info("게임 종료! 곧 다음 판 시작…")
            else:
                st.info(f"👤 {curr_p['name']} 대기 중… ({int(time_left)}s)")

# =========================
# 13. Auto refresh (버튼 씹힘 방지 버전)
# =========================
# - 기존의 time.sleep + st.rerun 무한루프 제거(클릭이 안 먹는 원인)
# - 가능하면 st_autorefresh 사용 (있으면 더 안정적)
if auto_refresh:
    interval_ms = 3000 if state["phase"] == "WAITING" else 1000
    try:
        from streamlit_autorefresh import st_autorefresh  # pip: streamlit-autorefresh
        st_autorefresh(interval=interval_ms, key="autorefresh")
    except Exception:
        # 패키지 없으면 자동 갱신 없이 진행(클릭 안정성 우선)
        st.caption("자동 새로고침 모듈이 없어 기본 자동갱신은 꺼진 상태로 동작합니다. (버튼 클릭은 정상)")


