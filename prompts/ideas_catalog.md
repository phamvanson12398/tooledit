# Nhiệm vụ: GHI DANH MỤC CẢNH của một phần video dài (phần {{part}}, giây {{lo}}–{{hi}})

Chủ dự án có một video dài (vlog, du lịch, lịch sử…) và muốn dùng nó làm KHO CẢNH để dựng nhiều video TikTok ngắn MỚI —
không nhất thiết theo câu chuyện gốc (vd vlog du lịch Nhật → short "Nhật Bản có gì đẹp?"). Bước này chỉ GHI LẠI phần
{{lo}}–{{hi}}s có những cảnh gì, để bước sau nghĩ ý tưởng và chọn cảnh.

## Cách ghi
- Mỗi phần tử `shots` = một CẢNH dùng được: `start`–`end` (giây gốc, nằm trong {{lo}}–{{hi}}s, dài ≥ {{min_shot}} giây).
  Cảnh liền nhau cùng nội dung (cùng chỗ, cùng việc) thì GỘP thành một; cảnh dài mà đổi nội dung thì tách.
- Dựa vào danh sách điểm đổi cảnh máy dò + khung hình (mở bằng Read để xem) — khung hình chỉ là mẫu rải rác, ghi đúng
  điều THẤY được, không đoán điều không thấy.
- `desc_vi`: tiếng Việt, ngắn, CỤ THỂ — nơi chốn, vật, món ăn, người, hành động, thời tiết / giờ (vd "đền đỏ, cổng
  torii, trời nắng, đông khách", "cận bát ramen, khói bốc", "người dẫn nói trước ống kính trong phòng khách sạn").
  Có chữ / biển hiệu đọc được thì ghi (tên địa danh trên biển là thông tin thật dùng được).
- `tags`: vài nhãn ngắn (địa điểm, chủ đề: ẩm thực / phong cảnh / đường phố / con người / lịch sử…, không khí).
- `quality` 1–5: cảnh đẹp, rõ, dùng làm short được thì cao; mờ, rung mạnh, tối, che ống kính, chỉ người nói trước máy
  không có gì để xem thì thấp.
- Phủ hết phần này (không bỏ sót đoạn nào có hình dùng được); đoạn đen / lỗi hình thì bỏ qua.
- `editor_notes`: 1–2 câu về phần này có gì đáng chú ý.

## Tóm tắt cả video
{{summary}}

## Điểm đổi cảnh máy dò (giây gốc)
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc trong phần này (để hiểu đang ở đâu / làm gì)
{{transcript}}
