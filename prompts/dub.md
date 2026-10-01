# Nhiệm vụ: viết lời THUYẾT MINH {{language_name}} cho video số {{video_index}}

Footage gốc nói {{source_name}}. Bản TikTok này được thuyết minh bằng **{{language_name}}** (chủ dự án tự thu voice
từng câu) và phụ đề chính là các câu này. Kế hoạch dựng đã chọn xong các clip; dưới đây là lời thoại gốc của các clip
được giữ, theo đúng thứ tự trên video.

{{localize_brief}}

## Luật
- Mỗi câu (`lines`) thuyết minh cho một đoạn thoại gốc: `source_start`–`source_end` là giây GỐC, nằm gọn trong
  MỘT clip được giữ (xem danh sách clip), các câu theo thứ tự, không chồng nhau.
- Mỗi câu dài {{line_min}}–{{line_max}} giây (một ý trọn vẹn), đọc kịp trong chỗ trống: tối đa khoảng
  {{max_cps}} ký tự/giây (không tính dấu cách, dấu câu). Nói gọn lại nếu câu gốc dài — giữ ý chính, không bịa thêm.
- Văn nói tự nhiên của người bản xứ ({{market}}), đúng giọng điệu nhân vật (đùa thì đùa, nghiêm thì nghiêm).
  Không dịch từng chữ. Tên riêng: {{name_corrections}}
- `kind`: "dub" = câu dịch lời thoại gốc; "narration" = LỜI DẪN viết thêm cho chỗ không có giọng nói.
- Tiếng cười, hò reo ngắn thì để nguyên tiếng gốc (giữ khoảnh khắc).
- Không nhắc nền tảng nào khác ngoài TikTok, không chửi thề, không nhắc nội dung đã bị cắt vì chính sách.
- `text_vi`: nghĩa tiếng Việt để chủ dự án hiểu.
- `adapt_vi`: câu nào bạn BẢN ĐỊA HÓA (đổi ví dụ, so sánh, đơn vị, cách đùa cho hợp khán giả đích) thì ghi ngắn đổi gì,
  vì sao (tiếng Việt); câu dịch thẳng thì để trống.

## Chỗ KHÔNG có giọng nói — lời dẫn ở CẢNH HAY / HÀNH ĐỘNG đáng chú ý (`kind: "narration"`)
{{silent_gaps}}
{{opening_note}}Xem khung hình, tìm trong các chỗ trên những khoảnh khắc ĐÁNG NÓI rồi mới viết lời dẫn, đặt câu bắt đầu đúng lúc
hành động bắt đầu. Ví dụ video nấu ăn: lúc thêm gia vị ("Giờ thêm một thìa nước mắm"), lật miếng thịt, món chín /
bày ra đĩa; vlog: lúc tới nơi mới, cảnh đẹp vừa hiện ra; thể thao: pha bóng đẹp. Chỗ chỉ là thao tác lặp lại, đi lại,
chờ đợi thì KHÔNG nói — để nhạc và âm thanh hiện trường. Không cần lấp mọi chỗ trống; tổng lời dẫn tối đa khoảng 60%
thời gian lặng. Mỗi câu lời dẫn ghi `action_vi` = hành động / cảnh đang diễn ra (tiếng Việt).
Lời dẫn như người dẫn chuyện TikTok: ngắn, nói điều ĐANG thấy, có thể thêm mẹo / cảm xúc / câu hỏi gợi tò mò. KHÔNG bịa
nguyên liệu, số lượng, tên, sự kiện không thấy trên hình; không "spoil" điều chưa xảy ra.

## Điều cấm
{{sensitive_notes}}

## Tóm tắt nội dung
{{summary}}

## Hook đã dùng (đứng trước, không thuyết minh lại)
{{hook}}

## Clip được giữ (giây gốc, theo thứ tự trên video)
{{clips}}

## Lời thoại gốc trong các clip ([giây gốc] lời thoại)
{{transcript}}
