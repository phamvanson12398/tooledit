# Nhiệm vụ: xem bài TikTok ảnh rồi viết CONTENT MỚI về nhiều phim — {{language_name}}, {{market}}

Chủ dự án gửi một bài TikTok dạng ẢNH (ảnh + tiêu đề bên dưới) làm Ý TƯỞNG. Hãy hiểu bài đó nói gì (vd "5 nhân vật
thông minh nhất trong phim hoạt hình"), nhận ra từng PHIM và NHÂN VẬT trong ảnh, rồi viết một content MỚI cùng chủ đề.
Video mới dùng HÌNH CẮT TỪ CHÍNH CÁC PHIM (chủ dự án có file phim), tiếng phim tắt, chỉ có giọng đọc + nhạc nền nhẹ.

## Bài gốc
- Tiêu đề / mô tả: {{title}}
- Tài khoản: {{uploader}}
- Ảnh của bài (mở từng file bằng Read để xem):
{{images}}

## Nhận ra phim
- `films`: các phim được nhắc, theo thứ tự xuất hiện trong video MỚI, `key` = phim1, phim2… Tối đa {{max_films}} phim.
- `title` = tên phim CHÍNH THỨC ở thị trường {{market}} (hiện trên màn hình); `title_vi` = tên tiếng Việt / tên gốc để
  chủ dự án tìm đúng file phim; `year` chỉ khi biết chắc.
- CHỈ ghi phim bạn nhận ra chắc chắn (qua ảnh / chữ trên ảnh / tiêu đề). Không chắc thì ghi vào `editor_notes` để chủ dự
  án kiểm tra, đừng đoán bừa.

## Viết content mới
- Viết `story_vi` (dàn ý tiếng Việt) TRƯỚC: câu mở cuốn ngay giây đầu → từng phim / nhân vật (mỗi phần: là ai, điều
  gì làm họ đáng nhắc, một chi tiết / khoảnh khắc đắt) → câu kết có dư âm.
- Lời đọc (`lines`) bằng {{language_name}}, văn NÓI của người bản xứ, không dịch máy; KHÔNG chép lời bài gốc. Đúng sự
  thật về phim — không bịa tình tiết; không chắc thì nói chung chung.
- Mỗi câu 1 ý, đọc 2–10 giây. `film` = phim mà câu đó nói tới (hình lấy từ phim đó). `want_vi` = cảnh cần tìm, CỤ THỂ
  (ai, đang làm gì, khoảnh khắc nào) để bước sau tìm đúng trong phim.
- Câu mở / kết cũng gắn với một phim (thường phim nổi bật nhất).
- **DỪNG HÌNH** (`shot: "freeze"` — chủ dự án thích): video chạy rồi ĐỨNG HÌNH ở khoảnh khắc đắt, tiếng "tách" + tên
  nhân vật (`label`, {{language_name}}, ngắn) hiện lên. Dùng ở câu giới thiệu mỗi nhân vật / chi tiết đắt nhất. Mỗi lần
  đứng tối đa {{freeze_max_s}}s; tổng thời gian dừng hình ≤ {{image_share}} video — còn lại `shot: "video"`.
- Cả bài đọc khoảng **{{video_s}} giây** ở tốc độ giọng ~{{cps}} chữ/giây → khoảng **{{chars}} chữ** (không tính dấu cách,
  dấu câu). Tool đếm và bắt viết lại nếu thiếu / thừa.
- `titles_top`: 2 dòng tiêu đề ngắn ({{language_name}}) — dòng 1 bối cảnh / gây tò mò, dòng 2 cú chốt.
- `music`: chọn từ danh sách dưới (đúng tên) hợp không khí, hoặc name = null. `caption` + `hashtags` bằng
  {{language_name}}, kèm bản dịch tiếng Việt.
- Không chửi thề, không nhắc nền tảng khác ngoài TikTok, không "follow / xem phần sau".

## Văn mẫu chủ dự án thích (học GIỌNG, NHỊP — không chép nội dung)
{{style_examples}}

## Góp ý của chủ dự án
{{feedback}}

## Nhạc có sẵn
{{music_list}}
