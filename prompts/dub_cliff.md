# Nhiệm vụ: VIẾT TRƯỚC bài lời đọc "REVIEW BỎ LỬNG" phần {{part}} — {{language_name}}, {{market}} (video số {{video_index}})

Cách làm việc của chủ dự án: bạn viết TRƯỚC một bài lời đọc liền mạch → chủ dự án đọc CẢ BÀI vào một file voice → tool
dựa vào voice để CHỌN CẢNH và DỰNG (câu nào kể đoạn phim nào thì hình đoạn đó chạy dưới câu đó, cắt cảnh nhanh 1–3 giây).
Tiếng phim TẮT HẲN trong phần review — toàn bộ âm thanh là giọng kể (+ nhạc nền nhẹ). Phim gốc nói {{source_name}} — lời
thoại gốc chỉ để bạn HIỂU chuyện, không dịch lại; điều quan trọng nhân vật nói thì KỂ lại bằng lời của người review.

## Video này gồm gì
1. Đầu video: một đoạn SHORT cắt nguyên từ phim, giữ hình + tiếng gốc: {{hook_clip}}.
   Bạn KHÔNG viết lời cho short; câu đầu tiên của bạn cất lên NGAY SAU short — nối vào sự tò mò short vừa gợi ra (kiểu
   "Chuyện gì đã dẫn tới cảnh này? Mọi thứ bắt đầu từ…"), rồi kể theo đúng thứ tự phim. Không tả lại short.
2. Lời review kể đoạn phim của phần này: giây gốc {{range}}.

## Phần {{part}} của series — KỂ HẾT, KHÔNG BỎ CẢNH
- Kể theo đúng thứ tự phim, phủ KÍN đoạn {{range}}: câu đầu kể từ đầu đoạn, đoạn phim của câu sau NỐI TIẾP câu trước,
  câu cuối kể tới cuối đoạn. Chỗ quan trọng kể kỹ vài câu, chỗ ít quan trọng gói lại bằng MỘT câu lướt (câu đó gắn đoạn
  phim dài) — không được bỏ trống đoạn nào (tool kiểm tra).
- {{recap_rule}}
- {{ending_rule}}

Các phần trước đã kể (để nối mạch, không kể lại):
{{prev_parts}}

## Ngôi kể
{{pov_rule}}
Tool tự kiểm tra ngôi kể và bắt viết lại nếu sai. `text_vi` (nghĩa tiếng Việt) cũng dùng đúng ngôi đó.

## Đây là KỂ CHUYỆN, không phải thuyết minh hình ảnh
SAI (tả cảnh): "Cậu bé đang chạy trên đường. Con mèo đang nhìn cậu. Bây giờ cậu ấy đang mở cửa."
ĐÚNG (kể chuyện): nhân vật + điều họ khao khát / hoàn cảnh → "nhưng / không ngờ" → hé lộ → câu sau trả lời và mở tiếp mâu
thuẫn mới; cả bài là chuỗi nhịp như vậy. Nối câu bằng nhân – quả, thời gian (vì thế, nhưng, ngay lúc đó, không ngờ, thế
là…); KHÔNG lặp cùng một từ nối ở nhiều câu liền; không mở câu bằng "Bây giờ…", "Cảnh này…"; không kêu gọi follow /
subscribe, không nhắc nền tảng khác.

## Cách viết
1. XEM HẾT CÁC KHUNG HÌNH bên dưới (mở từng file bằng Read) + đọc lời thoại để hiểu trọn diễn biến của đoạn.
2. Viết `story_vi` (tiếng Việt) TRƯỚC: dàn ý của phần này (bối cảnh → diễn biến → chỗ dừng bỏ lửng / kết).
3. Viết bài lời đọc theo dàn ý — văn NÓI của người bản xứ, không dịch máy; câu dài ngắn xen kẽ, câu ngắn bật ra ở chỗ
   bất ngờ; chêm chút cảm xúc / hài đúng chỗ.
4. ĐÚNG SỰ THẬT: tên nhân vật đúng như trong phim (xem "Tên riêng đúng"); không bịa tình tiết ngoài những gì phim cho thấy.

## Văn mẫu chủ dự án thích (học GIỌNG, NHỊP, CÁCH NỐI CÂU — không chép nội dung)
{{style_examples}}

## Góp ý của chủ dự án
{{feedback}}

{{localize_brief}}

## Độ dài và gắn đoạn phim
- Cả bài đọc khoảng **{{target_s}} giây** ở tốc độ giọng chủ dự án ~{{cps}} chữ/giây → khoảng **{{target_chars}} chữ**
  (không tính dấu cách, dấu câu) — cộng với short là đủ {{video_s}} giây. Tool sẽ đếm và bắt viết lại nếu thiếu / thừa.
- Mỗi phần tử `lines` là 1 câu (hoặc 2 câu rất ngắn), đọc khoảng 2–10 giây.
- `source_start`–`source_end` = ĐOẠN PHIM (giây gốc) mà câu đó kể; đoạn phim phải dài ít nhất bằng thời gian đọc câu
  (thường dài hơn nhiều), theo đúng thứ tự phim, các câu không chồng đoạn phim lên nhau và nối tiếp nhau.
- `kind`: "narration"; `action_vi` = đoạn phim đó có gì (tiếng Việt, ngắn); `adapt_vi` = chỗ bản địa hóa, không có thì trống.
- Không chửi thề, không nhắc nội dung đã bị cắt vì chính sách.

## Điều cấm
{{sensitive_notes}}

## Tóm tắt phần này (giây gốc {{range}})
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Các cảnh trong đoạn (giây gốc)
{{scenes}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời thoại gốc để hiểu chuyện ([giây gốc] lời thoại — KHÔNG dịch lại)
{{transcript}}
