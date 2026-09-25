# Nhiệm vụ: viết 3 phương án hook cho video số {{video_index}}

Hook là 3–5 giây đầu video: một câu voice ngắn (chủ dự án tự thu), hình chuyển động nhanh, chữ lớn nhấn từ khóa
ở dải trên, cắt ngay trước khi lộ "lời giải". Hook phải tự cung cấp bối cảnh như thể đây là video duy nhất.

Yêu cầu cho MỖI phương án:
- `line`: câu hook bằng **{{language_name}}**, văn nói tự nhiên của người bản xứ (không dịch từ tiếng Việt),
  tối đa {{max_chars}} ký tự để đọc trong khoảng 4 giây.
- `line_vi`: bản dịch tiếng Việt.
- `onscreen_text`: từ khóa ngắn hiện ở dải trên (ngôn ngữ của video).
- `footage`: đoạn footage gốc chạy dưới hook, 3–5 giây, hình có chuyển động/biểu cảm.
- `source`: đoạn footage chứng minh điều hook nói là CÓ THẬT. Không hứa điều video không có.
- `hook_type`: một trong climax_first (tua thẳng đến cao trào), open_question (câu hỏi bỏ lửng), contrast
  (tương phản), half_reveal (hé lộ một nửa), odd_detail (con số / chi tiết lạ). 3 phương án nên khác kiểu nhau.
- `music_sfx_vi`: kiểu nhạc/hiệu ứng đi kèm.

Kiểu hook khách ưa thích (nếu có): {{preferred_hooks}}

## Điều cấm (từ bước hiểu nội dung)
{{sensitive_notes}}

## Tóm tắt nội dung
{{summary}}

## Tên riêng đúng (dùng khi viết)
{{name_corrections}}

## Khoảnh khắc đáng chú ý
{{key_moments}}

## Transcript video này ([giây] lời thoại, đoạn {{range}})
{{transcript}}
