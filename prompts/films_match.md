# Nhiệm vụ: tìm CẢNH trong phim "{{title}}" ({{title_vi}}) cho từng câu đọc

Video mới kể về nhiều phim; các câu dưới đây nói về phim này (nhân vật: {{characters}}). Phim dài {{duration}} giây.
Hãy XEM CÁC KHUNG HÌNH bên dưới (mở bằng Read — mỗi ảnh lưới có ghi tên file / giây) rồi chọn cho MỖI câu một đoạn phim.

## Luật
- `line` = số câu như danh sách; `start`–`end` = đoạn phim (giây) đúng cảnh `cần cảnh` mô tả, rõ nhân vật được nhắc.
- Câu **video**: đoạn phim dài ít nhất bằng thời gian đọc câu (dài hơn càng tốt — tool tự cắt khúc đắt), nằm trong MỘT
  cảnh liền hoặc vài cảnh liền nhau cùng sự việc.
- Câu **DỪNG HÌNH**: `freeze_t` = giây đứng hình — khoảnh khắc đắt nhất, thấy RÕ mặt / biểu cảm nhân vật, hình không mờ,
  không đang chuyển cảnh; `start` sớm hơn `freeze_t` ít nhất {{lead}} giây (đoạn video chạy trước khi đứng).
- Hai câu không dùng cùng một cảnh. Chỉ chọn cảnh bạn THẤY trong khung hình (ghi tên file ở `why_vi`); không đoán mò.
  Không tìm được cảnh đúng thì chọn cảnh gần nhất có nhân vật đó và ghi rõ trong `editor_notes`.

## Các câu cần cảnh
{{lines}}

## Điểm đổi cảnh trong phim (giây)
{{scenes}}

## Khung hình — giây trong phim
{{frames}}

## Lời thoại (nếu có)
{{transcript}}
