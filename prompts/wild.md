# Nhiệm vụ: dựng phim THẾ GIỚI ĐỘNG VẬT từ các đoạn có sẵn — {{language_name}}, {{market}}

Chủ dự án đưa nhiều đoạn quay động vật (đã nối thành một video ~{{total}} giây, {{n}} cảnh). Làm thành MỘT video kiểu phim
tài liệu thế giới động vật:
- LÀM THEO ĐÚNG THỨ TỰ NÀY:
  1. Xem hết khung hình, rồi nghĩ KỊCH BẢN MỚI trước (`story_vi`: mở – diễn biến – kết) — câu chuyện của riêng bạn về con
     vật, KHÔNG kể lại câu chuyện / lời nói cũ, không đi theo thứ tự quay cũ.
  2. CHỌN CẢNH THEO KỊCH BẢN MỚI: với từng đoạn của kịch bản, lấy cảnh hợp nhất → ra `order`. Thứ tự cũ không có ý nghĩa gì;
     ít nhất {{order_diff}} cặp cảnh liền nhau phải khác thứ tự gốc.
  3. Viết lời dẫn bám kịch bản mới, mỗi câu trên đúng cảnh nó nói tới.
- HÌNH: dùng TOÀN BỘ {{n}} cảnh, KHÔNG được bỏ cảnh nào, không cắt bớt — chỉ ĐẢO THỨ TỰ (`order` = danh sách mã cảnh theo
  thứ tự mới, đủ mọi cảnh, mỗi cảnh đúng một lần). Gợi ý mạch: mở bằng cảnh bối cảnh / cảnh đẹp giới thiệu nơi sống → nhân
  vật chính (con vật) → hành động / sự kiện (kiếm ăn, săn mồi, chăm con, di cư…) → kết lắng đọng.
- ÂM THANH: giọng nói gốc (nếu có) bị bỏ; tiếng thiên nhiên / tiếng con vật GIỮ. Bạn viết LỜI DẪN MỚI.

## Lời dẫn (`lines`)
- Giọng người dẫn phim tài liệu: điềm tĩnh, cuốn hút, giàu hình ảnh, có chút kịch tính khi cần; kể về tập tính, bản năng,
  cuộc sống của con vật đang THẤY trên hình.
- NHỊP phim tài liệu: nói MỘT CHÚT rồi NGHỈ để tiếng thiên nhiên dẫn dắt, rồi mới nói tiếp. Mỗi câu ≤ {{max_line}} giây;
  giữa 2 câu nghỉ ít nhất {{pause}} giây; tổng lời dẫn chiếm {{talk_lo}}–{{talk_hi}} thời lượng video. Câu đầu tiên bắt đầu
  trong {{first_line}} giây đầu (mở lời giới thiệu).
- Mỗi câu gắn với MỘT cảnh: `scene` = số mã cảnh, `start`–`end` = giây GỐC nằm trong cảnh đó (đoạn đọc câu). Câu phải đọc
  KỊP trong đoạn: khoảng ≤ (end − start) × {{cps}} chữ/giây (không tính dấu cách, dấu câu). Xếp các câu theo đúng thứ tự
  hiện trên video mới.
- ĐÚNG SỰ THẬT: chỉ nói điều THẤY trong hình và kiến thức động vật phổ biến, chắc chắn đúng; không bịa tên loài khi không
  chắc (nói chung "con báo", "loài chim này"…), không bịa số liệu. Không chửi thề, không nhắc nền tảng khác ngoài TikTok.
- `text` bằng {{language_name}} (văn nói tự nhiên của người dẫn phim tài liệu bản xứ), `text_vi` = nghĩa tiếng Việt.
- `story_vi`: mạch phim mới (tiếng Việt). `titles_top`: 2 dòng tiêu đề ngắn bằng {{language_name}}.

{{localize_brief}}

## Góp ý của chủ dự án
{{feedback}}

## Tóm tắt nội dung
{{summary}}

## Các cảnh (mã, giây gốc, độ dài)
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc (sẽ bị bỏ — chỉ để hiểu con vật / sự việc; KHÔNG dựa vào đây để viết hay xếp cảnh)
{{transcript}}
