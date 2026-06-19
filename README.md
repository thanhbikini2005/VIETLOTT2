# 🎯 Vietlott Simulator Bot

Bot giả lập so sánh phương pháp chọn số: **Bạn (thống kê)** vs **Claude (trực giác máy)**

---

## 📁 Cấu trúc

```
vietlott-bot/
├── vietlott_bot.py          # Script chính - phân tích & gửi số dự đoán
├── update_score.py          # Script cập nhật điểm sau khi có kết quả thật
├── tracking.json            # Lưu điểm tích lũy (tự động cập nhật)
├── last_picks.json          # Số đã chọn hôm qua (để so kết quả)
└── .github/workflows/
    └── vietlott.yml         # Tự động chạy 2 lần/ngày
```

---

## ⚙️ Setup (5 bước)

### 1. Tạo repo GitHub mới
Tạo repo tên `vietlott-bot` (private hoặc public tuỳ bạn), upload toàn bộ files này lên.

### 2. Thêm Secrets vào GitHub
Vào repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret name | Giá trị |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token bot của bạn (từ @BotFather) |
| `TELEGRAM_CHAT_ID` | Chat ID của bạn |

### 3. Cấp quyền write cho Actions
Vào repo → **Settings** → **Actions** → **General** → **Workflow permissions**
→ Chọn **Read and write permissions** → Save

### 4. Kích hoạt workflow
Vào tab **Actions** → chọn workflow → **Enable**

### 5. Test ngay
Vào **Actions** → **Vietlott Simulator Bot** → **Run workflow** → chọn `predict` → Run

---

## 🕐 Lịch chạy tự động

| Thời gian (ICT) | Việc làm |
|---|---|
| 8:00 SA mỗi ngày | Gửi số dự đoán cho ngày hôm đó |
| 9:00 SA mỗi ngày | So kết quả hôm qua, cập nhật điểm |

---

## 🏅 Hệ thống tính điểm

| Kết quả | Điểm |
|---|---|
| Trúng Jackpot (tất cả số) | 10 điểm |
| Trúng giải phụ (thiếu 1 số) | 3 điểm |
| Đúng 3 số trở lên | 1 điểm |
| Ít hơn 3 số | 0 điểm |

---

## 📊 Logic chọn số

**Bạn (thống kê):** Dựa trên tần suất xuất hiện 50 kỳ gần nhất — ưu tiên số "nóng" kết hợp số "lạnh đang chờ thời"

**Claude (trực giác):** Phân tích số "đang ngủ" (có trong 30 kỳ nhưng vắng 10 kỳ gần), cân bằng chẵn/lẻ, trải đều nhóm thấp/giữa/cao

---

## ⚠️ Lưu ý
- Đây là **giả lập thuần tuý** để so sánh phương pháp
- Không có công thức nào thực sự dự đoán được xổ số ngẫu nhiên
- Dùng để vui và kiểm chứng trực giác vs thống kê thôi nhé!
