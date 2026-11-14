# Nhiệm vụ: tìm các ĐOẠN HAY trong một phần video dài (phần {{part}}, giây {{lo}}–{{hi}})

Chủ dự án đưa MỘT video dài (podcast, livestream, phỏng vấn, vlog, show…). Tool sẽ cắt các đoạn hay ra thành nhiều video
ngắn theo CHỦ ĐỀ, GIỮ NGUYÊN hình + tiếng gốc. Việc của bạn ở bước này: liệt kê các ĐOẠN HAY trong phần {{lo}}–{{hi}}s.

## Thế nào là đoạn hay
- Có NGHĨA trọn vẹn khi đứng riêng: người xem không cần xem đoạn trước vẫn hiểu (có đầu – có ý – có kết).
- Hấp dẫn: câu nói đắt, quan điểm thú vị, câu chuyện có kết, kiến thức hữu ích, hài, bất ngờ, cảm xúc, cao trào, tranh luận.
- Bỏ: chào hỏi, đọc quảng cáo, nói lan man, kỹ thuật trục trặc, đoạn lặng không có gì.
- Độ dài TÙY nội dung — miễn đủ ý và hay (vài giây tới vài phút đều được), tối thiểu {{min_s}} giây.

## Quy tắc
- `start` / `end` = giây GỐC, nằm trong {{lo}}–{{hi}}; bắt đầu ở ĐẦU câu, kết thúc ở CUỐI câu (xem mốc giây lời gốc bên
  dưới), không cắt ngang câu nói. Các đoạn không chồng nhau.
- `topic_vi`: chủ đề ngắn của đoạn (vài chữ, tiếng Việt) — các đoạn cùng chủ đề dùng cùng tên để gom lại sau.
- `summary_vi`: đoạn nói gì; `why_vi`: vì sao hay. Chỉ ghi điều có thật trong video, không bịa.
- Không có đoạn nào hay thì trả `moments` rỗng.

## Tóm tắt cả video
{{summary}}

## Khung hình trong phần này (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời gốc trong phần này (mốc giây)
{{transcript}}
