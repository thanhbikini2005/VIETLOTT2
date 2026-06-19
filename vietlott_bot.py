import os
import json
import random
import requests
from datetime import datetime, timedelta
from collections import Counter
import pytz

ICT = pytz.timezone("Asia/Ho_Chi_Minh")
NOW = datetime.now(ICT)
TODAY_STR = NOW.strftime("%d/%m/%Y")
DOW = NOW.strftime("%A")  # Monday, Tuesday...
WEEKDAY_VI = {
    "Monday": "Thứ Hai", "Tuesday": "Thứ Ba", "Wednesday": "Thứ Tư",
    "Thursday": "Thứ Năm", "Friday": "Thứ Sáu", "Saturday": "Thứ Bảy", "Sunday": "Chủ Nhật"
}
TODAY_VI = WEEKDAY_VI.get(DOW, DOW)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
TRACKING_FILE = "tracking.json"

# ── Helpers ──────────────────────────────────────────────────────────────────

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=15)
    r.raise_for_status()

def load_tracking() -> dict:
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "score_ban": 0, "score_claude": 0,
        "history": [], "streak_ban": 0, "streak_claude": 0
    }

def save_tracking(data: dict):
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Fetch data từ Vietlott API ────────────────────────────────────────────────

def fetch_vietlott(product_id: str, count: int = 50) -> list[dict]:
    """
    Fetch lịch sử kết quả từ API công khai của Vietlott.
    product_id: 'mega645' | 'power655' | 'max3dplus' | 'lotto535'
    """
    url = f"https://api.vietlott.vn/api/trung-thuong/index"
    headers = {"Content-Type": "application/json", "Referer": "https://vietlott.vn/"}
    payload = {
        "ProductType": _product_type(product_id),
        "PageIndex": 0,
        "PageSize": count,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("Data", [])
    except Exception as e:
        print(f"[WARN] Fetch {product_id} lỗi: {e}")
        return []

def _product_type(pid: str) -> int:
    return {"mega645": 0, "power655": 1, "max3dplus": 5, "lotto535": 7}.get(pid, 0)

def parse_numbers(raw_list: list) -> list[list[int]]:
    """Trả về list các bộ số đã quay."""
    result = []
    for item in raw_list:
        nums = item.get("DrawResult", []) or item.get("Result", [])
        if nums:
            try:
                result.append([int(n) for n in nums if n is not None])
            except Exception:
                pass
    return result

# ── Phân tích thống kê (công thức CỦA BẠN) ───────────────────────────────────

def analyze_frequency(draws: list[list[int]], n_top: int = 15) -> list[int]:
    """Tần suất xuất hiện — trả về top N số hay ra nhất."""
    counter = Counter()
    for draw in draws:
        counter.update(draw)
    return [num for num, _ in counter.most_common(n_top)]

def pick_by_stats(draws: list[list[int]], choose: int, max_num: int) -> list[int]:
    """
    Công thức của bạn:
    - 2 số hay ra nhất (con đầu/cuối theo tần suất)
    - 2 số nhóm giữa hay ra
    - 2 số 'lạnh' (ít ra gần đây) — chờ thời cơ
    """
    if not draws:
        return sorted(random.sample(range(1, max_num + 1), choose))

    freq = analyze_frequency(draws, n_top=max_num)
    hot = freq[:8]
    cold = freq[-8:]

    selected = set()
    # 3 hot
    for n in random.sample(hot, min(3, len(hot))):
        selected.add(n)
    # 2 cold (chờ thời)
    for n in random.sample(cold, min(2, len(cold))):
        selected.add(n)
    # fill ngẫu nhiên còn lại
    pool = [x for x in range(1, max_num + 1) if x not in selected]
    while len(selected) < choose:
        selected.add(random.choice(pool))

    return sorted(selected)

def pick_by_claude(draws: list[list[int]], choose: int, max_num: int) -> list[int]:
    """
    Logic của Claude:
    - Phân tích khoảng cách giữa các số trong các lần trúng gần nhất
    - Ưu tiên số chưa xuất hiện trong 10 kỳ gần nhất nhưng trong 30 kỳ có ra
    - Cân bằng số chẵn/lẻ (tỉ lệ 3:3 hoặc 2:4)
    - Trải đều theo nhóm (thấp/giữa/cao)
    """
    if not draws:
        return sorted(random.sample(range(1, max_num + 1), choose))

    recent_10 = set(n for draw in draws[:10] for n in draw)
    appeared_30 = set(n for draw in draws[:30] for n in draw)

    # Số "đang ngủ" — trong 30 kỳ có ra nhưng 10 kỳ gần chưa thấy
    sleeping = [n for n in appeared_30 if n not in recent_10]
    # Chia nhóm thấp/giữa/cao
    third = max_num // 3
    low   = [n for n in range(1, third + 1)]
    mid   = [n for n in range(third + 1, 2 * third + 1)]
    high  = [n for n in range(2 * third + 1, max_num + 1)]

    selected = set()
    # Mỗi nhóm ít nhất 1 số
    for group in [low, mid, high]:
        candidates = [n for n in sleeping if n in group] or group
        selected.add(random.choice(candidates))

    # Fill còn lại — xen kẽ chẵn/lẻ
    pool = [x for x in range(1, max_num + 1) if x not in selected]
    odds  = [x for x in pool if x % 2 == 1]
    evens = [x for x in pool if x % 2 == 0]
    while len(selected) < choose:
        src = odds if len([x for x in selected if x % 2 == 1]) < choose // 2 else evens
        if not src:
            src = pool
        n = random.choice(src)
        selected.add(n)
        pool = [x for x in pool if x != n]
        odds  = [x for x in odds  if x != n]
        evens = [x for x in evens if x != n]

    return sorted(selected)

# ── Chọn số cho từng loại ────────────────────────────────────────────────────

def get_picks_for(product_id: str, choose: int, max_num: int) -> dict:
    draws_raw = fetch_vietlott(product_id, count=50)
    draws = parse_numbers(draws_raw)
    last_result = draws[0] if draws else []
    last_date = draws_raw[0].get("DrawDate", "?")[:10] if draws_raw else "?"

    ban   = pick_by_stats(draws, choose, max_num)
    claude = pick_by_claude(draws, choose, max_num)
    return {
        "ban": ban,
        "claude": claude,
        "last_result": last_result,
        "last_date": last_date,
        "draws_count": len(draws),
    }

# ── Xác định hôm nay quay gì ─────────────────────────────────────────────────

def games_today() -> list[str]:
    """Trả về danh sách game quay hôm nay."""
    wd = NOW.weekday()  # 0=Mon ... 6=Sun
    games = []
    # Mega 6/45: Thứ 4 (2), Thứ 6 (4), Chủ Nhật (6)
    if wd in (2, 4, 6):
        games.append("mega645")
    # Power 6/55: Thứ 3 (1), Thứ 5 (3), Thứ 7 (5)
    if wd in (1, 3, 5):
        games.append("power655")
    # Max 3D+: Thứ 2 (0), Thứ 4 (2), Thứ 6 (4)
    if wd in (0, 2, 4):
        games.append("max3dplus")
    # Lotto 5/35: hàng ngày
    games.append("lotto535")
    return games

# ── Tạo nội dung tin nhắn ────────────────────────────────────────────────────

GAME_INFO = {
    "mega645":  {"name": "MEGA 6/45",   "emoji": "🟡", "schedule": "T4, T6, CN"},
    "power655": {"name": "POWER 6/55",  "emoji": "🟠", "schedule": "T3, T5, T7"},
    "max3dplus":{"name": "MAX 3D+",     "emoji": "🟢", "schedule": "T2, T4, T6"},
    "lotto535": {"name": "LOTTO 5/35",  "emoji": "🟣", "schedule": "Hàng ngày"},
}

GAME_CONFIG = {
    "mega645":   {"choose": 6, "max_num": 45},
    "power655":  {"choose": 6, "max_num": 55},
    "max3dplus": {"choose": 2, "max_num": 999},  # 2 bộ 3 chữ số
    "lotto535":  {"choose": 5, "max_num": 35},
}

def format_nums(nums: list[int], pid: str) -> str:
    if pid == "max3dplus":
        # 2 số 3 chữ số
        return " - ".join(f"{n:03d}" for n in nums[:2])
    return " - ".join(f"{n:02d}" for n in nums)

def build_message(tracking: dict) -> str:
    lines = []
    lines.append(f"🎯 <b>VIETLOTT SIMULATOR</b>")
    lines.append(f"📅 {TODAY_VI}, {TODAY_STR}")
    lines.append("")

    today_games = games_today()
    all_picks = {}

    for pid in ["mega645", "power655", "max3dplus", "lotto535"]:
        info = GAME_INFO[pid]
        cfg  = GAME_CONFIG[pid]
        is_today = pid in today_games

        picks = get_picks_for(pid, cfg["choose"], cfg["max_num"])
        all_picks[pid] = picks

        status = "🔔 Quay hôm nay!" if is_today else f"📆 {info['schedule']}"
        lines.append(f"{info['emoji']} <b>{info['name']}</b>  |  {status}")
        lines.append(f"   📌 Kỳ cuối ({picks['last_date']}): {format_nums(picks['last_result'], pid) if picks['last_result'] else 'N/A'}")
        lines.append(f"   👤 Bạn:   <b>{format_nums(picks['ban'], pid)}</b>")
        lines.append(f"   🤖 Claude: <b>{format_nums(picks['claude'], pid)}</b>")
        lines.append("")

    # Bảng điểm
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 <b>BẢNG ĐUA ĐIỂM</b>")
    lines.append(f"👤 Bạn:    <b>{tracking['score_ban']} điểm</b>")
    lines.append(f"🤖 Claude: <b>{tracking['score_claude']} điểm</b>")
    diff = tracking['score_ban'] - tracking['score_claude']
    if diff > 0:
        lines.append(f"🏆 Bạn đang dẫn <b>{diff} điểm</b>!")
    elif diff < 0:
        lines.append(f"🏆 Claude đang dẫn <b>{abs(diff)} điểm</b>!")
    else:
        lines.append("🤝 Đang hoà!")
    lines.append("")
    lines.append("🏅 Trúng Jackpot=10đ | Giải phụ=3đ | 3 số đúng=1đ")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("⚠️ <i>Giả lập thuần tuý — không khuyến khích đánh tiền thật</i>")

    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tracking = load_tracking()
    msg = build_message(tracking)
    send_telegram(msg)
    print("✅ Đã gửi tin nhắn Telegram thành công!")
    print(f"   Điểm: Bạn={tracking['score_ban']} | Claude={tracking['score_claude']}")

if __name__ == "__main__":
    main()
