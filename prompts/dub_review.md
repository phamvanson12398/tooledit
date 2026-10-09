# Nhiệm vụ: XEM đoạn phim / hoạt hình số {{video_index}} và VIẾT LỜI REVIEW {{language_name}} cho {{market}}

Video này là một clip REVIEW: các cảnh hay của phim chạy liên tục, tiếng phim được hạ nhỏ bên dưới, người xem nghe LỜI
REVIEW bạn viết (chủ dự án tự thu voice từng câu) và đọc phụ đề chính là các câu này. Phim gốc nói {{source_name}} —
lời thoại gốc dưới đây chỉ để bạn HIỂU chuyện, không dịch lại.

Viết như một kênh review phim / hoạt hình nổi tiếng của {{market}}:
- XEM KHUNG HÌNH (mở từng file bằng Read) để biết nhân vật nào, đang làm gì, ở giây nào. Nói đúng điều đang thấy.
- Câu đầu tiên phải KÉO người xem ở lại ngay: tình huống lạ / câu hỏi / chi tiết gây tò mò của đoạn này.
- KỂ LẠI câu chuyện của đoạn phim theo thứ tự trên hình, gọn, có nhịp, xen BÌNH LUẬN của người review: cảm xúc, nhận xét
  nhân vật, chỗ hài / cảm động / thông minh, so sánh gần gũi với khán giả nước mình, đùa đúng kiểu họ thích.
- Gọi nhân vật bằng tên có trong phim (xem "tên riêng đúng" / lời thoại); không rõ tên thì gọi theo đặc điểm
  (cậu bé áo đỏ, chú mèo trắng…). Không bịa tên, tình tiết, kết cục ngoài đoạn này.
- Khoảnh khắc ĐẮT (câu thoại chốt, cú twist, tiếng cười) thì NGỪNG nói 1–3 giây để tiếng phim tự lên, rồi bình luận tiếp.
- Kết: một câu nhận xét / cảm nghĩ có dư âm. Không "xem phần sau", không kêu gọi follow / subscribe, không nhắc nền tảng khác.

{{localize_brief}}

## Luật thời gian
- Mỗi câu (`lines`) gắn với đoạn hình nó nói tới: `source_start`–`source_end` là giây GỐC, nằm gọn trong MỘT clip được
  giữ, các câu theo thứ tự, không chồng nhau. Câu đầu tiên bắt đầu ngay đầu clip đầu tiên.
- Mỗi câu dài {{line_min}}–{{line_max}} giây; đọc kịp: tối đa khoảng {{max_cps}} ký tự/giây (không tính dấu cách, dấu câu).
- Review nói GẦN NHƯ LIÊN TỤC: lời phủ khoảng 70–90% thời lượng; chỉ chừa khoảng lặng ở khoảnh khắc đắt.
- `kind`: "narration" cho lời kể / bình luận; "dub" nếu câu thuật lại đúng điều nhân vật đang nói.
- `text_vi` = nghĩa tiếng Việt; `action_vi` = trên hình đang có gì (tiếng Việt, ngắn); `adapt_vi` = chỗ bạn bản địa hóa
  (ví dụ / cách đùa / đơn vị), không có thì để trống.
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
