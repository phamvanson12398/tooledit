# Nhiệm vụ: VIẾT KỊCH BẢN MỚI + CHỌN CẢNH cho video "bán content" — {{language_name}}, {{market}} (video số {{video_index}})

Chủ dự án tải lên một video gốc ngắn (~{{source_s}} giây). BẠN TỰ xem kỹ nội dung gốc (khung hình + lời nói gốc nếu có)
để hiểu video nói / cho thấy gì, rồi tự chọn góc kể hấp dẫn nhất và dựng lại thành MỘT video TikTok MỚI dài khoảng
**{{target_s}} giây**:
- TOÀN BỘ âm thanh gốc bị bỏ. Âm thanh mới = giọng đọc kịch bản của bạn (chủ dự án thu / AI đọc) + nhạc nền mới.
- Hình = các cảnh cắt từ video gốc, ĐƯỢC ĐẢO THỨ TỰ cho khớp lời dẫn, được dùng lại một cảnh khi cần (tool tự lấy khúc
  khác + phản chiếu cho khỏi lộ lặp) — nhưng hạn chế dùng lại, ưu tiên cảnh chưa dùng.
- Tool sẽ đo độ dài từng câu voice thật rồi cắt các cảnh bạn chọn cho dài đúng bằng câu (cảnh ngắn thì làm chậm nhẹ /
  ghép thêm cảnh khác). Bạn không cần tính giây cho từng cảnh trên màn hình.

## Định hướng nội dung (bạn tự xác định từ nội dung gốc)
{{brief}}
- Video về sản phẩm / món ăn / quán / dịch vụ / địa điểm → giới thiệu cho người xem muốn thử, muốn mua, muốn ghé.
- Video kể chuyện / khoảnh khắc / mẹo / kiến thức → kể lại cuốn hơn, rõ ý hơn bản gốc.
- Viết góc kể đã chọn vào đầu `outline_vi` (vd "Góc kể: giới thiệu quán mì — nhấn nước dùng, sợi mì kéo tay").

## Phụ đề / chữ trên màn hình của video gốc
{{onscreen}}

## Cấu trúc kịch bản
1. Viết `outline_vi` (tiếng Việt) TRƯỚC: mở đầu thu hút → nội dung chính (2–4 ý, nối nhau mạch lạc) → kết / kêu gọi hành
   động (nếu cần).
2. `lines[0]` có `role: "hook"`: câu mở đầu THU HÚT ngay giây đầu (câu hỏi gây tò mò, con số / chi tiết lạ, tương phản,
   vấn đề người xem đang gặp…), đọc ≤ 3–4 giây, chạy trên cảnh MẠNH NHẤT của video (không nhất thiết là cảnh đầu).
3. Các câu `role: "body"`: nội dung mạch lạc, mỗi câu một ý, nối nhau tự nhiên; câu nào nói về gì thì cảnh dưới câu đó
   phải THẤY đúng thứ đó.
4. `role: "cta"` — lời kêu gọi hành động, CHỈ khi nội dung cần (giới thiệu sản phẩm / quán / dịch vụ, xin follow…),
   đặt ở CUỐI, 1–2 câu, tự nhiên, không ép. Kiểu được dùng: follow, bình luận, lưu video, "link ở bio", "giỏ hàng TikTok".
   KHÔNG nhắc nền tảng khác ngoài TikTok (YouTube, Instagram, subscribe/구독/チャンネル登録…). Nội dung không cần thì
   không có câu cta, câu cuối khép lại gọn.

## Viết lời
- Văn NÓI tự nhiên của người bản xứ {{language_name}} làm TikTok cho khán giả nước mình — không dịch từ tiếng Việt, không
  văn viết; câu dài ngắn xen kẽ, không lặp cùng từ nối ở nhiều câu liền.
- ĐÚNG SỰ THẬT: chỉ nói điều thấy trong khung hình hoặc nghe trong lời nói gốc. Không bịa tên quán / thương hiệu, công
  dụng, giá, địa chỉ, số liệu, cam kết ("chữa khỏi", "100%", "rẻ nhất"…) mà video gốc không có. Không chửi thề.
- Độ dài: cả bài đọc khoảng **{{target_s}} giây** ở tốc độ giọng ~{{cps}} chữ/giây → khoảng **{{target_chars}} chữ**
  (không tính dấu cách, dấu câu). Tool đếm và bắt viết lại nếu thiếu / thừa. Giọng đọc phải PHỦ KÍN video từ đầu tới
  cuối — thiếu chữ là video có khoảng chỉ còn nhạc, rất dở: thà đủ ý, đủ chi tiết còn hơn viết cụt. Mỗi phần tử `lines` là 1 câu (hoặc 2 câu
  rất ngắn), đọc khoảng 2–7 giây.
- `text_vi` = nghĩa tiếng Việt; `shots_vi` = các cảnh dưới câu có gì (tiếng Việt, ngắn).

## Chọn cảnh (`shots`)
- Mỗi câu 1–3 cảnh, ghi giây GỐC `start`–`end`, nằm TRỌN trong một cảnh của danh sách "Các cảnh" bên dưới (không vắt qua
  điểm đổi cảnh — trừ khi video gốc tự cắt cảnh rất dày, cảnh < 2–3 giây, như video game / montage), mỗi cảnh ≥ 1 giây. Thứ tự trong `shots` = thứ tự hiện trên màn hình.
- Được lấy cảnh ở BẤT KỲ đâu trong video gốc và đảo thứ tự tùy ý cho khớp lời.
- Tổng độ dài các cảnh của một câu nên ≥ thời gian đọc câu đó (thiếu thì tool làm chậm nhẹ / thêm cảnh khác).
- Rải cảnh cho đều: cố dùng hết các cảnh đẹp của video; 2 câu liền nhau không dùng cùng một cảnh.
- Tránh cảnh mờ, rung, có chữ / logo của người khác, đoạn vi phạm chính sách (xem "Điều cấm").

## Tiêu đề và nhạc
- `titles_top`: 2 dòng tiêu đề CHỮ RẤT TO cố định phía trên video, ngôn ngữ đích, mỗi dòng ≤ {{title_max}} ký tự, gây tò
  mò, đúng nội dung (không spoil hết, không nhắc nền tảng khác).
- `music`: chọn một bài trong danh sách nhạc (đúng tên) hợp không khí; không bài nào hợp thì `name: null`.

{{localize_brief}}

## Góp ý của chủ dự án
{{feedback}}

## Điều cấm
{{sensitive_notes}}
{{policy_cuts}}

## Tóm tắt nội dung video gốc
{{summary}}

## Nhạc có sẵn
{{music_list}}

## Các cảnh trong video gốc (giây gốc)
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc (nếu có — để hiểu nội dung, lấy thông tin thật như tên, giá… KHÔNG dịch lại từng câu)
{{transcript}}
