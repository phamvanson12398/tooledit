# Nhiệm vụ: LỒNG TIẾNG NHÂN VẬT — dịch thoại video số {{video_index}} sang {{language_name}} và ghi rõ AI ĐANG NÓI từng câu

Phim gốc nói {{source_name}}. Bản TikTok giữ nguyên hình + nhạc + tiếng nền gốc; chỉ GIỌNG NÓI của các nhân vật được thay
bằng {{language_name}} — chủ dự án tự thu voice cho TỪNG NHÂN VẬT (mỗi nhân vật một giọng) theo đúng các câu bạn viết, và
phụ đề chính là các câu này.

## 1. Nhận diện nhân vật (rất quan trọng)
- Với MỖI câu thoại gốc, xác định ai nói: dựa vào tên gọi / xưng hô trong lời thoại, ai hỏi ai đáp, mạch hội thoại,
  và KHUNG HÌNH gần câu đó (mở bằng Read — xem nhân vật nào đang mở miệng / ở cận cảnh).
- `speaker` = TÊN nhân vật, viết THỐNG NHẤT suốt video (cùng một người luôn cùng một tên, vd luôn "징징이" hoặc luôn
  "Squidward" — chọn tên khán giả {{market}} quen; xem "Tên riêng đúng"). Không biết tên thì đặt theo đặc điểm, ngắn, dễ
  nhớ: "Cậu bé áo đỏ", "Ông chủ", "Người dẫn chuyện".
- Một câu gốc có 2 người nói xen nhau thì TÁCH thành 2 câu, mỗi câu một `speaker`.

## 2. Dịch thoại
- Mỗi phần tử `lines` = một câu thoại gốc: `source_start`–`source_end` là giây GỐC của câu đó (lấy theo lời thoại bên
  dưới), nằm gọn trong MỘT clip được giữ, theo thứ tự, không chồng nhau — giọng lồng sẽ đặt đúng lúc nhân vật mở miệng.
- Dịch thành văn NÓI tự nhiên của người bản xứ {{market}}, ĐÚNG TÍNH CÁCH từng nhân vật (trẻ con nói kiểu trẻ con, người
  già kiểu người già, cáu thì cáu, đùa thì đùa); xưng hô đúng quan hệ nhân vật. Không dịch từng chữ.
- Đọc kịp trong thời gian câu gốc: mỗi câu dài {{line_min}}–{{line_max}} giây, tối đa khoảng {{max_cps}} ký tự/giây
  (không tính dấu cách, dấu câu) — câu gốc dài thì nói gọn ý chính, không bịa thêm. Câu gốc rất ngắn liền nhau của CÙNG
  một người thì gộp.
- Tiếng hét / cười / thở / tiếng kêu không thành lời: KHÔNG viết thành câu (giữ âm thanh gốc nếu được).
- `kind` luôn là "dub" (chế độ này KHÔNG có lời dẫn — chỗ không ai nói để nguyên tiếng nền gốc).
- `text_vi` = nghĩa tiếng Việt; `action_vi` = nhân vật đang làm gì (ngắn, để chủ dự án nhập vai khi thu); `adapt_vi` =
  chỗ bản địa hóa (đổi cách đùa / đơn vị…), không có thì để trống.
- Không chửi thề, không nhắc nền tảng khác ngoài TikTok, không nhắc nội dung đã bị cắt vì chính sách.

{{localize_brief}}

## Điều cấm
{{sensitive_notes}}

## Tóm tắt nội dung
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Clip được giữ (giây gốc, theo thứ tự trên video)
{{clips}}

## Khung hình gần từng câu thoại (mở bằng Read để xem ai đang nói) — giây gốc
{{frames}}

## Lời thoại gốc ([giây gốc] lời thoại)
{{transcript}}
