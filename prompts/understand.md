# Nhiệm vụ: hiểu nội dung footage

Xem transcript và các khung hình dưới đây, rồi cho biết:
- thể loại, không khí, số người xuất hiện, chủ thể chính;
- ngôn ngữ chính của video (ko / ja / en);
- tóm tắt một dòng bằng tiếng Việt (người dùng sẽ duyệt câu này);
- phong cách dựng phù hợp nhất (ghi đúng tên preset ở đầu dòng) trong danh sách:
{{styles}}
- 3–8 khoảnh khắc đáng chú ý (mốc giây trong footage gốc, lý do bằng tiếng Việt) — dùng cho hook và kế hoạch dựng;
- `usable_range`: đoạn chứa mạch nội dung chính (bỏ phần thừa, phần bị cắt dở);
- `name_corrections`: tên riêng/từ mà transcript tự động nghe sai, kèm căn cứ (chữ trên khung hình, ngữ cảnh).
  Chỉ ghi khi chắc chắn; phụ đề sẽ tự thay theo bảng này;
- `burned_in_text`: footage gốc có sẵn chữ in trên hình không, ở vùng nào (để bố cục tránh chồng chữ);
- `policy_issues`: MỌI đoạn vi phạm Nguyên tắc cộng đồng TikTok (xem phần "Chính sách TikTok" ở trên) — mốc giây gốc,
  `category`, lý do tiếng Việt. Các đoạn này sẽ bị CẮT BỎ khỏi video. Đánh dấu hẹp đúng chỗ vi phạm (một câu chửi
  thề thì chỉ đoạn câu đó), không đánh dấu cả phút nếu chỉ vài giây vi phạm. Không có thì để [];
  Lời thoại hoặc chữ trên hình nhắc tới nền tảng khác (YouTube, Instagram, "구독과 좋아요", "チャンネル登録"...) cũng là
  vi phạm (`category: other_platform`). Logo/watermark nền tảng khác nằm suốt video thì không đánh dấu cắt, mà ghi vào
  `burned_in_text` và `sensitive_notes_vi` để người dùng che/crop;
- `sensitive_notes_vi`: điều không được viết hay ám chỉ trên màn hình/hook (ví dụ câu đùa giả định dễ bị
  hiểu là sự thật, chuyện riêng tư, cáo buộc).

Phong cách mặc định của khách (nếu có): {{client_style}}

## Thông tin footage
- Thời lượng: {{duration}} giây, khung {{width}}x{{height}}, {{scene_count}} cảnh.
- Ngôn ngữ nhận dạng tự động: {{language}}

## Cảnh (giây bắt đầu–kết thúc)
{{scenes}}

## Transcript ([giây bắt đầu–kết thúc] lời thoại)
{{transcript}}

## Khung hình (tên file — giây)
{{frames}}
