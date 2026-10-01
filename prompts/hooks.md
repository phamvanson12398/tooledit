# Nhiệm vụ: viết 3 phương án hook cho video số {{video_index}}
{{translate_note}}

Hook gồm HAI phần, chủ dự án thu chung một file voice (đọc liền mạch phần 1 rồi phần 2):
1. **Câu dẫn đời thường** (`intro`): 1–2 câu bình thường, gần gũi, như đang kể chuyện với bạn bè trước khi vào
   chuyện chính (vd "Hôm qua tôi ngồi xem lại đoạn phỏng vấn này…", "Tối nay lạnh quá nên làm món này cho cả nhà…").
   Không giật tít; tạo cảm giác người thật đang nói. Tối đa {{intro_max_chars}} ký tự, phải đúng với bối cảnh có thật.
2. **Câu hook** (`line`): ngay sau đó, câu ngắn gây tò mò mạnh, cắt ngay trước khi lộ "lời giải".
Hình: phần 1 chạy trên `intro_footage` (cảnh bối cảnh / đời thường), phần 2 chạy trên `footage` (hình có chuyển động /
biểu cảm mạnh); chữ lớn nhấn từ khóa ở dải trên. Hook phải tự cung cấp bối cảnh như thể đây là video duy nhất.

Yêu cầu cho MỖI phương án:
- `intro`: câu dẫn đời thường bằng **{{language_name}}** (1–2 câu); `intro_vi`: bản dịch tiếng Việt.
- `intro_footage`: đoạn footage gốc chạy dưới câu dẫn, 3–6 giây.
- `line`: câu hook bằng **{{language_name}}**, văn nói tự nhiên của người bản xứ (không dịch từ tiếng Việt),
  tối đa {{max_chars}} ký tự để đọc trong khoảng 4 giây.
- `line_vi`: bản dịch tiếng Việt.
- `onscreen_text`: từ khóa ngắn hiện ở dải trên (ngôn ngữ của video).
- `footage`: đoạn footage gốc chạy dưới câu hook, 3–5 giây, hình có chuyển động/biểu cảm.
- `source`: đoạn footage chứng minh điều hook nói là CÓ THẬT. Không hứa điều video không có.
- `hook_type`: một trong climax_first (tua thẳng đến cao trào), open_question (câu hỏi bỏ lửng), contrast
  (tương phản), half_reveal (hé lộ một nửa), odd_detail (con số / chi tiết lạ). 3 phương án nên khác kiểu nhau.
- `music_sfx_vi`: kiểu nhạc/hiệu ứng đi kèm.

Kiểu hook khách ưa thích (nếu có): {{preferred_hooks}}

## Điều cấm (từ bước hiểu nội dung)
{{sensitive_notes}}

## Đoạn vi phạm chính sách TikTok (sẽ bị CẮT — hook không được dùng hay nhắc tới)
{{policy_cuts}}

## Tóm tắt nội dung
{{summary}}

## Tên riêng đúng (dùng khi viết)
{{name_corrections}}

## Sự kiện âm thanh (máy tự dò — tiếng cười thường KHÔNG có trong transcript)
{{audio_events}}

## Khoảnh khắc đáng chú ý
{{key_moments}}

## Transcript video này ([giây] lời thoại, đoạn {{range}})
{{transcript}}
