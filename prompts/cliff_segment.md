# Nhiệm vụ: chia phim thành các PHẦN cho video "REVIEW BỎ LỬNG" (mỗi phần một video TikTok)

Phim dài {{duration}} giây; đoạn cần kể {{range}} giây. Chủ dự án muốn kể HẾT phim theo dạng series review: mỗi phần là
một video {{min_video_s}}–{{max_video_s}} giây gồm (1) một đoạn SHORT kịch tính cắt nguyên từ phim đặt lên đầu, rồi (2)
lời review kể lại đoạn phim của phần đó (tiếng phim tắt, chỉ có giọng kể + nhạc nhẹ), kết BỎ LỬNG để người xem chờ phần sau.
{{chunk_note}}

## Luật bắt buộc
- **KHÔNG BỎ CẢNH**: các phần phủ KÍN đoạn {{range}} theo đúng thứ tự phim — phần đầu bắt đầu đúng giây đầu, phần sau
  bắt đầu ĐÚNG chỗ phần trước kết thúc (không hở, không chồng), phần cuối kết thúc đúng giây cuối. Đoạn nhạt cũng phải nằm
  trong một phần (bước sau sẽ kể lướt), không được bỏ ra ngoài.
- Mỗi phần {{min_raw_s}}–{{max_raw_s}} giây phim gốc (phần cuối được ngắn hơn). Không giới hạn số phần — phim dài thì
  nhiều phần, cho tới khi hết phim.
- **Điểm chia = chỗ BỎ LỬNG**: kết thúc mỗi phần (trừ phần cuối) NGAY TRƯỚC lúc lộ kết quả của một tình huống căng — cú
  twist sắp lộ, quyết định sống còn, ai đó sắp bị phát hiện, cuộc đối đầu sắp nổ ra… Không chia giữa một câu thoại, không
  chia ở chỗ câu chuyện đang yên ả nếu gần đó có chỗ gay cấn hơn. `cliff_vi` ghi người xem đang thắc mắc gì (phần cuối:
  phim kết ra sao).
- **Short mở đầu** (`hook`): {{hook_lo}}–{{hook_hi}} giây, NẰM TRONG phần đó, là khoảnh khắc kịch tính / gây sốc / hài nhất
  của phần (pha đánh nhau, câu thoại đắt, cú bất ngờ, biểu cảm cực mạnh) — xem là muốn biết chuyện gì dẫn tới đó. Short
  được giữ NGUYÊN (hình + tiếng gốc), nên chọn đoạn tự đứng được: bắt đầu / kết thúc ở chỗ ngắt câu, không cắt giữa câu
  thoại. Không lấy đúng cái kết bỏ lửng của phần (đừng tự lộ đáp án), không lấy đoạn vi phạm chính sách. `why_vi` nói vì sao.
- `narrator_vi`: tên nhân vật chính của phim (đúng tên trong phim; không rõ tên thì gọi theo đặc điểm) — dùng khi kể ở
  ngôi thứ nhất.
- `title_vi`, `summary_vi` tiếng Việt, ngắn. Không bịa nội dung không có trong phim.

## Điều cấm
{{sensitive_notes}}

## Đoạn vi phạm chính sách TikTok (sẽ bị CẮT khỏi video — không làm short ở đây)
{{policy_cuts}}

## Tóm tắt toàn bộ
{{summary}}

## Tên riêng đúng
{{name_corrections}}

## Khoảnh khắc đáng chú ý
{{key_moments}}

## Sự kiện âm thanh (máy tự dò)
{{audio_events}}

## Cảnh (giây)
{{scenes}}

## Khung hình
{{frames}}

## Lời thoại ([giây bắt đầu–kết thúc] lời thoại)
{{transcript}}
