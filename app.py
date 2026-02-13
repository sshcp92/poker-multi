import streamlit as st
import random
import time
from supabase import create_client

# ==========================================
# 0) Streamlit config
# ==========================================
st.set_page_config(layout="wide", page_title="AI 몬스터 토너먼트", page_icon="🦁")

# ==========================================
# 1) Settings
# ==========================================
MAX_SEATS = 9

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

# 접속 끊김 감지(자리 비우기)
DISCONNECT_TIMEOUT = 25

# 화면 자동 갱신(1초) - Streamlit 구조상 rerun은 필요함
AUTO_REFRESH_SEC = 1

RANKS = "23456789TJQKA"
SUITS = ["♠", "♥", "♦", "♣"]
DISPLAY_MAP = {"T": "10", "J": "J", "Q": "Q", "K": "K", "A": "A"}

ENTRY_STACKS = [60000, 70000, 80000]  # 총 3 엔트리

# ==========================================
# 2) CSS (dark + readable)
# ==========================================
st.markdown(
    """
<style>
.stApp {background-color:#0f0f10; color:#eaeaea;}
.stApp > header {visibility: hidden;}
div[data-testid="stStatusWidget"] {visibility: hidden;}

.top-hud {
  display:flex; gap:10px; align-items:center; justify-content:space-between;
  background:#0b0b0c; border:1px solid #222; padding:10px 12px; border-radius:14px;
  margin-bottom:10px;
}
.hud-left { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.pill {
  display:inline-flex; align-items:center; gap:8px;
  border:1px solid #2b2b2b; padding:6px 10px; border-radius:999px;
  background:#111;
  font-size:13px;
}
.pill-red { border-color:#ff3b30; color:#ff3b30; }
.pill-yellow { border-color:#ffcc00; color:#ffcc00; }
.pill-white { border-color:#3a3a3a; color:#f1f1f1; }

.hud-timer {
  min-width:120px;
  text-align:center;
  font-weight:800;
  font-size:18px;
  color:#ffcc00;
  background:#000;
  border:1px solid #222;
  border-radius:14px;
  padding:10px 12px;
}

.game-board-container {
  position:relative; width:100%;
  min-height:520px; height: 70vh;
  margin:0 auto;
  background-color:#141416;
  border-radius:20px;
  border:2px solid #222;
  overflow: hidden;
}
.poker-table {
  position:absolute; top:50%; left:50%;
  transform:translate(-50%,-50%);
  width: 92%;
  height: 75%;
  background: radial-gradient(#5d4037, #2d1a16);
  border: 12px solid #1a0f0d;
  border-radius: 180px;
  box-shadow: inset 0 0 35px rgba(0,0,0,0.85);
}

.seat {
  position:absolute;
  width:105px; height:118px;
  background:#141416;
  border:2px solid #333;
  border-radius:14px;
  color:white;
  text-align:center;
  font-size:10px;
  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
  z-index:10;
  padding-top:6px;
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

.hero-seat { border:3px solid #ffcc00; box-shadow:0 0 18px rgba(255,204,0,0.6); }
.active-turn { border:3px solid #ffcc00 !important; box-shadow: 0 0 20px rgba(255,204,0,0.7); }

.winner-seat {
  border:3px solid #34c759 !important;
  box-shadow:0 0 25px rgba(52,199,89,0.9);
  animation: winnerPulse 1.2s ease-in-out infinite;
}
@keyframes winnerPulse {
  0% { box-shadow:0 0 10px rgba(52,199,89,0.6); }
  50% { box-shadow:0 0 26px rgba(52,199,89,1.0); }
  100% { box-shadow:0 0 10px rgba(52,199,89,0.6); }
}

.card-span {
  background:white;
  padding:1px 5px;
  border-radius:6px;
  margin:2px;
  font-weight:900;
  font-size:18px;
  color:black;
  border:1px solid #ddd;
  display:inline-block;
}
.comm-card-span { font-size: 28px !important; padding: 3px 7px !important; }

.role-badge {
  position: absolute; top: -10px; left: -10px;
  min-width: 26px; height: 26px; padding: 0 5px;
  border-radius: 14px; color: black; font-weight: 900;
  line-height: 24px; border: 1px solid #111;
  z-index: 100; font-size: 11px; background:white;
}
.role-D { background: #ffcc00; }
.role-SB { background: #9ad7ff; }
.role-BB { background: #ff8a80; }
.role-D-SB { background: linear-gradient(135deg, #ffcc00 50%, #9ad7ff 50%); font-size: 10px; }

.action-badge {
  position: absolute;
  bottom: -12px;
  background:#ffcc00;
  color:#000;
  font-weight:900;
  padding:2px 6px;
  border-radius:6px;
  font-size: 10px;
  border: 1px solid #000;
  z-index:100;
  white-space: nowrap;
}
.fold-text { color: #ff3b30; font-weight: 900; font-size: 14px; }
.folded-seat { opacity: 0.35; }

.turn-timer {
  position:absolute;
  top: -18px; left:0;
  width: 100%;
  text-align:center;
  color:#ffcc00;
  font-weight:900;
  font-size: 12px;
}

.center-overlay {
  position:absolute;
  top:45%;
  left:50%;
  transform:translate(-50%,-50%);
  text-align:center;
  color:white;
  width:100%;
  pointer-events:none;
}
.center-overlay h3 { margin: 6px 0 0 0; }
.center-msg {
  font-size:18px;
  color:#ffcc00;
  font-weight:900;
  background:rgba(0,0,0,0.70);
  padding:6px 10px;
  border-radius:10px;
  display:inline-block;
  margin-top:8px;
  border:1px solid #222;
}

.showdown-box {
  margin-top:10px;
  padding:10px 12px;
  border-radius:14px;
  background:#0b0b0c;
  border:1px solid #222;
}

.stButton>button { font-size: 14px !important; height: 42px !important; border-radius: 12px !important; }
div[data-baseweb="input"] { background-color: #111 !important; color: white; border: 1px solid #333; }
div[data-baseweb="input"] input { text-align: center; font-weight: 900; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 3) Supabase helpers
# ==========================================
@st.cache_resource
def get_supabase():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("SUPABASE_URL / SUPABASE_KEY 가 Secrets에 없습니다.")
        st.stop()
    return create_client(url, key)

sb_client = get_supabase()

def supa_get_room(room_id: str):
    try:
        res = sb_client.table("poker_rooms").select("state").eq("room_id", room_id).single().execute()
        return res.data["state"]
    except Exception:
        return None

def supa_upsert_room(room_id: str, state: dict):
    sb_client.table("poker_rooms").upsert(
        {"room_id": room_id, "state": state, "updated_at": "now()"},
        on_conflict="room_id",
    ).execute()

# ==========================================
# 4) Game state
# ==========================================
def init_game_data():
    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)

    players = []
    for i in range(MAX_SEATS):
        players.append(
            {
                "name": "빈 자리",
                "seat": i + 1,
                "stack": 0,
                "hand": [],
                "bet": 0,
                "status": "standby",
                "action": "",
                "is_human": False,
                "role": "",
                "has_acted": False,
                "style": "None",
                "entries_used": 0,   # 0이면 아직 입장 전 / 1~3까지
                "last_active": 0,
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
        "game_over_time": 0,
        "winner_info": [],
        "last_showdown_text": "",
    }

def load_data(room_id: str):
    data = supa_get_room(room_id)
    if data is None:
        data = init_game_data()
        supa_upsert_room(room_id, data)
    return data

def save_data(room_id: str, data: dict):
    supa_upsert_room(room_id, data)

# ==========================================
# 5) Hand evaluation
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

def get_hand_strength_detail(hand):
    if not hand or len(hand) < 5:
        return (-1, [], "No Hand")

    rank_map = {r: i for i, r in enumerate("..23456789TJQKA", 0)}
    ranks = sorted([rank_map[c[0]] for c in hand], reverse=True)
    suits = [c[1] for c in hand]

    flush_suit = None
    for s in ["♠", "♥", "♦", "♣"]:
        if suits.count(s) >= 5:
            flush_suit = s
            break
    is_flush = flush_suit is not None
    flush_ranks = (
        sorted([rank_map[c[0]] for c in hand if c[1] == flush_suit], reverse=True)
        if is_flush
        else []
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
        is_sf, sf_high = check_straight(flush_ranks)

    from collections import Counter

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
        return (6, [sorted_counts[0][0], sorted_counts[1][0]],
                f"풀하우스 ({r_name(sorted_counts[0][0])}, {r_name(sorted_counts[1][0])})")
    if is_flush:
        return (5, flush_ranks[:5], f"플러시 ({r_name(flush_ranks[0])})")
    if is_straight:
        return (4, [straight_high], f"스트레이트 ({r_name(straight_high)})")
    if sorted_counts[0][1] == 3:
        kickers = sorted([r for r in ranks if r != sorted_counts[0][0]], reverse=True)[:2]
        return (3, [sorted_counts[0][0]] + kickers, f"트리플 ({r_name(sorted_counts[0][0])})")
    if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
        kicker = [r for r in ranks if r != sorted_counts[0][0] and r != sorted_counts[1][0]][0]
        return (2, [sorted_counts[0][0], sorted_counts[1][0], kicker],
                f"투페어 ({r_name(sorted_counts[0][0])}, {r_name(sorted_counts[1][0])})")
    if sorted_counts[0][1] == 2:
        kickers = sorted([r for r in ranks if r != sorted_counts[0][0]], reverse=True)[:3]
        return (1, [sorted_counts[0][0]] + kickers,
                f"원페어 ({r_name(sorted_counts[0][0])}) - 킥 {r_name(kickers[0])}")
    return (0, ranks[:5], f"하이카드 ({r_name(ranks[0])}, {r_name(ranks[1])})")

# ==========================================
# 6) Game flow helpers
# ==========================================
def _active_players(players):
    return [p for p in players if p["name"] != "빈 자리" and p["status"] == "alive"]

def _seated_players(players):
    return [p for p in players if p["name"] != "빈 자리" and p["is_human"]]

def _can_stay_in_tournament(p):
    if p["name"] == "빈 자리":
        return False
    if p["stack"] > 0:
        return True
    return p.get("entries_used", 0) < 3

def ensure_auto_rebuy(players):
    # stack 0인데 entries 남아있으면 자동 리바인 (버튼 없이)
    for p in players:
        if p["name"] == "빈 자리":
            continue
        if p.get("entries_used", 0) >= 3:
            continue
        if p["stack"] == 0:
            # 다음 엔트리 지급
            next_idx = p.get("entries_used", 0)
            if next_idx < 3:
                p["stack"] = ENTRY_STACKS[next_idx]
                p["entries_used"] = next_idx + 1
                p["status"] = "folded"
                p["action"] = f"자동 리바인({p['entries_used']}/3)"
                p["has_acted"] = True

def reset_for_next_hand(old_data):
    players = old_data["players"]

    # 자동 리바인 우선 처리
    ensure_auto_rebuy(players)

    active_indices = [i for i, p in enumerate(players) if p["name"] != "빈 자리" and p["stack"] > 0]
    if len(active_indices) < 2:
        # 2명 미만이면 대기 상태로
        d = init_game_data()
        # 자리 유지(이름/엔트리 정보는 유지)
        d["players"] = players
        d["phase"] = "WAITING"
        d["msg"] = "플레이어를 기다리는 중... (최소 2명)"
        return d

    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)

    # dealer 이동
    current_d = old_data["dealer_idx"]
    new_dealer_idx = current_d
    for i in range(1, MAX_SEATS + 1):
        nxt = (current_d + i) % MAX_SEATS
        if players[nxt]["name"] != "빈 자리" and players[nxt]["stack"] > 0:
            new_dealer_idx = nxt
            break

    elapsed = time.time() - old_data["start_time"]
    lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
    sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl - 1]

    current_pot = 0

    # 카드/상태 초기화 + ante
    for p in players:
        p["bet"] = 0
        p["action"] = ""
        p["has_acted"] = False
        p["role"] = ""

        if p["name"] == "빈 자리":
            p["status"] = "standby"
            p["hand"] = []
            continue

        if p["stack"] > 0:
            p["status"] = "alive"
            p["hand"] = [deck.pop(), deck.pop()]
            if ante_amt > 0:
                actual_ante = min(p["stack"], ante_amt)
                p["stack"] -= actual_ante
                current_pot += actual_ante
        else:
            p["status"] = "folded"
            p["hand"] = []

    def find_next_alive(idx):
        for i in range(1, MAX_SEATS + 1):
            nxt = (idx + i) % MAX_SEATS
            if players[nxt]["status"] == "alive":
                return nxt
        return idx

    # SB/BB/D 배정
    if len(active_indices) == 2:
        sb_idx = new_dealer_idx
        bb_idx = find_next_alive(sb_idx)
        players[sb_idx]["role"] = "D-SB"
        players[bb_idx]["role"] = "BB"
        turn_start_idx = sb_idx
    else:
        sb_idx = find_next_alive(new_dealer_idx)
        bb_idx = find_next_alive(sb_idx)
        players[new_dealer_idx]["role"] = "D"
        players[sb_idx]["role"] = "SB"
        players[bb_idx]["role"] = "BB"
        turn_start_idx = find_next_alive(bb_idx)

    # 블라인드 납부
    if players[sb_idx]["status"] == "alive":
        pay = min(players[sb_idx]["stack"], sb_amt)
        players[sb_idx]["stack"] -= pay
        players[sb_idx]["bet"] = pay
        current_pot += pay

    if players[bb_idx]["status"] == "alive":
        pay = min(players[bb_idx]["stack"], bb_amt)
        players[bb_idx]["stack"] -= pay
        players[bb_idx]["bet"] = pay
        current_pot += pay

    return {
        "players": players,
        "pot": current_pot,
        "deck": deck,
        "community": [],
        "phase": "PREFLOP",
        "current_bet": bb_amt,
        "turn_idx": turn_start_idx,
        "dealer_idx": new_dealer_idx,
        "sb": sb_amt,
        "bb": bb_amt,
        "ante": ante_amt,
        "level": lvl,
        "start_time": old_data["start_time"],
        "msg": f"Level {lvl} 시작! (SB {sb_amt}/BB {bb_amt})",
        "turn_start_time": time.time(),
        "game_over_time": 0,
        "winner_info": [],
        "last_showdown_text": "",
    }

def pass_turn(data):
    curr = data["turn_idx"]
    players = data["players"]
    for i in range(1, MAX_SEATS + 1):
        idx = (curr + i) % MAX_SEATS
        if players[idx]["status"] == "alive" and players[idx]["stack"] > 0:
            data["turn_idx"] = idx
            break
        if players[idx]["status"] == "alive" and players[idx]["stack"] == 0:
            players[idx]["has_acted"] = True

    data["turn_start_time"] = time.time()

def check_phase_end(data):
    players = data["players"]
    active = [p for p in players if p["status"] == "alive"]

    if len(active) <= 1:
        # 전원 폴드 승리 처리
        if len(active) == 1:
            winner = active[0]
            winner["stack"] += data["pot"]
            data["winner_info"] = [{
                "name": winner["name"],
                "hand": winner.get("hand", []),
                "desc": "전원 폴드 승리"
            }]
            data["msg"] = f"🏆 {winner['name']} 승리! (전원 폴드) 🎉"
            data["last_showdown_text"] = f"SHOWDOWN - 전원 폴드 승리: {winner['name']} {''.join([make_card(c) for c in winner.get('hand', [])])}"
        data["pot"] = 0
        data["phase"] = "GAME_OVER"
        data["game_over_time"] = time.time()
        return True

    target = data["current_bet"]
    all_acted = all(p["has_acted"] for p in active)
    all_matched = all(p["bet"] == target or p["stack"] == 0 for p in active)

    if all_acted and all_matched:
        deck = data["deck"]

        if data["phase"] == "PREFLOP":
            data["phase"] = "FLOP"
            data["community"] = [deck.pop() for _ in range(3)]
        elif data["phase"] == "FLOP":
            data["phase"] = "TURN"
            data["community"].append(deck.pop())
        elif data["phase"] == "TURN":
            data["phase"] = "RIVER"
            data["community"].append(deck.pop())
        elif data["phase"] == "RIVER":
            winners = []
            best_rank = -1
            best_tie = []
            desc = ""
            for p in active:
                rank_val, tie_breaker, d_text = get_hand_strength_detail(p["hand"] + data["community"])
                if rank_val > best_rank or (rank_val == best_rank and tie_breaker > best_tie):
                    best_rank = rank_val
                    best_tie = tie_breaker
                    winners = [p]
                    desc = d_text
                elif rank_val == best_rank and tie_breaker == best_tie:
                    winners.append(p)

            split = data["pot"] // len(winners)
            for w in winners:
                w["stack"] += split

            data["winner_info"] = [{"name": w["name"], "hand": w["hand"], "desc": desc} for w in winners]
            data["msg"] = f"🏆 {', '.join([w['name'] for w in winners])} 승리! [{desc}] 🎉"
            data["last_showdown_text"] = "SHOWDOWN - " + " / ".join(
                [f"{w['name']} {''.join([make_card(c) for c in w['hand']])} ({desc})" for w in winners]
            )

            data["pot"] = 0
            data["phase"] = "GAME_OVER"
            data["game_over_time"] = time.time()
            return True

        # 다음 스트리트 준비
        data["current_bet"] = 0
        for p in players:
            p["bet"] = 0
            p["has_acted"] = False
            if p["status"] == "alive":
                p["action"] = ""

        # 다음 턴 시작(딜러 다음 살아있는 사람)
        dealer = data["dealer_idx"]
        found = False
        for i in range(1, MAX_SEATS + 1):
            idx = (dealer + i) % MAX_SEATS
            if players[idx]["status"] == "alive" and players[idx]["stack"] > 0:
                data["turn_idx"] = idx
                found = True
                break
        if not found:
            for i in range(1, MAX_SEATS + 1):
                idx = (dealer + i) % MAX_SEATS
                if players[idx]["status"] == "alive":
                    data["turn_idx"] = idx
                    break

        data["msg"] = f"{data['phase']} 시작!"
        data["turn_start_time"] = time.time()
        return True

    return False

def check_disconnection(data):
    now = time.time()
    changed = False
    players = data["players"]

    for p in players:
        if p["name"] == "빈 자리":
            continue
        last_active = p.get("last_active", 0)
        if last_active and (now - last_active) > DISCONNECT_TIMEOUT:
            # 자리 비움(강퇴)
            p["name"] = "빈 자리"
            p["stack"] = 0
            p["hand"] = []
            p["bet"] = 0
            p["status"] = "standby"
            p["action"] = "퇴장"
            p["is_human"] = False
            p["role"] = ""
            p["has_acted"] = False
            p["style"] = "None"
            p["entries_used"] = 0
            p["last_active"] = 0
            changed = True

    # 2명 미만이면 WAITING으로
    alive_cnt = len([p for p in players if p["name"] != "빈 자리" and p["stack"] > 0])
    if alive_cnt < 2 and data["phase"] != "WAITING":
        data["phase"] = "WAITING"
        data["msg"] = "플레이어 퇴장으로 게임 중단. 대기 중..."
        changed = True

    return changed

# ==========================================
# 7) Room + login
# ==========================================
st.title("🦁 AI 몬스터 토너먼트")

if "room_id" not in st.session_state:
    st.session_state["room_id"] = "friends"  # 기본 방

with st.sidebar:
    st.markdown("### 방 설정")
    room_id = st.text_input("방코드", value=st.session_state["room_id"]).strip()
    if not room_id:
        room_id = "friends"
    st.session_state["room_id"] = room_id

    st.markdown("---")
    st.caption("친구들끼리 방코드 공유해서 같이 들어오면 같은 게임을 봅니다.")

ROOM_ID = st.session_state["room_id"]

if "my_seat" not in st.session_state:
    st.subheader("입장")
    u_name = st.text_input("닉네임", value="형님")
    colA, colB = st.columns(2)

    if colA.button("입장하기", type="primary"):
        data = load_data(ROOM_ID)

        # 이미 같은 이름으로 들어와있으면 그 자리로 재접속
        target = -1
        for i, p in enumerate(data["players"]):
            if p["is_human"] and p["name"] == u_name:
                target = i
                break

        # 없으면 빈 자리 찾기(우선 4번)
        if target == -1:
            if data["players"][4]["name"] == "빈 자리":
                target = 4
            else:
                for i in range(MAX_SEATS):
                    if data["players"][i]["name"] == "빈 자리":
                        target = i
                        break

        if target != -1:
            # 엔트리 1회로 시작(6만)
            data["players"][target] = {
                "name": u_name,
                "seat": target + 1,
                "stack": ENTRY_STACKS[0],
                "hand": [],
                "bet": 0,
                "status": "folded",
                "action": "관전 대기 중",
                "is_human": True,
                "role": "",
                "has_acted": True,
                "style": "Hero" if target == 4 else "None",
                "entries_used": 1,
                "last_active": time.time(),
            }

            # 2명 이상이면 바로 시작
            active_count = len([p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0])
            if data["phase"] == "WAITING" and active_count >= 2:
                data = reset_for_next_hand(data)

            save_data(ROOM_ID, data)
            st.session_state["my_seat"] = target
            st.session_state["my_name"] = u_name
            st.rerun()

    if colB.button("서버 초기화(이 방만)"):
        d = init_game_data()
        save_data(ROOM_ID, d)
        st.rerun()

    st.stop()

# ==========================================
# 8) Main loop
# ==========================================
data = load_data(ROOM_ID)
my_seat = st.session_state.get("my_seat", -1)
my_name = st.session_state.get("my_name", "")

if my_seat < 0 or my_seat >= MAX_SEATS:
    st.error("좌석 정보가 이상합니다. 새로고침 후 재입장 해주세요.")
    st.stop()

# 내 자리가 유지되는지 확인
if data["players"][my_seat]["name"] != my_name:
    st.error("연결이 끊겼거나 자리를 뺏겼습니다. 다시 입장해줘.")
    del st.session_state["my_seat"]
    st.stop()

# last_active 갱신
data["players"][my_seat]["last_active"] = time.time()
save_data(ROOM_ID, data)

# 접속 끊김 강퇴
if check_disconnection(data):
    save_data(ROOM_ID, data)
    st.rerun()

# 자동 리바인 반영
ensure_auto_rebuy(data["players"])
save_data(ROOM_ID, data)

me = data["players"][my_seat]
curr_idx = data["turn_idx"]
curr_p = data["players"][curr_idx]

# 레벨 갱신
elapsed = time.time() - data["start_time"]
lvl = min(len(BLIND_STRUCTURE), int(elapsed // LEVEL_DURATION) + 1)
sb_amt, bb_amt, ante_amt = BLIND_STRUCTURE[lvl - 1]

# 토너먼트 생존자(스택>0 or 리바인 가능)
active_tournament = sum(1 for p in data["players"] if _can_stay_in_tournament(p))

# 평균 스택(스택>0만)
alive_p = [p for p in data["players"] if p["name"] != "빈 자리" and p["stack"] > 0]
avg_stack = (sum(p["stack"] for p in alive_p) // len(alive_p)) if alive_p else 0

# 타이머(레벨)
remain_lvl = int(LEVEL_DURATION - (elapsed % LEVEL_DURATION))
remain_mm = remain_lvl // 60
remain_ss = remain_lvl % 60

# HUD
st.markdown(
    f"""
<div class="top-hud">
  <div class="hud-left">
    <span class="pill pill-white">LV {lvl}</span>
    <span class="pill pill-white">Players {active_tournament}/{MAX_SEATS}</span>
    <span class="pill pill-red">SB {sb_amt}</span>
    <span class="pill pill-red">BB {bb_amt}</span>
    <span class="pill pill-red">Ante {ante_amt}</span>
    <span class="pill pill-red">Avg {avg_stack:,}</span>
  </div>
  <div class="hud-timer">{remain_mm:02d}:{remain_ss:02d}</div>
</div>
""",
    unsafe_allow_html=True,
)

# GAME OVER 처리
if data["phase"] == "GAME_OVER":
    rem = int(AUTO_NEXT_HAND_DELAY - (time.time() - data["game_over_time"]))
    st.info(f"게임 종료! {rem}초 후 다음 판 시작...")
    if rem <= 0:
        data = reset_for_next_hand(data)
        save_data(ROOM_ID, data)
        st.rerun()

# 턴 타이머
time_left = max(0, TURN_TIMEOUT - (time.time() - data["turn_start_time"]))
if data["phase"] not in ["WAITING", "GAME_OVER"] and time_left <= 0:
    # 시간초과 폴드
    if curr_p["status"] == "alive":
        curr_p["status"] = "folded"
        curr_p["action"] = "시간초과"
        curr_p["has_acted"] = True
        if not check_phase_end(data):
            pass_turn(data)
        save_data(ROOM_ID, data)
        st.rerun()

# WAITING
if data["phase"] == "WAITING":
    st.info("다른 플레이어 입장을 기다리는 중입니다. (최소 2명)")
    # 테이블 렌더
    html = '<div class="game-board-container"><div class="poker-table"></div>'
    for i in range(MAX_SEATS):
        p = data["players"][i]
        if p["name"] == "빈 자리":
            html += f'<div class="seat pos-{i}" style="opacity:0.2;"><div>빈 자리</div></div>'
        else:
            hero = "hero-seat" if i == my_seat else ""
            html += f'<div class="seat pos-{i} {hero}"><div><b>{p["name"]}</b></div><div>{int(p["stack"]):,}</div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    time.sleep(AUTO_REFRESH_SEC)
    st.rerun()

# ==========================================
# 9) UI layout
# ==========================================
col_table, col_controls = st.columns([1.55, 1])

# winners for effect
winner_names = set()
if data.get("winner_info"):
    for w in data["winner_info"]:
        winner_names.add(w["name"])

with col_table:
    html = '<div class="game-board-container"><div class="poker-table"></div>'

    comm = "".join([make_comm_card(c) for c in data["community"]])

    for i in range(MAX_SEATS):
        p = data["players"][i]
        if p["name"] == "빈 자리":
            html += f'<div class="seat pos-{i}" style="opacity:0.2;"><div>빈 자리</div></div>'
            continue

        active_cls = "active-turn" if i == curr_idx and data["phase"] not in ["GAME_OVER", "WAITING"] else ""
        hero_cls = "hero-seat" if i == my_seat else ""
        winner_cls = "winner-seat" if (data["phase"] == "GAME_OVER" and p["name"] in winner_names) else ""

        timer_html = ""
        if i == curr_idx and data["phase"] not in ["GAME_OVER", "WAITING"]:
            timer_html = f'<div class="turn-timer">{int(time_left)}s</div>'

        # 카드 표시: 내 카드 or GAME_OVER 시 살아있던 사람 오픈
        cards = "<div style='font-size:16px;'>🂠 🂠</div>"
        folded_cls = ""
        if p["status"] == "folded":
            cards = "<div class='fold-text'>FOLD</div>"
            folded_cls = "folded-seat"
        else:
            if i == my_seat or (data["phase"] == "GAME_OVER" and p["status"] != "folded"):
                if p["hand"]:
                    cards = f"<div>{make_card(p['hand'][0])}{make_card(p['hand'][1])}</div>"

        role = p.get("role", "")
        role_cls = "role-D-SB" if role == "D-SB" else f"role-{role}"
        role_div = f"<div class='role-badge {role_cls}'>{role}</div>" if role else ""

        action_text = p.get("action", "")
        if not action_text:
            action_text = " "
        action_div = f"<div class='action-badge'>{action_text}</div>"

        html += (
            f'<div class="seat pos-{i} {active_cls} {hero_cls} {winner_cls} {folded_cls}">'
            f"{timer_html}{role_div}"
            f"<div><b>{p['name']}</b></div>"
            f"<div>{int(p['stack']):,}</div>"
            f"{cards}"
            f"{action_div}"
            "</div>"
        )

    center = (
        f"<div class='center-overlay'>"
        f"<div>{comm}</div>"
        f"<h3>Pot: {data['pot']:,}</h3>"
        f"<div class='center-msg'>{data['msg']}</div>"
        f"</div>"
    )
    html += center + "</div>"
    st.markdown(html, unsafe_allow_html=True)

    # Showdown details under board
    if data["phase"] == "GAME_OVER" and data.get("winner_info"):
        lines = []
        lines.append("<div class='showdown-box'>")
        lines.append("<div style='font-weight:900; color:#34c759; font-size:14px;'>SHOWDOWN</div>")
        for w in data["winner_info"]:
            hand_html = "".join([make_card(c) for c in w.get("hand", [])])
            lines.append(
                f"<div style='margin-top:6px; font-size:14px;'>"
                f"<b style='color:#ffcc00;'>{w['name']}</b> "
                f"{hand_html} "
                f"<span style='color:#eaeaea;'>- {w.get('desc','')}</span>"
                f"</div>"
            )
        lines.append("</div>")
        st.markdown("".join(lines), unsafe_allow_html=True)

with col_controls:
    # 내 카드 표시
    if me.get("hand"):
        st.markdown("### 내 카드")
        st.markdown("".join([make_card(c) for c in me["hand"]]), unsafe_allow_html=True)
    else:
        st.markdown("### 내 카드")

    # 서버 초기화
    if st.button("서버 초기화(이 방)", use_container_width=True):
        d = init_game_data()
        save_data(ROOM_ID, d)
        st.rerun()

    st.markdown("---")

    # 액션 패널
    if data["phase"] not in ["GAME_OVER", "WAITING"]:
        if curr_idx == my_seat and me["status"] == "alive":
            st.success(f"내 차례! ({int(time_left)}초)")

            to_call = data["current_bet"] - me["bet"]
            if to_call < 0:
                to_call = 0

            c1, c2 = st.columns(2)

            check_label = "체크/콜"
            if data["phase"] == "PREFLOP" and to_call == 0 and ("BB" in me.get("role", "") or "SB" in me.get("role", "") or "D-SB" in me.get("role", "")):
                check_label = "체크 (옵션)"

            if c1.button(check_label, use_container_width=True):
                data = load_data(ROOM_ID)
                me = data["players"][my_seat]

                to_call2 = max(0, data["current_bet"] - me["bet"])
                pay = min(to_call2, me["stack"])
                me["stack"] -= pay
                me["bet"] += pay
                data["pot"] += pay
                me["has_acted"] = True
                me["action"] = "체크" if pay == 0 else f"콜({pay})"

                if not check_phase_end(data):
                    pass_turn(data)

                save_data(ROOM_ID, data)
                st.rerun()

            if c2.button("폴드", type="primary", use_container_width=True):
                data = load_data(ROOM_ID)
                me = data["players"][my_seat]

                me["status"] = "folded"
                me["has_acted"] = True
                me["action"] = "폴드"

                if not check_phase_end(data):
                    pass_turn(data)

                save_data(ROOM_ID, data)
                st.rerun()

            if st.button("ALL-IN", use_container_width=True):
                data = load_data(ROOM_ID)
                me = data["players"][my_seat]

                pay = me["stack"]
                me["stack"] = 0
                me["bet"] += pay
                data["pot"] += pay
                me["has_acted"] = True
                me["action"] = "올인!"

                if me["bet"] > data["current_bet"]:
                    data["current_bet"] = me["bet"]
                    # 레이즈가 나왔으니 다른 사람 다시 행동
                    for p in data["players"]:
                        if p != me and p["status"] == "alive" and p["stack"] > 0:
                            p["has_acted"] = False

                if not check_phase_end(data):
                    pass_turn(data)

                save_data(ROOM_ID, data)
                st.rerun()

            st.markdown("---")

            # Raise UI: min raise = max(current_bet*2, bb*2) (프리플랍 포함)
            min_raise = max(data["current_bet"] * 2, bb_amt * 2)
            max_raise = me["stack"] + me["bet"]

            if max_raise >= min_raise and me["stack"] > to_call:
                step_val = 1000 if sb_amt >= 1000 else 100

                # 기본값: 최소 레이즈(2배)
                default_raise = min_raise

                raise_val = st.number_input(
                    "레이즈/베팅 (총액 기준)",
                    min_value=int(min_raise),
                    max_value=int(max_raise),
                    value=int(default_raise),
                    step=int(step_val),
                )

                if st.button("레이즈 확정", use_container_width=True):
                    data = load_data(ROOM_ID)
                    me = data["players"][my_seat]

                    pay = raise_val - me["bet"]
                    pay = max(0, min(pay, me["stack"]))
                    me["stack"] -= pay
                    me["bet"] += pay
                    data["pot"] += pay
                    data["current_bet"] = me["bet"]
                    me["has_acted"] = True
                    me["action"] = f"레이즈({me['bet']})"

                    for p in data["players"]:
                        if p != me and p["status"] == "alive" and p["stack"] > 0:
                            p["has_acted"] = False

                    if not check_phase_end(data):
                        pass_turn(data)

                    save_data(ROOM_ID, data)
                    st.rerun()
            else:
                st.info("레이즈 불가(칩 부족 또는 콜 올인 상태)")

        else:
            # 내 차례가 아니면 상태 표시
            st.info(f"{curr_p['name']} 플레이 중... ({int(time_left)}s)")

# 마지막 자동 갱신
time.sleep(AUTO_REFRESH_SEC)
st.rerun()
