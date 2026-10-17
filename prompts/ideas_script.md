# Nhiệm vụ: VIẾT KỊCH BẢN + CHỌN CẢNH cho một short theo Ý TƯỞNG đã chọn — {{language_name}}, {{market}} (video số {{video_index}})

Chủ dự án có một video dài làm KHO CẢNH và đã chọn ý tưởng dưới đây. Dựng thành MỘT video TikTok MỚI dài khoảng
**{{target_s}} giây**:
- TOÀN BỘ âm thanh gốc bị bỏ. Âm thanh mới = giọng đọc kịch bản của bạn + nhạc nền mới.
- Hình = các cảnh trong danh sách "Các cảnh dùng được" (≈{{footage_s}} giây cảnh), xếp theo thứ tự hợp lời dẫn
  (không cần theo thứ tự gốc). Tool đo voice thật từng câu rồi cắt cảnh cho dài đúng bằng câu.

## Ý tưởng
{{idea}}
Video phải ĐỨNG MỘT MÌNH, không nhắc "video gốc" / "vlog" / "phần tiếp theo".

## Phụ đề / chữ trên màn hình của video gốc
{{onscreen}}

## Cấu trúc kịch bản
1. Viết `outline_vi` (tiếng Việt) TRƯỚC: mở đầu thu hút → nội dung chính theo ý tưởng (các ý nối nhau mạch lạc, kiểu top
   list thì đánh số rõ) → kết gọn / kêu gọi hành động (nếu cần).
2. `lines[0]` có `role: "hook"`: câu mở đầu THU HÚT ngay giây đầu, đọc ≤ 3–4 giây, chạy trên cảnh MẠNH NHẤT.
3. Các câu `role: "body"`: mỗi câu một ý; câu nói về gì thì cảnh dưới câu đó phải THẤY đúng thứ đó.
4. `role: "cta"` CHỈ khi hợp (follow, lưu video, bình luận…), ở CUỐI, 1–2 câu, không ép. Không nhắc nền tảng khác ngoài
   TikTok.

## Viết lời
- Văn NÓI tự nhiên của người bản xứ {{language_name}} làm TikTok cho khán giả nước mình — không dịch từ tiếng Việt.
- ĐÚNG SỰ THẬT: nói điều THẤY trong cảnh / NGHE trong lời nói gốc; kiến thức chung chỉ khi phổ biến và chắc chắn đúng.
  KHÔNG bịa tên quán / địa danh / giá / số liệu / năm tháng không có trong video và bạn không chắc — thà nói chung chung
  ("một ngôi đền cổ", "giá khá mềm") còn hơn nói sai. Không cam kết quá sự thật, không chửi thề.
- Độ dài: cả bài đọc khoảng **{{target_s}} giây** ở tốc độ ~{{cps}} chữ/giây → khoảng **{{target_chars}} chữ** (không tính
  dấu cách, dấu câu). Tool đếm và bắt viết lại nếu thiếu / thừa. Giọng đọc phải PHỦ KÍN video. Mỗi phần tử `lines` là 1
  câu (hoặc 2 câu rất ngắn), đọc khoảng 2–7 giây.
- `keyword` = CHỮ NHẤN của câu (≤ {{title_max}} ký tự, ngôn ngữ đích, có trong câu); khoảng một nửa số câu có, câu mở đầu
  nên có.
- `text_vi` = nghĩa tiếng Việt; `shots_vi` = các cảnh dưới câu có gì (tiếng Việt, ngắn).

## Chọn cảnh (`shots`)
- Mỗi câu 1–3 cảnh, giây GỐC `start`–`end`, nằm TRỌN trong MỘT cảnh của danh sách "Các cảnh dùng được" (không lấy cảnh
  ngoài danh sách), mỗi cảnh ≥ 1 giây. Thứ tự trong `shots` = thứ tự hiện trên màn hình.
- Tổng độ dài các cảnh của một câu nên ≥ thời gian đọc câu đó.
- Rải cảnh cho đều, dùng nhiều cảnh khác nhau; 2 câu liền nhau không dùng cùng một cảnh.
- TRÁNH các đoạn short khác của chủ dự án đã dùng: {{used}} (chỉ dùng lại khi thật cần).
- Tránh cảnh mờ, rung, có chữ / logo của người khác, đoạn vi phạm chính sách (xem "Điều cấm").

## Kho cảnh chung (CHỈ dùng khi video gốc thiếu cảnh khớp lời)
Các cảnh đẹp tool đã lưu từ video khác (mã, độ dài, mô tả). Câu nào video gốc KHÔNG có cảnh đúng thứ câu đó nói (hoặc
cảnh quá ít, phải lặp nhiều) thì được lấy cảnh kho: trong `shots` ghi `lib` = mã (vd "L12"), `start`–`end` tính TRONG
cảnh kho (0 → độ dài cảnh). Cảnh kho phải THỂ HIỆN ĐÚNG điều câu nói (không lấy cảnh "na ná"); không có cảnh khớp thì
thôi — dùng cảnh video gốc, tool tự bù. Cảnh kho chiếm tối đa {{lib_share}} tổng cảnh; cảnh video gốc để `lib` rỗng.
{{library}}

## Tiêu đề và nhạc
- `titles_top`: 2 dòng tiêu đề CHỮ RẤT TO phía trên video, ngôn ngữ đích, mỗi dòng ≤ {{title_max}} ký tự, gây tò mò, đúng
  nội dung.
- `music`: chọn một bài trong danh sách nhạc (đúng tên) hợp không khí; không bài nào hợp thì `name: null`.

{{localize_brief}}

## Góp ý của chủ dự án
{{feedback}}

## Điều cấm
{{sensitive_notes}}
{{policy_cuts}}

## Tóm tắt video gốc (chỉ để hiểu bối cảnh)
{{summary}}

## Nhạc có sẵn
{{music_list}}

## Các cảnh dùng được (giây gốc — mô tả)
{{scenes}}

## Khung hình của các cảnh đó (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc trong các cảnh đó (nếu có — để lấy thông tin thật, KHÔNG dịch lại từng câu)
{{transcript}}
