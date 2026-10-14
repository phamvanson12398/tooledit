# Nhiệm vụ: dịch PHỤ ĐỀ cho đoạn short mở đầu — {{language_name}}, {{market}} (video số {{video_index}})

Đầu video review là một đoạn SHORT cắt nguyên từ phim (giữ hình + tiếng gốc {{source_name}}). Người xem nghe tiếng gốc
và ĐỌC phụ đề bằng {{language_name}}. Hãy dịch từng câu thoại gốc dưới đây thành một câu phụ đề.

## Cách dịch
- Như phụ đề phim chuyên nghiệp của nước đó: gọn (đọc kịp trong thời lượng câu), tự nhiên, đúng giọng nhân vật (đang
  la hét thì phụ đề cũng gấp gáp), không dịch máy, không giải thích thêm.
- Giữ đúng nghĩa, không bịa thêm; câu chửi thề thì viết nhẹ đi (TikTok).
- Tên riêng đúng như danh sách dưới.
- Mỗi câu gốc đúng MỘT phần tử `lines` (`i` = số câu), `text` = phụ đề {{language_name}}, `text_vi` = nghĩa tiếng Việt.
- Câu gốc chỉ là tiếng kêu / thở / Whisper nghe nhầm vô nghĩa thì `text` để rỗng.

## Bối cảnh phim
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Câu thoại gốc trong short ([số] (giây gốc) lời thoại)
{{lines}}
