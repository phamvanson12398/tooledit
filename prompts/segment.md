# Nhiệm vụ: chia footage dài thành nhiều video TikTok ĐỘC LẬP

Footage dài {{duration}} giây; đoạn dùng được {{range}} giây. Hãy chọn các đoạn hay để mỗi đoạn thành MỘT video riêng.

## Luật bắt buộc
- Mỗi video là **một video độc lập**: trọn vẹn có mở, diễn biến, kết; người xem không cần biết video khác.
- **Không có dấu vết series**: không "Part 1/2", không "xem phần tiếp theo"; phần kết khép lại gọn.
- Bạn toàn quyền chọn: đoạn hay thì thành video, đoạn nhạt thì bỏ. Không giới hạn số video.
- Thời lượng mỗi video sau khi dựng: {{min_video_s}}–{{max_video_s}} giây (kể cả hook 3–5s). Bước sau sẽ cắt gọn nhịp
  (bỏ khoảng lặng, câu thừa, tua nhanh đoạn nhàm), nên mỗi video là **một đoạn footage liền** dài
  {{min_raw_s}}–{{max_raw_s}} giây footage gốc.
  - Đoạn hay nhưng ngắn: ghép với đoạn LIỀN KỀ cùng chủ đề nếu tự nhiên; không được thì bỏ và ghi lý do.
  - Đoạn quá dài: tách thành hai video độc lập, mỗi video tự đứng được.
  - Nếu toàn bộ footage dùng được vẫn ngắn hơn {{min_raw_s}} giây: trả về một video duy nhất, không kéo dài.
- Các video không chồng nhau. Mọi mốc là giây trong footage gốc, nằm trong đoạn dùng được.
- Ghi **cả các đoạn bị bỏ** vào `dropped` kèm lý do (tiếng Việt), để người dùng xem lại.
- `title_vi`, `summary_vi`, `why_vi` viết tiếng Việt, ngắn. Không bịa nội dung không có trong footage.

## Điều cấm
{{sensitive_notes}}

## Tóm tắt toàn bộ
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Khoảnh khắc đáng chú ý
{{key_moments}}

## Sự kiện âm thanh (máy tự dò — tiếng cười thường KHÔNG có trong transcript)
{{audio_events}}

## Cảnh (giây)
{{scenes}}

## Transcript ([giây bắt đầu–kết thúc] lời thoại)
{{transcript}}
