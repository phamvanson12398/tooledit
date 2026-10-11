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

{{voice_note}}
## 2. Giọng từng nhân vật (`cast`)
Với MỖI nhân vật có trong `speaker`, thêm một phần tử `cast`: `speaker` (đúng tên), `instruct` = mô tả giọng cho máy đọc
OmniVoice bằng thuộc tính TIẾNG ANH cách nhau dấu phẩy, chỉ chọn trong: male / female; child / teenager / young adult /
middle-aged / elderly; very low pitch / low pitch / moderate pitch / high pitch / very high pitch; whisper (khi nhân vật
thì thầm) — vd "male, young adult, high pitch"; `note_vi` = chất giọng / tính cách (tiếng Việt, ngắn) để chủ dự án chọn
giọng khi thu tay.

## 3. Dịch thoại — MỖI CÂU GỐC ĐÚNG MỘT CÂU DỊCH
- Bên dưới là {{n_lines}} câu thoại gốc đã đánh số, kèm giây gốc. `lines` phải có ĐÚNG {{n_lines}} phần tử, theo đúng
  thứ tự số: phần tử thứ k là bản dịch của câu gốc số k. KHÔNG gộp câu, KHÔNG bỏ câu nào, KHÔNG thêm câu — kể cả câu rất
  ngắn, câu cảm thán, tiếng kêu có chữ ("え？" → "어?", "うわっ！" → "으악!"): chỗ nào nhân vật mở miệng thì phải có giọng lồng.
- `source_start` / `source_end`: chép đúng giây của câu gốc đó (tool tự đặt lại cho khớp, bạn không cần chọn).
- Dịch ĐỦ Ý từng câu (chủ dự án: "đừng sót ý") — không lược bỏ chi tiết, câu đùa, lời đáp của câu gốc; chỉ nói gọn lại
  cách diễn đạt khi cần cho vừa thời gian.
- Dịch thành văn NÓI tự nhiên của người bản xứ {{market}}, ĐÚNG TÍNH CÁCH từng nhân vật (trẻ con nói kiểu trẻ con, người
  già kiểu người già, cáu thì cáu, đùa thì đùa); xưng hô đúng quan hệ nhân vật. Không dịch từng chữ.
- Đọc kịp trong thời gian câu gốc (khớp miệng): tối đa khoảng {{max_cps}} ký tự/giây theo độ dài ghi ở mỗi câu (không tính
  dấu cách, dấu câu) — câu gốc ngắn thì dịch ngắn, nói gọn ý chính, không bịa thêm.
- Một câu gốc mà 2 người nói xen nhau: vẫn MỘT phần tử, `speaker` = người nói phần chính.
- `kind` luôn là "dub" (chế độ này KHÔNG có lời dẫn — chỗ không ai nói tool tự giữ âm thanh gốc).
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

## Khung hình gần từng câu thoại (mở bằng Read để xem ai đang nói) — giây gốc
{{frames}}

## {{n_lines}} câu thoại gốc cần dịch ([giây gốc, độ dài] lời thoại)
{{source_lines}}
