# Nhiệm vụ: làm BIẾN THỂ video hoạt hình — CỐT TRUYỆN MỚI từ chính các cảnh có sẵn — {{language_name}}, {{market}}

Video hoạt hình gốc dài ~{{duration}} giây. Hãy dùng CHÍNH CÁC CẢNH của nó dựng thành một video MỚI có CỐT TRUYỆN KHÁC bản
gốc ít nhất {{min_story_diff}}%:
- HÌNH: các cảnh gốc XẾP LẠI theo thứ tự mới (cắt khúc trong cảnh tùy ý), mỗi đoạn gốc chỉ dùng MỘT lần, tốc độ thường.
- ÂM THANH: giữ nhạc + tiếng động gốc; giọng nói gốc bị tách bỏ. Cảnh nào nhân vật NÓI (có lời nói gốc / đang mở miệng) thì
  viết LỜI THOẠI MỚI cho nhân vật đó theo cốt truyện mới (chủ dự án lồng voice + phụ đề {{language_name}}).

## Cốt truyện mới
1. Viết `original_story_vi` (bản gốc kể gì) rồi `new_story_vi` (cốt truyện MỚI: mở đầu – diễn biến – kết, mạch lạc,
   hấp dẫn người xem TikTok). Đổi được: mục đích / động cơ nhân vật, quan hệ giữa các nhân vật, nguyên nhân – kết quả, thứ
   tự sự việc, cái kết, thể loại (hài → cảm động…). Lời thoại MỚI hoàn toàn, không dịch lời gốc.
2. `story_diff` = cốt truyện mới khác bản gốc bao nhiêu % (đánh giá THẬT THÀ). Cần ≥ {{min_story_diff}}%.
3. Nếu với các cảnh có sẵn KHÔNG THỂ làm khác ≥ {{min_story_diff}}% (quá ít cảnh, cảnh quá liền mạch…) thì vẫn làm bản khác
   nhất có thể nhưng đặt `feasible: false` và ghi lý do vào `diff_note_vi` — tool sẽ báo chủ dự án. Đạt thì `feasible: true`
   và ghi ngắn khác ở đâu.

## Xếp cảnh (`beats`, theo thứ tự hiện trên video mới)
- Mỗi beat: `start`–`end` giây GỐC (≥ 0.8 giây, nên gọn trong một cảnh ở danh sách "Các cảnh"), `what_vi` = cảnh thấy gì /
  đóng vai gì trong truyện mới.
- Thứ tự phải KHÁC bản gốc: ≥ {{min_order_diff}} số cặp cảnh liền nhau không được nối tiếp nhau như bản gốc (máy tự đo).
- Không chồng đoạn, không lặp đoạn. Dùng ít nhất {{min_cover}} thời lượng gốc (không bỏ quá nhiều cảnh).
- Tránh đoạn vi phạm chính sách (xem "Điều cấm").

## Lời thoại (`line` của beat)
- BẮT BUỘC có `line` ở mọi beat chứa lời nói gốc (xem "Lời nói gốc" — giọng gốc bị tách bỏ, nhân vật mở miệng phải có
  tiếng). Beat không có ai nói thì để `line` rỗng (giữ nhạc / tiếng động gốc).
- `speaker` = tên nhân vật đang nói trong cảnh đó (nhìn khung hình; đặt tên thống nhất, tên mới hợp truyện mới cũng được),
  `text` = câu thoại MỚI bằng {{language_name}}, văn nói tự nhiên hợp tính cách nhân vật, `text_vi` = nghĩa tiếng Việt.
- Câu phải đọc KỊP trong beat: khoảng ≤ thời lượng beat × {{cps}} chữ/giây (không tính dấu cách, dấu câu).
- Không chửi thề, không nhắc nền tảng khác ngoài TikTok.
- `titles_top`: 2 dòng tiêu đề ngắn bằng {{language_name}} theo cốt truyện mới.

{{localize_brief}}

## Góp ý của chủ dự án
{{feedback}}

## Tóm tắt video gốc
{{summary}}

## Các cảnh (giây gốc)
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc (giây gốc — chỗ nào có lời thì cảnh đó cần lời thoại mới)
{{transcript}}

## Điều cấm
Không dùng đoạn vi phạm chính sách TikTok (bạo lực thật, gợi dục, chửi thề…).
