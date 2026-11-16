# Nhiệm vụ: KỊCH BẢN SHORT "COPS US" (cảnh sát Mỹ) — VIẾT MỚI HOÀN TOÀN + CHỌN CẢNH — {{language_name}}, {{market}}

Chủ dự án đưa MỘT video dài (~{{source_s}} giây) thể loại cảnh sát Mỹ: bodycam / dashcam / truy đuổi / chặn xe / bắt
giữ / thẩm vấn / tình huống hiện trường. Tool đã xem hết video và ghi DANH MỤC CẢNH (bên dưới, {{footage_s}} giây cảnh
dùng được). Việc của bạn: HIỂU vụ việc rồi dựng thành MỘT short TikTok MỚI dài **{{target_s}} giây**, KHÁC VIDEO GỐC
HOÀN TOÀN:
- **Góc kể MỚI**: không thuật lại theo trình tự bodycam. Tự chọn một hướng kể khác hấp dẫn hơn — vd mở bằng cao trào rồi
  quay lại vì sao; kể theo góc nhìn người bị chặn / viên cảnh sát / người xem phán xét ("ai đúng ai sai?"); tập trung vào
  một chi tiết bất ngờ, một câu nói đắt, một sai lầm, một bài học luật pháp… Viết góc kể vào đầu `outline_vi`.
- **Thứ tự cảnh MỚI**: cảnh lấy từ bất kỳ đâu trong video, đảo tự do theo mạch kể mới (không đi theo thứ tự gốc).
- **Lời MỚI**: lời dẫn của bạn, không dịch / đọc lại lời gốc. Tool còn tự phản chiếu một phần cảnh cho khác bản gốc.
- **Xen voice và tiếng gốc**: đoạn cần dẫn dắt / giải thích bối cảnh thì voice; đoạn câu thoại, phản ứng, cao trào ĐẮT
  hơn mọi lời kể thì GIỮ NGUYÊN tiếng gốc (mục "Nửa thuyết minh, nửa tiếng gốc") — miễn sao hợp nhịp short.
- Âm thanh mới = giọng đọc + nhạc nền căng / hồi hộp; âm thanh gốc chỉ còn ở các đoạn giữ tiếng gốc.
- Tool đo voice thật từng câu rồi cắt cảnh bạn chọn cho dài đúng câu; bạn không cần tính giây từng cảnh.

## Đúng sự thật + an toàn
- Chỉ kể điều THẤY / NGHE trong video. Không bịa tên, tội danh, bản án, kết cục, số liệu, địa danh mà video không có.
  Không kết tội người trong video khi video không cho thấy rõ; nói "bị nghi", "theo bodycam"… khi chưa rõ.
- Không cổ vũ bạo lực, không chế giễu nạn nhân, không phân biệt chủng tộc. Không chửi thề (kể cả trích lời gốc trong
  phụ đề — câu gốc có chửi thề thì đừng chọn làm đoạn giữ tiếng gốc).
- Đoạn vi phạm chính sách (xem "Điều cấm") KHÔNG được dùng làm cảnh hay đoạn tiếng gốc.

## Định hướng của chủ dự án
{{brief}}

## Nhiều bản từ cùng một video
{{variants}}

## Phụ đề / chữ trên màn hình của video gốc
{{onscreen}}

## Cấu trúc kịch bản
1. Viết `outline_vi` (tiếng Việt) TRƯỚC: mở đầu thu hút → nội dung chính (2–4 ý, nối nhau mạch lạc) → kết / kêu gọi hành
   động (nếu cần).
2. `lines[0]` có `role: "hook"`: câu mở đầu THU HÚT ngay giây đầu (câu hỏi gây tò mò, con số / chi tiết lạ, tương phản,
   vấn đề người xem đang gặp…), đọc ≤ 3–4 giây, chạy trên cảnh MẠNH NHẤT của video (không nhất thiết là cảnh đầu).
3. Các câu `role: "body"`: nội dung mạch lạc, mỗi câu một ý, nối nhau tự nhiên; câu nào nói về gì thì cảnh dưới câu đó
   phải THẤY đúng thứ đó.
4. `role: "cta"` — lời kêu gọi hành động, CHỈ khi nội dung cần (giới thiệu sản phẩm / quán / dịch vụ, xin follow…),
   đặt ở CUỐI, 1–2 câu, tự nhiên, không ép. Kiểu được dùng: follow, bình luận, lưu video, "link ở bio", "giỏ hàng TikTok".
   KHÔNG nhắc nền tảng khác ngoài TikTok (YouTube, Instagram, subscribe/구독/チャンネル登録…). Nội dung không cần thì
   không có câu cta, câu cuối khép lại gọn.

## Nửa thuyết minh, nửa tiếng gốc
{{orig}}

## Viết lời
- Văn NÓI tự nhiên của người bản xứ {{language_name}} làm TikTok cho khán giả nước mình — không dịch từ tiếng Việt, không
  văn viết; câu dài ngắn xen kẽ, không lặp cùng từ nối ở nhiều câu liền.
- ĐÚNG SỰ THẬT: chỉ nói điều thấy trong khung hình hoặc nghe trong lời nói gốc. Không bịa tên quán / thương hiệu, công
  dụng, giá, địa chỉ, số liệu, cam kết ("chữa khỏi", "100%", "rẻ nhất"…) mà video gốc không có. Không chửi thề.
- Độ dài: cả bài đọc khoảng **{{target_s}} giây** ở tốc độ giọng ~{{cps}} chữ/giây → khoảng **{{target_chars}} chữ**
  (không tính dấu cách, dấu câu). Tool đếm và bắt viết lại nếu thiếu / thừa. Giọng đọc phải PHỦ KÍN video từ đầu tới
  cuối — thiếu chữ là video có khoảng chỉ còn nhạc, rất dở: thà đủ ý, đủ chi tiết còn hơn viết cụt. Mỗi phần tử `lines` là 1 câu (hoặc 2 câu
  rất ngắn), đọc khoảng 2–7 giây.
- `keyword` = CHỮ NHẤN của câu: 1 từ / cụm ngắn đắt nhất (≤ {{title_max}} ký tự, ngôn ngữ đích, lấy đúng chữ có trong câu
  — con số, tên món, tính từ mạnh…); tool hiện chữ to giữa màn lúc đọc câu đó. Khoảng một nửa số câu có, câu mở đầu nên có;
  câu không cần nhấn thì để rỗng.
- `text_vi` = nghĩa tiếng Việt; `shots_vi` = các cảnh dưới câu có gì (tiếng Việt, ngắn).

## Chọn cảnh (`shots`)
- Mỗi câu 1–3 cảnh, ghi giây GỐC `start`–`end`, nằm TRỌN trong một cảnh của danh sách "Các cảnh" bên dưới (không vắt qua
  điểm đổi cảnh — trừ khi video gốc tự cắt cảnh rất dày, cảnh < 2–3 giây, như video game / montage), mỗi cảnh ≥ 1 giây. Thứ tự trong `shots` = thứ tự hiện trên màn hình.
- Được lấy cảnh ở BẤT KỲ đâu trong video gốc và đảo thứ tự tùy ý cho khớp lời.
- Tổng độ dài các cảnh của một câu nên ≥ thời gian đọc câu đó (thiếu thì tool làm chậm nhẹ / thêm cảnh khác).
- Rải cảnh cho đều: cố dùng hết các cảnh đẹp của video; 2 câu liền nhau không dùng cùng một cảnh.
- Tránh cảnh mờ, rung, có chữ / logo của người khác, đoạn vi phạm chính sách (xem "Điều cấm").

## Kho cảnh chung (CHỈ dùng khi video gốc thiếu cảnh khớp lời)
Các cảnh đẹp tool đã lưu từ video khác (mã, độ dài, mô tả). Câu nào video gốc KHÔNG có cảnh đúng thứ câu đó nói (hoặc
cảnh quá ít, phải lặp nhiều) thì được lấy cảnh kho: trong `shots` ghi `lib` = mã (vd "L12"), `start`–`end` tính TRONG
cảnh kho (0 → độ dài cảnh). Cảnh kho phải THỂ HIỆN ĐÚNG điều câu nói (không lấy cảnh "na ná"); không có cảnh khớp thì
thôi — dùng cảnh video gốc, tool tự bù. Cảnh kho chiếm tối đa {{lib_share}} tổng cảnh; cảnh video gốc để `lib` rỗng.
{{library}}

## Tiêu đề và nhạc
- `titles_top`: 2 dòng tiêu đề CHỮ RẤT TO cố định phía trên video, ngôn ngữ đích, mỗi dòng ≤ {{title_max}} ký tự, gây tò
  mò, đúng nội dung (không spoil hết, không nhắc nền tảng khác).
- `music`: chọn một bài trong danh sách nhạc (đúng tên) hợp không khí; không bài nào hợp thì `name: null`.

{{localize_brief}}

## Góp ý của chủ dự án
{{feedback}}

## Điều cấm
{{sensitive_notes}}
{{policy_cuts}}

## Tóm tắt nội dung video gốc
{{summary}}

## Nhạc có sẵn
{{music_list}}

## Danh mục cảnh của video (giây gốc) — chỉ chọn cảnh trong danh sách này
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời nói gốc (nếu có — để hiểu nội dung, lấy thông tin thật như tên, giá… KHÔNG dịch lại từng câu)
{{transcript}}
