# Nhiệm vụ: KỂ LẠI đoạn phim / hoạt hình số {{video_index}} thành MỘT CÂU CHUYỆN bằng {{language_name}} cho {{market}}

Video này là một clip REVIEW KỂ CHUYỆN: các cảnh hay của phim chạy liên tục, tiếng phim hạ nhỏ bên dưới, người xem nghe
GIỌNG KỂ của bạn (chủ dự án tự thu voice từng câu) và đọc phụ đề chính là các câu này. Phim gốc nói {{source_name}} —
lời thoại gốc dưới đây chỉ để bạn HIỂU chuyện, không dịch lại.

## Đây là KỂ CHUYỆN, không phải thuyết minh hình ảnh
Như các kênh review / tóm tắt phim nổi tiếng của {{market}}: người xem nghe như đang được kể một câu chuyện cuốn hút,
hình phim chỉ MINH HỌA cho lời kể.

SAI (tả cảnh — KHÔNG viết kiểu này):
- "Cậu bé đang chạy trên đường. Con mèo đang nhìn cậu. Bây giờ cậu ấy đang mở cửa."

ĐÚNG (kể chuyện):
- "Cả đời cậu bé chỉ mong một điều: tìm lại con mèo đã mất. Nhưng cậu không ngờ, thứ chờ cậu sau cánh cửa ấy lại là…"

Cách làm:
1. TRƯỚC KHI viết lời, viết `story_vi` (tiếng Việt): dàn ý câu chuyện của đoạn này —
   **mở đầu** (nhân vật là ai, hoàn cảnh, họ muốn gì) → **mâu thuẫn** (trở ngại, chuyện bất ngờ) → **cao trào** →
   **kết** (kết quả, ý nghĩa / dư âm).
2. Viết lời theo đúng dàn ý đó. Mỗi câu đẩy câu chuyện đi tiếp; các câu NỐI với nhau bằng nhân – quả và thời gian
   (vì thế, nhưng, ngay lúc đó, không ngờ, thế là, cuối cùng…), không phải những câu rời nhau.
3. Kể ĐỘNG CƠ và CẢM XÚC nhân vật (muốn gì, sợ gì, vì sao làm vậy — chỉ khi phim cho thấy rõ), tạo tò mò, giấu bớt rồi
   hé lộ đúng lúc. Thỉnh thoảng một câu bình luận ngắn của người kể ("ai mà ngờ được", "đây mới là lúc đáng xem").
4. KHÔNG thuật lại "ai đang làm gì" trên hình. Không mở câu bằng "Bây giờ…", "Ở đây…", "Cảnh này…". Tối đa vài câu được
   tả hành động, và phải là hành động then chốt của câu chuyện.
5. Câu đầu tiên kéo người xem ở lại ngay (mâu thuẫn / bí ẩn / tình huống lạ của câu chuyện). Câu cuối khép lại câu
   chuyện có dư âm. Không "xem phần sau", không kêu gọi follow / subscribe, không nhắc nền tảng khác.
6. ĐÚNG SỰ THẬT của phim: gọi nhân vật bằng tên có trong phim (xem "tên riêng đúng" / lời thoại); không rõ tên thì gọi
   theo đặc điểm (cậu bé áo đỏ, chú mèo trắng…). Không bịa tình tiết, kết cục ngoài đoạn này.
7. Khoảnh khắc ĐẮT (câu thoại chốt, cú twist, tiếng cười) thì NGỪNG kể 1–3 giây để tiếng phim tự lên, rồi kể tiếp.
8. XEM KHUNG HÌNH (mở từng file bằng Read) để hiểu đúng diễn biến và đặt câu nào lên cảnh nào.

{{localize_brief}}

## Luật thời gian
- Mỗi câu (`lines`) đặt lên đoạn hình minh họa cho nó: `source_start`–`source_end` là giây GỐC, nằm gọn trong MỘT clip
  được giữ, các câu theo thứ tự, không chồng nhau. Câu đầu tiên bắt đầu ngay đầu clip đầu tiên.
- Mỗi câu dài {{line_min}}–{{line_max}} giây; đọc kịp: tối đa khoảng {{max_cps}} ký tự/giây (không tính dấu cách, dấu câu).
- Kể GẦN NHƯ LIÊN TỤC: lời phủ khoảng 70–90% thời lượng; chỉ chừa khoảng lặng ở khoảnh khắc đắt.
- `kind`: "narration" cho lời kể; "dub" nếu câu thuật lại đúng lời nhân vật đang nói.
- `text_vi` = nghĩa tiếng Việt (cũng là giọng kể chuyện); `action_vi` = trên hình đang có gì (tiếng Việt, ngắn — chỉ để
  chủ dự án đối chiếu, KHÔNG đưa vào lời kể); `adapt_vi` = chỗ bạn bản địa hóa, không có thì để trống.
- Không chửi thề, không nhắc nội dung đã bị cắt vì chính sách.

## Điều cấm
{{sensitive_notes}}

## Tóm tắt nội dung đoạn này
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Hook đã dùng (đứng trước, không lặp lại)
{{hook}}

## Clip được giữ (giây gốc, theo thứ tự trên video)
{{clips}}

## Khung hình (mở bằng Read để xem) — giây gốc
{{frames}}

## Lời thoại gốc để hiểu chuyện ([giây gốc] lời thoại — KHÔNG dịch lại)
{{transcript}}
