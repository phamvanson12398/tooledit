# Báo cáo tương thích CapCut 9.5.0 — BẢN SƠ BỘ

> **Trạng thái: CHƯA XONG.** Repo chưa có dự án mẫu `samples/capcut_template/`, nên báo cáo này
> mới dựa trên **mã nguồn thật** của hai thư viện (đọc ngày 2026-09-25), chưa so với file của
> CapCut 9.5.0 trên máy chủ dự án. Các mục ghi `[CHỜ FILE MẪU]` sẽ điền khi có mẫu.
> Chưa code tính năng chính cho tới khi báo cáo này hoàn tất và chủ dự án xác nhận.

## 1. Draft có bị mã hóa không?

- Theo `capcut-cli` (`dist/decrypt.js`, `docs/version-support.md`): **chỉ JianYing (bản Trung Quốc)
  6.0+ mã hóa** `draft_content.json`. **CapCut quốc tế không mã hóa.**
- Cách kiểm tra: file bắt đầu bằng `{` và parse được JSON → không mã hóa. Script
  `tools/inspect_draft.py` làm đúng việc này cho mọi file timeline trong thư mục draft.
- Kết luận cho 9.5.0: `[CHỜ FILE MẪU]` (dự đoán: không mã hóa).

## 2. Thư viện nào dùng được với 9.5.0?

### pyCapCut (PyPI `pycapcut` 0.0.3)
- Tách ra từ pyJianYingDraft, đang "migrating" (beta).
- File mẫu đi kèm (`assets/draft_content_template.json`) ghi `app_version: 6.7.0`,
  `version: 360000`, `new_version: 140.0.0`. Tức là **draft sinh từ mẫu trống của thư viện mang
  dấu phiên bản cũ**.
- Có sẵn bảng effect_id/resource_id cho: hiệu ứng cảnh (~1583), hiệu ứng nhân vật (~254),
  filter (~454), font (~348), hiệu ứng âm thanh (~213), animation, chuyển cảnh, mask.
- Có "template mode": nạp một `draft_content.json` (không mã hóa) làm mẫu, thay media, sửa chữ,
  chép track — hợp với cách "dựng từ dự án mẫu của chủ dự án".
- Chỉ ghi `draft_content.json` ở gốc thư mục; **không biết tới `Timelines/<id>/draft_info.json`**.

### capcut-cli (npm `capcut-cli` 0.26.0, Node.js, MIT)
- Có bảng hỗ trợ phiên bản rất chi tiết. Điểm quan trọng cho 9.x:
  - **8.7 Windows**: draft sinh từ mẫu cũ (6.5.0) bị CapCut từ chối ("from an unusual path")
    vì dấu phiên bản cũ. Khi **dùng một dự án do chính CapCut trên máy tạo ra làm mẫu**, draft
    mở được, và đã có người dùng thử trên **9.3.0** (mở, sửa, lưu, mở lại).
  - **9.2.8+**: CapCut có thể đọc `Timelines/<main_timeline_id>/draft_info.json`; file ở gốc chỉ
    là bản sao cũ → ghi vào gốc có thể bị bỏ qua. `capcut sync-timelines --nested --apply` đồng bộ.
  - 9.3.0: `local_material_id` rỗng khiến clip không nhận file → phải điền.
  - **10.x bị chặn ghi** (CapCut mới từ chối draft do tool viết). → Việc chủ dự án khóa ở
    9.5.0 và tắt tự cập nhật là đúng.
  - Bộ bảo vệ: ghi vào draft CapCut > 9.x hoặc `version` > 360000 thì từ chối.
- Có lệnh `capcut version`, `capcut diagnose`, `capcut decrypt` (chỉ phát hiện), `capcut fixture`
  (xuất bản sao đã xóa thông tin cá nhân, không kèm media).
- Có sẵn giới hạn phụ đề CJK (`dist/script.js`): ja 13 ký tự/dòng, 4 ký tự/giây; ko 16/dòng,
  12/giây. Sẽ dùng làm giá trị mặc định trong `config/`.
- Bản 9.5.0 **không có trong bảng đã kiểm chứng** của capcut-cli (chỉ "9.x expected-compatible").

### Hướng đi dự kiến (cần xác nhận bằng file mẫu)
1. Luôn **dựng từ dự án mẫu do CapCut 9.5.0 trên máy tạo ra** (giữ đúng dấu phiên bản), không
   dựng từ mẫu trống của thư viện.
2. Ghi timeline vào **mọi file timeline CapCut thực sự đọc** (gốc + `Timelines/<id>/`), theo
   cách capcut-cli làm.
3. Có thể dùng pyCapCut để sinh các khối JSON (segment, keyframe, text) rồi tự ghi file, hoặc
   gọi capcut-cli cho phần đồng bộ/kiểm tra. Chọn cụ thể sau khi so với mẫu `[CHỜ FILE MẪU]`.

## 3. Tham chiếu hiệu ứng, chuyển cảnh, filter, sticker, âm thanh thư viện

| Loại | Cách tham chiếu (theo mã nguồn) | Sinh bằng code? |
|---|---|---|
| Hiệu ứng, filter, chuyển cảnh, animation, font | `effect_id` + `resource_id` (có bảng sẵn trong pyCapCut) | Có, nếu id có trong bảng. Id mới phải lấy từ dự án mẫu. CapCut có thể cần tải về khi mở `[CẦN KIỂM TRA TRÊN MÁY]` |
| Sticker | `resource_id` — lấy từ draft mẫu (pyCapCut có hàm liệt kê) | Có, sau khi đã lấy id từ mẫu |
| Âm thanh/nhạc thư viện CapCut | vật liệu `audios` có `music_id` + `path` trỏ vào cache của CapCut | `[CHỜ FILE MẪU]` — nghi là cần CapCut tải về máy trước (file phải có trong cache). **Không chép file đó ra ngoài CapCut.** |

## 4. Việc còn lại khi có file mẫu
- Chạy `tools/inspect_draft.py` và `capcut version / diagnose` trên mẫu, dán kết quả vào đây.
- So từng trường của mẫu với những gì pyCapCut sinh ra.
- Thử một draft sinh bằng code trên máy thật `[CẦN KIỂM TRA TRÊN MÁY]`.
- Kết luận câu hỏi mở: chèn nhạc thư viện online bằng code có tự động hoàn toàn được không.
