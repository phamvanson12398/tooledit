# Báo cáo tương thích CapCut 9.5.0

Dựa trên dự án mẫu thật `samples/capcut_template/` (CapCut 9.5.0.4050 quốc tế, Windows 10),
mã nguồn `pycapcut` 0.0.3 và `capcut-cli` 0.26.0. Ngày 2026-09-25.
Bản mẫu trong repo đã xóa tên user Windows, `device_id`, `mac_address` (bằng
`tools/sanitize_draft.py`), bỏ ảnh bìa và file `.bak`.

## Kết luận nhanh

| Câu hỏi | Trả lời |
|---|---|
| Draft có bị mã hóa? | **Không.** Mọi file timeline là JSON thường, đọc/sửa được. |
| Phiên bản ghi trong draft | `app_version 9.5.0`, `app_source cc`, `version 360000`, `new_version 187.0.0` |
| pyCapCut dùng thẳng được không? | **Không nên dùng để tạo draft từ đầu** (dấu phiên bản 6.7.0, thiếu nhiều trường, chỉ ghi 1 file). Có thể mượn một phần logic. |
| capcut-cli dùng được không? | Đọc/chẩn đoán được (`version`, `diagnose` chạy tốt). Ghi thì "untested" với 9.5.0. |
| CapCut đọc file nào? | **`Timelines/<main_timeline_id>/draft_content.json`** (đã thử trên máy, xem mục 1). |
| Draft do tool sửa có mở được? | **Có.** Dự án thăm dò do script sửa được CapCut 9.5.0 mở bình thường, kể cả khi đã xóa `mini_draft.json`. |
| Hướng đi (chủ dự án đã đồng ý) | **Tự viết bộ ghi draft bằng Python, dựa trên dự án mẫu do CapCut 9.5.0 tạo**. Ghi vào file chính trong `Timelines/`, đồng bộ 3 bản còn lại, xóa `mini_draft.json`. |
| CapCut Pro | Chủ dự án **có Pro**, nên dùng được tài nguyên `is_vip`. |

## 1. Cấu trúc thư mục draft 9.5.0

```
<thư mục draft>/
  draft_content.json        ← timeline (bản 1)
  template-2.tmp            ← timeline (bản 2, giống hệt bản 1)
  draft_meta_info.json      ← tên draft, id, đường dẫn thư mục, danh sách media đã nhập
  key_value.json            ← thông tin tài nguyên thư viện (is_vip, danh mục...)
  draft_virtual_store.json, draft_settings, draft.extra (nhị phân), ...
  Timelines/
    project.json            ← main_timeline_id
    <main_timeline_id>/
      draft_content.json    ← timeline (bản 3)
      template-2.tmp        ← timeline (bản 4)
      template.tmp          ← bản rút gọn
      attachment_*.json, common_attachment/, draft.extra
```

- **Có 4 bản timeline giống hệt nhau từng byte**, cộng **bản thứ 5** ở
  `Timelines/<id>/attachment/patch/mini_draft.json` (định dạng khác: `draft` + danh sách
  `segments`, mỗi segment gói luôn vật liệu của nó). Không có `draft_info.json`.
- **Kết quả thử trên máy (2026-09-25).** Script `tools/make_probe_draft.py` tạo dự án thăm dò,
  trong đó mỗi bản timeline mang một nhãn chữ khác nhau:
  - `probe2` (đổi chữ ở cả 5 bản): CapCut hiện **`TRONG_CONTENT`**.
  - `probe3` (4 bản mang nhãn, đã xóa `mini_draft.json`): CapCut vẫn mở được, hiện **`TRONG_CONTENT`**.
  - → **File CapCut 9.5.0 thực sự đọc là `Timelines/<main_timeline_id>/draft_content.json`.**
    `mini_draft.json` không cần thiết, xóa đi vẫn mở bình thường. Các file ở gốc chỉ là bản sao.
  - Vòng 1 được báo là "hiện đúng chữ gốc". Kết quả đó không khớp với vòng 2, có lẽ do hiểu lệch câu hỏi. Vòng 2 có đối chứng rõ nên lấy vòng 2 làm căn cứ.
- `capcut diagnose` chọn `template-2.tmp` ở gốc làm bản chính. **Điều này sai với 9.5.0**, và mọi lệnh
  sửa của capcut-cli cũng chỉ ghi file ở gốc. → Không dùng capcut-cli để ghi.
- pyCapCut cũng chỉ ghi `draft_content.json` ở gốc → CapCut 9.5.0 sẽ **bỏ qua** thay đổi.
- Tool sẽ ghi file chính trong `Timelines/`, rồi chép cùng nội dung sang 3 bản kia cho nhất quán,
  và xóa `attachment/patch/` (mini_draft).
- `draft_meta_info.json` chứa `draft_fold_path` (đường dẫn thư mục) và `draft_name`. Khi tạo
  draft mới phải sửa hai trường này và cấp `draft_id` mới.
- Media (video) **không được chép vào thư mục draft**. Draft chỉ lưu đường dẫn tuyệt đối tới file
  gốc, ví dụ `C:/Users/.../final.mp4`. → Tool phải để footage ở một chỗ cố định trên máy.
- Trường `local_material_id` của video đang rỗng, do chính CapCut ghi, nên để rỗng là hợp lệ.
- Thời gian tính bằng micro giây (1 giây = 1 000 000).

## 2. So sánh với pyCapCut

Mình cho pyCapCut 0.0.3 tạo một draft (2 clip, 1 chuyển cảnh, 1 âm thanh, 1 chữ) rồi so với mẫu:

- Dấu phiên bản: pyCapCut ghi `app_version 6.7.0`, `new_version 140.0.0`, còn mẫu là 9.5.0 / 187.0.0.
  capcut-cli ghi nhận CapCut 8.7 **từ chối** draft mang dấu phiên bản cũ.
- Thiếu trường: vật liệu video thiếu khoảng 50 trường, âm thanh khoảng 50, chữ hơn 100, segment khoảng 27.
  Thiếu hẳn các vật liệu phụ mà 9.5.0 gắn vào mỗi clip: `canvases`, `sound_channel_mappings`,
  `vocal_separations`, `placeholder_infos`, `material_colors`, `beats`. Mỗi clip video của
  9.5.0 tham chiếu 7–8 vật liệu phụ, pyCapCut chỉ tạo 2.
- Chỉ ghi `draft_content.json` ở gốc. `duplicate_as_template` chép cả `Timelines/` nhưng khi
  lưu chỉ cập nhật file gốc, nên bản trong `Timelines/` sẽ cũ đi.
- Điểm dùng được: bảng `effect_id`/`resource_id` có sẵn (hiệu ứng, filter, font, animation...),
  cách tính keyframe, cách viết JSON nội dung chữ.

## 3. So sánh với capcut-cli

- `capcut version`: nhận đúng 9.5.0, `write_guard: ok`, trạng thái "untested" (chưa ai kiểm chứng
  9.5.0).
- Lệnh sửa của capcut-cli chỉ ghi file ở gốc. Muốn cập nhật `Timelines/` phải chạy thêm
  `sync-timelines --nested --apply`.
- Là Node.js nên phải cài thêm Node trên máy. Có giới hạn phụ đề CJK hữu ích
  (ja 13 ký tự/dòng, 4 ký tự/giây; ko 16/dòng, 12/giây) → sẽ chép vào `config/`.
- Công cụ `diagnose` rất tiện để kiểm tra draft do tool mình sinh ra.

## 4. Tài nguyên thư viện CapCut trong draft

Mọi tài nguyên từ thư viện đều tham chiếu bằng **id + đường dẫn tới cache** của CapCut
(`%LOCALAPPDATA%\CapCut\User Data\Cache\...`):

| Loại (trong mẫu) | Nằm ở | Khóa |
|---|---|---|
| Hiệu ứng "Lệch flash" | `materials.video_effects` + track `effect` | `effect_id` = `resource_id` = `7667810664672546068`, `path` → `Cache/effect/<id>/<md5>` |
| Filter "Hè thư thái" | `materials.effects` (type `filter`) + track `filter` | `effect_id` = `resource_id`, `path` → `Cache/effect/...` |
| Chuyển cảnh "Lấp lánh mùa đông" | `materials.transitions`, gắn vào clip qua `extra_material_refs` | `effect_id` = `resource_id`, `duration`, `is_overlap` |
| Nhạc "Abstraction" | `materials.audios` (type `music`) | `music_id`, `path` → `Cache/music/<md5>.mp3`. `draft_meta_info.json` còn lưu cả **URL tải** của bài |
| Sticker | Mẫu **không có sticker** | Theo pyCapCut: `resource_id` trong `materials.stickers` |
| Font chữ | Mẫu dùng font hệ thống `en.ttf` (theo thư mục cài CapCut 9.5.0.4050) | Font thư viện dùng `font_resource_id` |

`key_value.json` ghi thêm siêu dữ liệu cho mỗi tài nguyên: `is_vip`, danh mục, `material_copyright`.
Trong mẫu, **nhạc, hiệu ứng và chuyển cảnh đều có `is_vip: "1"` (tài nguyên Pro)**, chỉ filter là miễn phí.

**Cái gì sinh bằng code được:**
- Hiệu ứng, filter, chuyển cảnh, animation, font: **được**, miễn là biết `effect_id`/`resource_id`
  và file đã nằm trong cache của máy. Đường dẫn cache có dạng `Cache/effect/<id>/<md5>`. Phần
  `<md5>` không đoán được, nên tool sẽ **quét thư mục cache để tìm** (chỉ để ghi đường dẫn vào
  draft, không chép file ra ngoài). Chưa biết nếu cache chưa có thì CapCut có tự tải khi mở draft
  không `[CẦN KIỂM TRA TRÊN MÁY]`.
- Nhạc/âm thanh thư viện: **tự động một phần.** Cần `music_id` và bài đó đã có trong
  `Cache/music/` (tức là đã dùng thử trong CapCut ít nhất một lần). Tool **không tìm kiếm được
  thư viện online** (không có API công khai). → Phương án: **"bộ sưu tập"**. Anh/chị tạo
  một dự án chứa sẵn những nhạc/SFX/hiệu ứng hay dùng. Tool đọc dự án đó, lập danh mục (tên, id,
  đường dẫn cache, is_vip) để đạo diễn chọn. Đây cũng là phương án dự phòng đã ghi trong bản thiết kế.
- Nhãn **Commercial**: mẫu không có trường nào thể hiện rõ (`commercial_music_category_ids`
  rỗng, `material_copyright` rỗng). Cần thêm một bài nhạc có nhãn Commercial vào dự án bộ sưu tập để xem.

## 5. Phương án đề xuất cho bộ ghi draft (`app/capcut_writer`)

1. Tool **nhân bản một draft mẫu do CapCut 9.5.0 trên máy tạo ra** (giữ nguyên dấu phiên bản và
   toàn bộ trường), đổi `draft_name`, `draft_fold_path`, `draft_id`.
2. Xóa clip/chữ/nhạc cũ, rồi thêm mới bằng **bản sao các khối JSON lấy từ chính mẫu 9.5.0**
   (mỗi loại một "khuôn": video segment, text, audio, effect, filter, transition, kèm các vật liệu
   phụ), chỉ thay id, thời gian, đường dẫn, nội dung. Làm vậy thì không thiếu trường nào như pyCapCut.
3. Ghi vào **`Timelines/<main_timeline_id>/draft_content.json`** (file CapCut đọc), chép cùng nội
   dung sang 3 bản còn lại, xóa `attachment/patch/`. Ghi an toàn (file tạm rồi đổi tên), và từ chối
   ghi khi CapCut đang mở.
4. Dùng `capcut diagnose` (tùy chọn) để kiểm tra lại sau khi ghi.
5. Nếu CapCut 9.5.0 từ chối draft do tool ghi: phương án dự phòng là xuất mp4 bằng FFmpeg (mất
   khả năng chỉnh tay trong CapCut).

## 6. Việc cần làm tiếp trên máy thật

**Giai đoạn 0 hoàn tất** (chủ dự án xác nhận ngày 2026-09-25).

1. ~~CapCut đọc bản timeline nào~~ → xong: `Timelines/<id>/draft_content.json`.
2. ~~Tài khoản Pro~~ → có.
3. Khi bắt đầu Giai đoạn 1: thêm vào mẫu 1 sticker, 1 animation chữ, 1 keyframe vị trí, 1 clip
   16:9 đã thu nhỏ vào giữa khung, để có đủ "khuôn".
