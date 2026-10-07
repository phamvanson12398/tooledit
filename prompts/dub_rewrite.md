# Nhiệm vụ: XEM video số {{video_index}} và VIẾT MỚI lời thuyết minh {{language_name}} cho {{market}}

Đây KHÔNG phải việc dịch. Footage gốc nói {{source_name}} — lời gốc dưới đây chỉ để bạn HIỂU sự việc. Tiếng gốc bị tắt;
người xem chỉ nghe lời thuyết minh MỚI bạn viết (chủ dự án tự thu voice từng câu) + nhạc, và phụ đề chính là các câu này.

Hãy làm như một creator TikTok bản xứ của {{market}} vừa xem đoạn video này và tự kể lại cho khán giả nước mình:
- XEM KHUNG HÌNH (mở từng file bằng Read) để biết trên hình đang có gì, ở giây nào.
- Viết kịch bản MỚI theo cách người {{market}} thích xem: câu mở cuốn hút ngay từ giây đầu, kể / giải thích / bình luận
  điều đang thấy, chêm cảm xúc, ví dụ, so sánh, cách đùa, đơn vị, tiền tệ quen thuộc với họ; giải thích chi tiết văn hóa
  lạ nếu cần; kết gọn có dư âm (không kêu gọi xem phần sau).
- KHÔNG dịch từng câu, KHÔNG bám theo câu chữ gốc. Được bỏ ý thừa, đổi thứ tự kể trong một cảnh, thêm lời dẫn ở chỗ im lặng.
- ĐÚNG SỰ THẬT: chỉ nói điều có trong hình / lời gốc. Không bịa tên, số liệu, giá, kết quả, lời hứa; không gán lời cho
  nhân vật; không "spoil" điều chưa diễn ra trên hình.

{{localize_brief}}

## Luật thời gian
- Mỗi câu (`lines`) gắn với đoạn hình nó nói tới: `source_start`–`source_end` là giây GỐC, nằm gọn trong MỘT clip được
  giữ, các câu theo thứ tự, không chồng nhau. Câu đầu tiên bắt đầu trong 1 giây đầu của clip đầu tiên.
- Mỗi câu dài {{line_min}}–{{line_max}} giây; đọc kịp: tối đa khoảng {{max_cps}} ký tự/giây (không tính dấu cách, dấu câu).
- Không nói liên tục: chừa khoảng thở / để nhạc dẫn ở chỗ hình tự nói lên (lời chiếm khoảng 60–85% thời lượng).
- `kind`: "dub" nếu câu nói về điều nhân vật đang nói / làm; "narration" nếu là lời dẫn thuần (tả cảnh, bình luận).
- `text_vi` = nghĩa tiếng Việt; `action_vi` = trên hình đang có gì (tiếng Việt, ngắn); `adapt_vi` = chỗ bạn bản địa hóa
  (đổi ví dụ / đơn vị / cách đùa), không có thì để trống.
- Không nhắc nền tảng khác ngoài TikTok, không chửi thề, không nhắc nội dung đã bị cắt vì chính sách.

## Điều cấm
{{sensitive_notes}}

## Tóm tắt nội dung
{{summary}}

## Hook đã dùng (đứng trước, không lặp lại)
{{hook}}

## Clip được giữ (giây gốc, theo thứ tự trên video)
{{clips}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời gốc để hiểu sự việc ([giây gốc] lời thoại — KHÔNG dịch lại)
{{transcript}}
