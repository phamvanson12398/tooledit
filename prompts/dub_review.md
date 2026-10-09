# Nhiệm vụ: VIẾT TRƯỚC bài lời đọc REVIEW (kể chuyện) cho đoạn phim / hoạt hình số {{video_index}} — {{language_name}}, {{market}}

Cách làm việc của chủ dự án (chốt 09/10): bạn viết TRƯỚC một bài lời đọc liền mạch → chủ dự án đọc CẢ BÀI vào một file
voice → tool dựa vào voice để CHỌN CẢNH và DỰNG (câu nào kể đoạn phim nào thì hình đoạn đó chạy dưới câu đó, cắt cảnh
nhanh 1–3 giây, dài đúng bằng câu đọc). Tiếng phim TẮT HẲN — phim chỉ lấy HÌNH; toàn bộ âm thanh là giọng kể (+ nhạc nền
nhẹ). Phim gốc nói {{source_name}} — lời thoại gốc chỉ để bạn HIỂU chuyện, không dịch lại; điều quan trọng nhân vật nói
thì KỂ lại bằng lời của người review.

## Đây là KỂ CHUYỆN, không phải thuyết minh hình ảnh
SAI (tả cảnh): "Cậu bé đang chạy trên đường. Con mèo đang nhìn cậu. Bây giờ cậu ấy đang mở cửa."
ĐÚNG (kể chuyện) — chủ dự án chốt đúng giọng này:
- "Cả đời cậu bé chỉ mong một điều: tìm lại con mèo đã mất. Nhưng cậu không ngờ, thứ chờ cậu sau cánh cửa ấy lại là…"
- 한국어: "소년의 소원은 단 하나, 잃어버린 고양이를 찾는 것이었습니다. 그런데 그 문 뒤에서 기다리고 있던 건…"
- 日本語: "少年の願いはただ一つ、いなくなった猫を見つけることでした。でも、その扉の向こうで待っていたのは…"
- English: "All the boy ever wanted was to find his lost cat. But what was waiting behind that door… he never saw coming."
Công thức: nhân vật + điều họ khao khát / hoàn cảnh → "nhưng / không ngờ" → bỏ lửng hoặc hé lộ → câu sau trả lời và mở
tiếp mâu thuẫn mới; cả bài là chuỗi những nhịp như vậy nối nhau tới cao trào và kết.

## Cách viết
1. XEM HẾT CÁC KHUNG HÌNH bên dưới (mở từng file bằng Read) + đọc lời thoại để hiểu trọn diễn biến của đoạn phim.
2. Viết `story_vi` (tiếng Việt) TRƯỚC: dàn ý mở đầu (nhân vật, hoàn cảnh, muốn gì) → mâu thuẫn → cao trào → kết.
3. Viết bài lời đọc theo dàn ý: câu đầu kéo người xem ở lại ngay; các câu NỐI nhau bằng nhân – quả, thời gian (vì thế,
   nhưng, ngay lúc đó, không ngờ, thế là, cuối cùng…); kể động cơ, cảm xúc nhân vật (chỉ khi phim cho thấy rõ); thỉnh
   thoảng một câu bình luận ngắn của người kể; câu cuối khép lại câu chuyện có dư âm. Không "xem phần sau", không kêu gọi
   follow / subscribe, không nhắc nền tảng khác. KHÔNG thuật lại "ai đang làm gì"; không mở câu bằng "Bây giờ…", "Cảnh này…".
4. GIỌNG KỂ thì QUÁ KHỨ, đều, cuốn — tiếng Hàn "~습니다 / ~었죠 / ~였는데요"; tiếng Nhật "〜でした / 〜んです";
   tiếng Anh thì quá khứ, câu ngắn có nhịp.
5. ĐÚNG SỰ THẬT: tên nhân vật đúng như trong phim (xem "Tên riêng đúng"); không rõ tên thì gọi theo đặc điểm. Không bịa
   tình tiết, kết cục ngoài đoạn này.

6. TỰ NHIÊN NHƯ NÓI (rất quan trọng — chủ dự án chê "chưa hay, chưa tự nhiên"): viết văn NÓI của người bản xứ, không
   văn viết, không dịch máy; câu dài ngắn xen kẽ, câu ngắn bật ra ở chỗ bất ngờ; KHÔNG lặp cùng một từ nối ở nhiều câu
   liền (그런데 / でも / but…); không giải thích điều hình đã cho thấy; chêm chút hài / cảm xúc của người kể đúng chỗ.

## Văn mẫu chủ dự án thích (học GIỌNG, NHỊP, CÁCH NỐI CÂU — không chép nội dung)
{{style_examples}}

## Góp ý của chủ dự án
{{feedback}}

{{localize_brief}}

## Độ dài và gắn đoạn phim
- Cả bài đọc khoảng **{{target_s}} giây** ở tốc độ giọng chủ dự án ~{{cps}} chữ/giây → khoảng **{{target_chars}} chữ**
  (không tính dấu cách, dấu câu). Tool sẽ đếm và bắt viết lại nếu thiếu / thừa.
- Mỗi phần tử `lines` là 1 câu (hoặc 2 câu rất ngắn), đọc khoảng 2–10 giây.
- `source_start`–`source_end` = ĐOẠN PHIM (giây gốc) mà câu đó kể — tool sẽ cắt cảnh nhanh trong đoạn này để chạy dưới
  câu. Đoạn phim phải dài ít nhất bằng thời gian đọc câu (thường dài hơn nhiều — tool chọn khúc đắt nhất), theo đúng
  thứ tự phim, các câu KHÔNG chồng đoạn phim lên nhau; được bỏ qua đoạn nhạt giữa 2 câu.
- `kind`: "narration"; `text_vi` = nghĩa tiếng Việt (cũng giọng kể chuyện); `action_vi` = đoạn phim đó có gì (tiếng Việt,
  ngắn, để chủ dự án đối chiếu); `adapt_vi` = chỗ bản địa hóa, không có thì để trống.
- Không chửi thề, không nhắc nội dung đã bị cắt vì chính sách.

## Điều cấm
{{sensitive_notes}}

## Tóm tắt nội dung đoạn này (giây gốc {{range}})
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Hook đã dùng (đứng trước, không lặp lại)
{{hook}}

## Các cảnh trong đoạn phim (giây gốc)
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời thoại gốc để hiểu chuyện ([giây gốc] lời thoại — KHÔNG dịch lại)
{{transcript}}
