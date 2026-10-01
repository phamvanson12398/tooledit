# Nhiệm vụ: viết lời THUYẾT MINH {{language_name}} cho video số {{video_index}}

Footage gốc nói {{source_name}}. Bản TikTok này được thuyết minh bằng **{{language_name}}** (chủ dự án tự thu voice
từng câu) và phụ đề chính là các câu này. Kế hoạch dựng đã chọn xong các clip; dưới đây là lời thoại gốc của các clip
được giữ, theo đúng thứ tự trên video.

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

## Chỗ KHÔNG có giọng nói — BẮT BUỘC viết lời dẫn (`kind: "narration"`)
{{silent_gaps}}
Mỗi chỗ trên phải có lời dẫn phủ ít nhất một nửa thời lượng (có thể 1–3 câu, mỗi câu nằm gọn trong một clip).
Lời dẫn như người dẫn chuyện TikTok: tả điều ĐANG thấy trên hình (xem khung hình), dẫn dắt sang đoạn sau, nói cảm xúc
của khoảnh khắc, đặt câu hỏi gợi tò mò. KHÔNG bịa sự kiện, con số, tên, lời nhân vật không có trong footage; không
"spoil" điều sắp xảy ra nếu chưa thấy. Giọng văn liền mạch với các câu thuyết minh xung quanh.

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
