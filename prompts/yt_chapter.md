# Nhiệm vụ: VIẾT LỜI ĐỌC + CHỌN CẢNH cho MỘT CHƯƠNG của video YouTube — {{language_name}}

Video YouTube dài: giọng đọc mới + nhạc nền mới (âm thanh gốc bỏ hết), hình cắt từ video nguồn, phụ đề in trên hình. Bạn
viết lời cho ĐÚNG MỘT chương dưới đây, dài khoảng **{{target_s}} giây**.

## Chương
{{chapter}}

## Ghi chú thêm của chủ dự án
{{brief}}

## Phụ đề / chữ trên màn hình của video gốc
{{onscreen}}

## Viết lời
- Văn NÓI tự nhiên của người bản xứ {{language_name}} làm YouTube (kể chuyện / bình luận cuốn hút, có cá tính), không dịch
  từ tiếng Việt, không văn viết. Câu dài ngắn xen kẽ; cứ ~1 phút có một câu giữ chân (câu hỏi, chi tiết bất ngờ, "nhưng…").
- Vai trò câu: chương mở đầu thì câu 1 `role: "hook"`; các câu khác `body`; `cta` (đăng ký kênh / bấm thích / bình luận)
  chỉ ở CUỐI chương, ngắn, tự nhiên, không ép (thường chỉ chương giữa video hoặc chương cuối). KHÔNG nhắc TikTok.
- Giá trị mới (chính sách YouTube): kể theo cách của kênh, thêm nhận xét / phân tích / bối cảnh; KHÔNG đọc lại y nguyên lời
  gốc.
- ĐÚNG SỰ THẬT: nói điều THẤY trong cảnh / NGHE trong lời gốc; kiến thức chung chỉ khi phổ biến, chắc chắn đúng. Không bịa
  tên, giá, số liệu, năm tháng — không chắc thì nói chung chung. Thân thiện quảng cáo: không chửi thề, không máu me.
- Độ dài: ~{{target_s}} giây ở tốc độ ~{{cps}} chữ/giây → khoảng **{{target_chars}} chữ** (không tính dấu cách, dấu câu).
  Tool đếm và bắt viết lại nếu thiếu / thừa. Mỗi phần tử `lines` là 1 câu (hoặc 2 câu ngắn), đọc 2–8 giây.
- `keyword` = CHỮ NHẤN (≤ {{title_max}} ký tự, có trong câu) — chỉ khoảng 1/4 số câu, câu thật đắt mới có.
- `text_vi` = nghĩa tiếng Việt; `shots_vi` = cảnh dưới câu có gì.
- `outline_vi`: dàn ý ngắn của chương; `titles_top`: để trống được; `music`: một bài trong danh sách nhạc hợp không khí
  chương (đúng tên) hoặc `name: null`.

## Chọn cảnh (`shots`)
- Mỗi câu 1–3 cảnh, giây GỐC `start`–`end`, nằm TRỌN trong MỘT cảnh của danh sách "Các cảnh của chương" (không lấy cảnh
  ngoài danh sách), mỗi cảnh ≥ 1 giây. Câu nói về gì thì cảnh phải THẤY đúng thứ đó.
- Tổng độ dài cảnh của một câu nên ≥ thời gian đọc câu đó. Dùng nhiều cảnh khác nhau, 2 câu liền nhau không cùng cảnh.
- Tránh cảnh mờ, rung, có chữ / logo của người khác, đoạn vi phạm chính sách (xem "Điều cấm").

## Kho cảnh chung (CHỈ dùng khi các cảnh của chương thiếu cảnh khớp lời)
Câu nào chương không có cảnh đúng thứ câu đó nói thì được lấy cảnh kho: `lib` = mã (vd "L12"), `start`–`end` tính TRONG
cảnh kho (0 → độ dài cảnh). Cảnh kho phải ĐÚNG điều câu nói; tối đa {{lib_share}} tổng cảnh; cảnh video gốc để `lib` rỗng.
{{library}}

{{localize_brief}}

## Góp ý của chủ dự án
{{feedback}}

## Điều cấm
{{sensitive_notes}}
{{policy_cuts}}

## Tóm tắt video nguồn
{{summary}}

## Nhạc có sẵn
{{music_list}}

## Các cảnh của chương (giây gốc — mô tả)
{{scenes}}

## Khung hình của các cảnh đó (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc trong các cảnh đó (nếu có — lấy thông tin thật, KHÔNG đọc lại y nguyên)
{{transcript}}
