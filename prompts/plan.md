# Nhiệm vụ: lập kế hoạch dựng cho video số {{video_index}}

Phong cách: **{{style_name}}** — {{style_description}}
{{style_brief}}

## Ràng buộc
- Thời lượng video (kể cả hook {{hook_s}} giây) phải từ 60 đến 150 giây. Nếu footage dùng được quá ngắn thì
  giữ tối đa có thể, không kéo dài nhân tạo.
- Chỉ dùng footage trong đoạn {{range}} giây. Các clip theo đúng thứ tự thời gian, không chồng nhau.
- Mọi mốc giây là giây trong FOOTAGE GỐC (code tự tính ra thời gian trên timeline).
- Chữ nhấn phải đúng với lời thoại thật ở gần mốc đó; dùng tên riêng đúng. Không vi phạm điều cấm.
- Phụ đề thoại, ducking nhạc, vị trí chữ trong vùng an toàn: code tự làm, bạn KHÔNG cần liệt kê.
- Footage {{width}}x{{height}}. Khung mặc định cho footage ngang: {{default_ratio}}
  ("4:3" cho cảnh rộng/nhiều người, "1:1" cho cận mặt/cận vật; "full" chỉ khi footage dọc).
  Đổi khung theo cảnh: {{reframe}}.
- Chữ có sẵn trên hình: {{burned_in}}
- Nhạc nền: chọn bài HỢP NHẤT với không khí của video này (thể loại, tâm trạng, nhịp) trong danh sách dưới;
  đừng chọn theo thói quen. Nếu không bài nào hợp thì đặt null và mô tả trong mood_vi (tool sẽ báo cần bổ sung):
{{music_list}}
- SFX: nếu có tiếng phù hợp trong kho dưới thì ghi `name`, không thì null:
{{sfx_list}}
{{business_note}}

## Bố cục và tiêu đề
{{layout_brief}}

## Mũi tên chỉ chi tiết
{{arrow_brief}}

## Trang trí cho video sinh động (chỉ dùng tên có trong kho; kho trống thì bỏ qua)
Liều lượng theo phong cách: {{decor_brief}}
- `effects`: hiệu ứng hình ngắn (flash, rung, lấp lánh...) đúng khoảnh khắc nhấn — kho:
{{effect_list}}
- `stickers`: emoji/sticker minh họa cảm xúc, đặt ở góc không che mặt người — kho:
{{sticker_list}}
- `transitions`: chuyển cảnh ở cuối clip số `after_clip` (tính từ 0), dùng khi đổi ý/đổi cảnh, không phải mọi chỗ cắt — kho:
{{transition_list}}
- `filter`: một filter màu cho cả video để đồng bộ tông (hoặc null) — kho:
{{filter_list}}

## Hook đã chọn (sẽ đặt trước clip đầu tiên)
{{hook}}

## Điều cấm
{{sensitive_notes}}

## Tóm tắt nội dung
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Khoảnh khắc đáng chú ý
{{key_moments}}

## Sự kiện âm thanh (máy tự dò — tiếng cười thường KHÔNG có trong transcript)
{{audio_events}}
Dùng các mốc này: giữ trọn tiếng cười / phản ứng (đừng cắt ngang), đặt chữ nhấn, SFX, zoom punch đúng lúc cười hoặc cao trào.

## Cảnh (giây)
{{scenes}}

## Transcript ([giây bắt đầu–kết thúc] lời thoại)
{{transcript}}
