"""
update_score.py
Chạy sau kỳ quay (ngày hôm sau lúc 8:00) để so kết quả thật vs số đã chọn.
Tự động cộng điểm và gửi báo cáo về Telegram.
"""
import os, json, requests
from datetime import datetime, timedelta
from collections import Counter
import pytz

ICT = pytz.timezone("Asia/Ho_Chi_Minh")
NOW = datetime.now(ICT)
YESTERDAY = (NOW - timedelta(days=1)).strftime("%d/%m/%Y")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
TRACKING_FILE = "tracking.json"
PICKS_FILE    = "last_picks.json"

def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15
    ).raise_for_status()

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_latest(product_type: int) -> list[int]:
    try:
        r = requests.post(
            "https://api.vietlott.vn/api/trung-thuong/index",
            json={"ProductType": product_type, "PageIndex": 0, "PageSize": 1},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        data = r.json().get("Data", [])
        if data:
            return [int(n) for n in data[0].get("DrawResult", []) if n]
    except Exception as e:
        print(f"Lỗi fetch: {e}")
    return []

PRODUCT_TYPES = {
    "mega645": 0, "power655": 1, "max3dplus": 5, "lotto535": 7
}
GAME_NAMES = {
    "mega645": "MEGA 6/45", "power655": "POWER 6/55",
    "max3dplus": "MAX 3D+", "lotto535": "LOTTO 5/35"
}

def score_match(picks: list[int], result: list[int]) -> tuple[int, str]:
    """Tính điểm dựa trên số lượng khớp."""
    matched = len(set(picks) & set(result))
    total = len(result)
    if matched == total:
        return 10, f"🎉 JACKPOT! {matched}/{total} số"
    elif matched >= total - 1:
        return 3, f"🥈 Giải phụ! {matched}/{total} số"
    elif matched >= 3:
        return 1, f"✅ {matched}/{total} số đúng"
    else:
        return 0, f"❌ {matched}/{total} số đúng"

def main():
    tracking = load_json(TRACKING_FILE) or {
        "score_ban": 0, "score_claude": 0, "history": []
    }
    picks_data = load_json(PICKS_FILE)

    if not picks_data:
        print("Không có picks hôm qua để check.")
        return

    lines = [f"📋 <b>KẾT QUẢ HÔM QUA</b> — {YESTERDAY}", ""]

    for pid, ptype in PRODUCT_TYPES.items():
        if pid not in picks_data:
            continue
        result = fetch_latest(ptype)
        if not result:
            lines.append(f"⚠️ {GAME_NAMES[pid]}: Không lấy được kết quả")
            continue

        pick_ban    = picks_data[pid]["ban"]
        pick_claude = picks_data[pid]["claude"]
        result_str  = " - ".join(f"{n:02d}" for n in result)

        pts_ban,    desc_ban    = score_match(pick_ban, result)
        pts_claude, desc_claude = score_match(pick_claude, result)

        tracking["score_ban"]    += pts_ban
        tracking["score_claude"] += pts_claude

        lines.append(f"{'🟡' if pid=='mega645' else '🟠' if pid=='power655' else '🟢' if pid=='max3dplus' else '🟣'} <b>{GAME_NAMES[pid]}</b>")
        lines.append(f"   📌 Kết quả: <b>{result_str}</b>")
        lines.append(f"   👤 Bạn:    {desc_ban} (+{pts_ban}đ)")
        lines.append(f"   🤖 Claude: {desc_claude} (+{pts_claude}đ)")
        lines.append("")

    # Cập nhật lịch sử
    tracking.setdefault("history", []).append({
        "date": YESTERDAY,
        "score_ban": tracking["score_ban"],
        "score_claude": tracking["score_claude"]
    })
    save_json(TRACKING_FILE, tracking)

    # Tổng kết
    diff = tracking["score_ban"] - tracking["score_claude"]
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Tổng: Bạn <b>{tracking['score_ban']}đ</b> vs Claude <b>{tracking['score_claude']}đ</b>")
    if diff >= 2:
        lines.append(f"🏆 Bạn dẫn {diff} điểm — Claude bắt đầu lo rồi đây! 😅")
    elif diff <= -2:
        lines.append(f"🤖 Claude dẫn {abs(diff)} điểm — Máy móc đang thắng! 😄")
    else:
        lines.append("🤝 Sát nút! Ngày mai ai thắng?")

    send_telegram("\n".join(lines))
    print("✅ Đã cập nhật điểm và gửi báo cáo!")

if __name__ == "__main__":
    main()
