# Nhiệm vụ: DỊCH CHỮ TRÊN MÀN HÌNH sang {{language_name}} — {{market}}

Video gốc ~{{duration}} giây, giữ NGUYÊN (hình + tiếng). Nội dung: {{summary}}

Tool sẽ CHE chữ gốc trên màn hình bằng một dải nền rồi viết bản dịch của bạn đè lên đúng chỗ đó. Việc của bạn: xem các
khung hình (mỗi khung có ghi giây gốc), tìm MỌI chữ có sẵn trên màn hình — phụ đề cứng, chú thích, tiêu đề, chữ trên biển
/ bảng / sản phẩm mà người xem cần hiểu — và dịch.

## Luật
- Mỗi mục (`items`) = MỘT dòng / một khối chữ liền nhau, từ lúc hiện tới lúc tắt:
  - `start`–`end`: giây GỐC lúc chữ hiện và tắt (chữ hiện qua nhiều khung liên tiếp thì gộp thành MỘT mục; chữ đổi nội
    dung thì sang mục mới).
  - `box`: [trái, trên, phải, dưới] — vị trí chữ trên khung GỐC, mỗi số 0..1 (0,0 = góc trên trái; 1,1 = góc dưới phải),
    bao TRỌN dòng chữ (thà rộng hơn một chút còn hơn sót nét).
  - `text_orig`: chép ĐÚNG chữ gốc. `text`: bản dịch {{language_name}} tự nhiên như người bản xứ viết, NGẮN GỌN để vừa chỗ
    chữ gốc (không dài hơn gốc quá nhiều). `text_vi`: nghĩa tiếng Việt.
- Tên riêng, số, thương hiệu không cần dịch thì `text` để y như `text_orig`.
- BỎ QUA: logo / watermark nhỏ ở góc, chữ quá nhỏ hoặc mờ không đọc được, chữ đã là {{language_name}}.
- Dịch đúng nghĩa, không thêm ý, không bịa. Không chửi thề; không nhắc nền tảng khác ngoài TikTok (gặp thì dịch nhẹ đi /
  bỏ mục đó).
- Video không có chữ nào trên màn hình → `items` rỗng, ghi lý do ở `editor_notes`.
- `editor_notes`: tiếng Việt, ngắn — video có những loại chữ nào, chỗ nào bỏ qua và vì sao.

## Khung hình (tên file — giây gốc)
{{frames}}

## Lời nói gốc (chỉ để hiểu ngữ cảnh khi dịch)
{{transcript}}

## Góp ý của chủ dự án
{{feedback}}
