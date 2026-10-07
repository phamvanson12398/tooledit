# CLAUDE.md — Tool tự động dựng video TikTok trên CapCut

File này là bản thiết kế đã được chủ dự án chốt. Đọc toàn bộ trước khi làm bất cứ việc gì.

## 0. Quy tắc làm việc với chủ dự án

- **Luôn trả lời bằng tiếng Việt**, giải thích đơn giản. Chủ dự án không phải lập trình viên chuyên nghiệp.
- Code chạy trên **Windows** (máy của chủ dự án), nhưng bạn đang làm việc trong **cloud session Linux**, không có CapCut, không có GPU của chủ dự án. Vì vậy:
  - Mọi đường dẫn dùng `pathlib`, không hard-code dấu `/` hay `\`.
  - Sau mỗi thay đổi đáng kể, ghi hướng dẫn chạy thử trên Windows (lệnh PowerShell cụ thể, từng bước) vào `docs/TESTING_WINDOWS.md`, và nói rõ trong câu trả lời chủ dự án cần kiểm tra gì trên máy.
  - Việc gì chỉ kiểm chứng được trên máy thật (CapCut mở được dự án, GPU, xuất video) thì đánh dấu `[CẦN KIỂM TRA TRÊN MÁY]`.
- Commit nhỏ, mô tả rõ ràng. Viết test tự động cho mọi phần không phụ thuộc CapCut/GPU.
- **Không bao giờ commit video, âm thanh, footage của khách, hồ sơ khách thật hay file trong `jobs/`**. Giữ `.gitignore` chặt.
- Khi không chắc một API/thư viện hoạt động thế nào (pyCapCut, capcut-cli, Claude Code CLI, Freesound), đọc tài liệu hoặc mã nguồn thật, không đoán. Nếu có điểm mâu thuẫn với bản thiết kế này, dừng lại hỏi chủ dự án.

## 1. Bối cảnh sản phẩm

- Chủ dự án nhận **edit video thuê** từ footage của chính khách (khách xác nhận sở hữu). Video chỉ đăng **TikTok**.
- Ngôn ngữ video: **tiếng Hàn, tiếng Nhật, tiếng Anh**.
- Footage đầu vào là **footage thô**: chỉ có thoại hoặc âm thanh hiện trường. Ưu tiên file gốc; có thể tải từ link của chính khách bằng `yt-dlp`.
- Dựng **trong CapCut Desktop 9.5.0 bản quốc tế trên Windows** (đã tắt tự động cập nhật). Tool **ghi thẳng file dự án CapCut** (draft), KHÔNG điều khiển chuột/bàn phím.
- "Đạo diễn" AI lúc chạy tool là **Claude Code chạy local trên máy chủ dự án** (gói Claude Pro, không có API key của bất kỳ AI nào).
- Voice cho hook: chủ dự án **tự thu tay** bằng Voice Studio (OmniVoice) rồi thả file vào. Tool KHÔNG tích hợp TTS.

## 2. Nhiệm vụ đầu tiên (bắt buộc làm trước mọi thứ khác)

1. Đọc dự án mẫu trong `samples/capcut_template/` (chủ dự án tạo bằng CapCut 9.5.0, gồm vài clip test, chữ, một hiệu ứng, một chuyển cảnh, một âm thanh từ thư viện CapCut).
2. Xác định file dự án (`draft_content.json` và/hoặc `draft_info.json`) có bị mã hóa không. Có thể dùng `capcut-cli` (`capcut version`, `capcut decrypt` chỉ để phát hiện) hoặc tự kiểm tra xem có parse được JSON không.
3. Kiểm tra `pyCapCut` (PyPI: `pycapcut`) và `capcut-cli` có tương thích với cấu trúc của bản 9.5.0 không. So sánh các trường thực tế trong file mẫu với những gì thư viện sinh ra.
4. Tìm hiểu cách tham chiếu hiệu ứng, chuyển cảnh, filter, sticker, **âm thanh/nhạc từ thư viện online của CapCut** trong draft (effect_id / resource_id). Ghi rõ cái nào sinh bằng code được, cái nào cần CapCut tải về máy trước.
5. Viết báo cáo ngắn bằng tiếng Việt vào `docs/CAPCUT_COMPAT.md` và tóm tắt cho chủ dự án. **Chưa code tính năng chính trước khi báo cáo này xong.**

Nếu draft bị mã hóa hoặc không thư viện nào tương thích: dừng lại, báo chủ dự án, đề xuất phương án (ví dụ dùng bản CapCut tương thích, hoặc xuất mp4 bằng FFmpeg).

## 3. Quy trình một job

Mỗi lần xử lý footage là một **job**, lưu trong `jobs/<job_id>/`. Job là một state machine lưu trạng thái ra đĩa (`job.json`) để có thể dừng chờ người dùng rồi chạy tiếp, kể cả sau khi tắt máy.

1. **Nhận việc**: footage + chọn khách + các tùy chọn (mục 9).
2. **Phân tích** (`analysis/`):
   - Làm sạch âm thanh: lọc ồn nhẹ, chuẩn hóa âm lượng (mục tiêu khoảng -14 LUFS, cấu hình được). Dùng FFmpeg (`afftdn`, `loudnorm`).
   - Nhận dạng thoại: `faster-whisper`, model `large-v3`, timestamp theo từ, tự nhận ngôn ngữ (ko/ja/en). Có fallback CPU và model nhỏ hơn, cấu hình được (chưa biết máy có GPU NVIDIA không).
   - Dò cảnh (PySceneDetect), trích khung hình rải đều + khung đầu mỗi cảnh, lưu JPEG nhỏ.
   - Dò chủ thể/khuôn mặt cho crop thông minh (MediaPipe hoặc OpenCV).
3. **AI hiểu nội dung**: đạo diễn đọc transcript + khung hình, xác định thể loại, không khí, số người, chủ thể chính. Trả về tóm tắt một dòng (tiếng Việt) + phong cách đề xuất. Nếu bật "Xác nhận trước khi dựng", job dừng chờ người dùng duyệt/sửa.
4. **Chia video** (nếu tick, mục 4) → bảng duyệt, job dừng chờ duyệt.
5. **Hook** (nếu tick, mục 5) → bảng chọn hook, job dừng chờ chọn và chờ file voice.
6. **Kế hoạch dựng** (edit plan) cho từng video: JSON theo schema (mục 10).
7. **Tìm tài nguyên** theo thứ tự ưu tiên (mục 7).
8. **Ghi dự án CapCut**: mỗi video một draft riêng trong thư mục draft của CapCut (`%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\` — xác minh lại đường dẫn trên máy thật, cho cấu hình được). Tên draft: `<khach>_<job_id>_video01`...
9. **Duyệt và xuất**: người dùng mở CapCut xem, chỉnh tay, xuất. Xuất hàng loạt tự động là giai đoạn 3.
10. **Giao hàng**: xuất `captions.txt` cho từng video: caption + hashtag bằng ngôn ngữ của video, kèm bản dịch tiếng Việt.
11. **Sửa theo yêu cầu khách**: người dùng mô tả thay đổi bằng lời, đạo diễn sửa đúng phần liên quan trong edit plan, tool cập nhật lại draft. Không dựng lại từ đầu.

## 4. Chia video dài (tick "Chia video")

- Mỗi video đầu ra là **một video độc lập**: trọn vẹn có mở, diễn biến, kết. Người xem không cần biết video khác.
- **Không có dấu vết series**: không nhãn "Part 1/2/3", không câu "xem phần tiếp theo", phần kết khép lại gọn.
- **AI toàn quyền chọn đoạn**: đoạn hay thì thành video, đoạn nhạt thì bỏ. Không giới hạn số lượng video.
- **Thời lượng mỗi video: tối thiểu 60 giây, tối đa 150 giây (2:30), tính cả hook.**
  - Đoạn hay nhưng < 60s: thử ghép với đoạn liền kề cùng chủ đề nếu tự nhiên; không được thì bỏ và ghi lý do.
  - Đoạn > 150s: cắt gọn nhịp (bỏ khoảng lặng, câu thừa, tăng tốc đoạn nhàm); vẫn dài thì tách thành hai video độc lập.
  - **Ngoại lệ**: nếu toàn bộ footage sau khi cắt gọn vẫn < 60s thì vẫn xuất bình thường, chỉ đánh dấu "ngắn hơn 1 phút" trong bảng duyệt. Không kéo dài nhân tạo.
- **Bảng duyệt** hiển thị: từng video (giây bắt đầu–kết thúc, thời lượng, tóm tắt nội dung) và **cả các đoạn bị bỏ kèm lý do**. Người dùng có thể chỉnh điểm cắt hoặc tick một đoạn bị bỏ để dựng thêm.
- Caption viết riêng từng video; hashtag có thể dùng chung vài cái.
- Không tick "Chia video": cả footage thành một video (vẫn áp dụng giới hạn tối đa 150s bằng cách cắt gọn; nếu không thể thì báo người dùng và đề nghị bật chia video).

## 5. Hook (tick "Có hook")

- Mỗi video (kể cả khi chia nhiều video) có **hook voice riêng**.
- Với mỗi video, đạo diễn đưa **3 phương án hook**, mỗi phương án gồm: câu hook bằng **ngôn ngữ của video** (văn nói tự nhiên của người bản xứ, không dịch từ tiếng Việt), bản dịch tiếng Việt, đoạn footage chạy bên dưới (giây bắt đầu–kết thúc trong footage gốc), kiểu nhạc/hiệu ứng đi kèm, và kiểu hook.
- Các kiểu hook: tua thẳng đến cao trào, câu hỏi bỏ lửng, tương phản, hé lộ một nửa, con số/chi tiết lạ.
- Hook nằm trong khoảng 3–5 giây đầu: câu ngắn, hình chuyển động nhanh, chữ lớn nhấn từ khóa ở dải trên, cắt ngay trước khi lộ "lời giải".
- **Cập nhật (chủ dự án chốt 01/10): hook dài hơn** — trước câu hook có **1–2 câu đời thường** (`intro`, gần gũi như kể
  chuyện với bạn bè) chạy trên cảnh bối cảnh (`intro_footage`), rồi mới tới câu hook trên cảnh mạnh. Thu chung một file
  voice; tổng hook khoảng 6–12 giây (`hook.max_s` trong styles).
- Khi chia video, hook mỗi video phải **tự cung cấp bối cảnh**, như thể đây là video duy nhất.
- **Nguyên tắc cứng: hook phải đúng với nội dung có thật trong footage.** Không hứa điều video không có. Mỗi phương án phải ghi nguồn (mốc giây). Code phải kiểm tra mốc giây được tham chiếu nằm trong footage.
- Tất cả phương án của mọi video gom vào **một bảng**. Người dùng chọn xong, tool xuất file `hook_scripts.txt` (câu cần thu + tên file tương ứng) để thu voice một lượt.
- Tên file voice: `jobs/<job_id>/voice/video01_hook.wav`, `video02_hook.wav`... (chấp nhận cả .mp3/.m4a). Tool quét thư mục, báo file nào còn thiếu, đủ thì dựng tiếp.
- Hồ sơ khách lưu kiểu hook khách ưa thích; tool ghi lại lựa chọn của người dùng để lần sau đề xuất sát hơn.
- Không tick: vào thẳng nội dung, không hook voice.

## 5b. Chế độ "Đổi ngôn ngữ" (chủ dự án chốt 01/10)

- Video gốc nói tiếng Hàn / Nhật / Anh / **Trung**; bản TikTok là tiếng Hàn / Nhật / Anh khác tiếng gốc.
- Ngôn ngữ mới thể hiện bằng **cả hai**: voice thuyết minh (chủ dự án tự thu từng câu bằng Voice Studio, file
  `voice/videoNN_dubMM.wav`) + phụ đề, tiêu đề, chữ nhấn, hook, caption bằng ngôn ngữ đích. **Cập nhật 02/10: tiếng gốc
  TẮT HẲN** (`mute_original` trong `config/dub.yaml`; false = chỉ hạ nhỏ dưới voice).
- "Khác bản gốc ~80%": đổi khung/cắt cận bám người, zoom + chuyển động mọi clip, filter, nhạc + hook + tiêu đề mới;
  **không đảo thứ tự cảnh**. Cấu hình trong `config/dub.yaml`.
  Cập nhật 01/10: **phản chiếu ngang** ~40% số cảnh (theo cảnh, cùng cảnh cùng chiều; tự tắt khi hình có chữ/logo —
  `mirror_ok` / `burned_in_text`), cấu hình `style_override.mirror` trong `config/dub.yaml`.
- **Bản địa hóa (chủ dự án chốt 01/10):** kịch bản (thuyết minh, lời dẫn, hook, tiêu đề, caption) viết THEO NƯỚC của khán
  giả đích — giọng, cách hài, tên riêng, đơn vị, tiền tệ, giải thích chi tiết văn hóa lạ, điều nên tránh
  (`config/localize.yaml`); câu được bản địa hóa ghi `adapt_vi`. Giữ đúng sự việc, không bịa.
- **Voice khớp hình cho video nói liên tục (chủ dự án yêu cầu 03/10, vd hướng dẫn trang điểm):** câu thuyết minh bám
  đúng đoạn thoại gốc của từng động tác, viết gọn hơn gốc 10–20%; mỗi câu được dùng chỗ trống tới lúc câu sau bắt đầu
  rồi mới tăng tốc (tối đa `max_speed`); có thể thu CẢ BÀI một file (nghỉ ~1 giây giữa các câu), tool tự cắt ra từng câu
  theo chỗ trống (`app/planner/voice_split.py`); giao diện báo từng câu 🟢 khớp / 🟡 tự tăng tốc / ⚪ ngắn / 🔴 thu lại.
- **Chống đè tiếng khi video gốc nói nhiều (chủ dự án yêu cầu 05/10):** voice không bao giờ chồng nhau — câu sau chờ
  câu trước nói xong (trễ ≤ `max_delay_s`, bắt kịp ở chỗ lặng), tăng tốc tới `hard_max_speed` (`place_voices`); video
  nói dày đặc thì AI nén ý còn ~75% (`dense_ratio`/`dense_keep`), viết nhắm 85% tốc độ tối đa; tool đo tốc độ đọc thật
  của giọng đã thu (lưu `config/local.yaml → voice_cps`) để lần sau viết vừa giọng; nút "✂️ Viết gọn các câu 🔴" cho
  AI viết lại ngắn hơn đúng các câu voice bị tràn (prompt `dub_shorten.md`), thu lại riêng các câu đó.
- **Chế độ "Chỉ thay tiếng" (chủ dự án chốt 06/10, video short):** ô tick ở trang chủ (cần chọn ngôn ngữ đích). Hình giữ
  NGUYÊN: không cắt (trừ đoạn vi phạm chính sách), không đổi thứ tự / khung / zoom / lật / tốc độ; khung = đúng tỉ lệ
  video gốc (`nearest_ratio`; dọc 9:16 thì chữ đè lên hình theo `overlay` trong `config/layout.yaml`). Chỉ thêm: voice
  thuyết minh + phụ đề + tiêu đề ngôn ngữ đích, nhạc nền nhẹ (-12 dB), hiệu ứng / sticker / SFX; không hook, không chia
  video, không filter, không chữ nhấn (`voice_only` trong `config/dub.yaml`).
- **Kịch bản thuyết minh còn lỗi nhỏ (chủ dự án yêu cầu 03/10):** code tự sửa (thu câu vắt 2 clip, gộp câu quá ngắn,
  tính tốc độ nói theo chỗ trống tới câu sau + `max_speed`); AI vẫn sai 3 lần thì trang lỗi có nút "Dùng bản này, bỏ
  qua lỗi còn lại" (bản lưu ở `plan/pending_dub_videoNN.json`), hoặc `accept_imperfect: true` để tự dùng.
- **Phụ đề tiếng Việt để kiểm tra (chủ dự án yêu cầu 03/10):** chữ vàng nhỏ ngay dưới phụ đề chính = `text_vi` của
  câu thuyết minh, cùng thời điểm; bật/tắt từng job ở trang job (`vi_subtitles` trong `config/dub.yaml`); tắt rồi
  dựng lại trước khi xuất video đăng TikTok.
- Chỗ **không có giọng nói**: AI viết thêm **lời dẫn** (`kind: narration`) để lồng voice, nhưng **chỉ ở cảnh hay /
  hành động đáng chú ý** (vd nấu ăn: lúc thêm gia vị), không nói liên tục (tối đa ~60% thời gian lặng); mỗi câu ghi
  `action_vi`, tả đúng cảnh đang thấy (có gửi khung hình), không bịa; chỗ tiếng cười/hò reo giữ nguyên.
- Video **mở đầu im lặng** (vd chỉ show món ăn / sản phẩm): BẮT BUỘC có lời dẫn mở đầu ngay từ cảnh đầu, giọng như
  video nấu ăn — gần gũi, gợi thèm, gợi tò mò cách làm (`narration.opening` trong `config/dub.yaml`).

## 6. Khung hình

- Canvas mặc định **9:16, 1080×1920**.
- Footage dọc: tràn viền.
- Footage ngang 16:9: đặt thành **khối 4:3 (1080×810) hoặc 1:1 (1080×1080)** giữa màn hình.
  - Crop thông minh bám theo chủ thể (mặt người nói, vật đang được nhắc tới), lia khung mượt bằng keyframe vị trí của CapCut khi chủ thể di chuyển.
  - Tick **"Đổi khung theo cảnh"**: AI chọn 4:3 hoặc 1:1 cho từng cảnh (cảnh rộng/nhiều người → 4:3; cận mặt/cận vật → 1:1), chuyển mượt. Không tick: giữ khung mặc định của hồ sơ khách suốt video.
  - Phần trống: dải trên cho tiêu đề/câu hook cố định, dải dưới cho phụ đề.
  - Nền phần trống (theo hồ sơ khách): bản mờ của chính video, màu trơn, hoặc ảnh nền của khách.
- **Cập nhật (chủ dự án chốt 25/09, theo video mẫu):** bố cục mặc định cho MỌI video là "4 dòng tiêu đề": nền đen,
  khối video 16:9 tràn ngang ở giữa, 2 dòng tiêu đề chữ rất lớn phía trên + 2 dòng phía dưới cố định suốt video,
  phụ đề thoại trong khối video, nhãn chủ đề nhỏ góc trên phải khối. Thông số trong `config/layout.yaml`
  (`preset: classic` để dùng lại bố cục 4:3/1:1 ở trên).
  **Cập nhật 01/10:** khung người dùng chọn khi tạo job (4:3 / 1:1 / 16:9) được áp dụng cho khối video của mọi bố cục;
  tiêu đề, phụ đề, nhãn tự dời theo khối (`app/styles.adapt_layout`). "Theo kiểu dựng" = khung mặc định của bố cục.
  ~~Cập nhật 02/10: khung cố định 3:4~~ — **chủ dự án BỎ ngày 02/10**: khung video trở lại theo lựa chọn 4:3 / 1:1 /
  16:9 khi tạo job như cập nhật 01/10 (`frame_ratio` / `frame_lock` không còn đặt trong `config/layout.yaml`).
- **Ngoại lệ thể thao (chủ dự án chốt 25/09, video mẫu boxing):** kiểu `sports_analysis` dùng bố cục `sports_focus`:
  nền đen, khối video 9:10 phóng vào pha đấu bám theo người, không dòng tiêu đề, phụ đề cụm ngắn chữ vàng viền đen
  trong khối video, mũi tên xanh chỉ chi tiết mà lời bình nhắc tới, chuyển cảnh mờ, replay quay chậm.
- **Chữ in sẵn trên footage (chủ dự án yêu cầu 02/10, rồi BỎ cùng ngày — `enabled: false` trong
  `config/text_cover.yaml`, mã giữ lại để bật lại khi cần):** khi AI báo có chữ in sẵn, máy dò vùng chữ trên khung hình
  (`app/analysis/textdetect.py`); khung cắt được cắt chặt hơn để đẩy chữ ra ngoài (mất ≤ 20%), không được thì che bằng
  dải nền tối (`config/text_cover.yaml`). Cập nhật 02/10: hạn chế che (ưu tiên cắt tránh, chỉ che đúng lúc chữ hiện),
  dải che nửa trong suốt, bo tròn, vừa khít chữ; gần hàng phụ đề thì gộp thành thanh phụ đề.
- **Vùng an toàn TikTok**: chữ tránh dải dưới cùng (caption, tên tài khoản), cạnh phải (cột nút), và dải trên cùng. Để các lề này là hằng số cấu hình được trong `config/`, giá trị mặc định ước lượng, ghi chú cần kiểm tra lại trên app thật.

## 7. Tài nguyên và bản quyền

Thứ tự tìm một tài nguyên (hiệu ứng, sticker, emoji, âm thanh, nhạc):

1. **Danh mục CapCut** (hiệu ứng, chuyển cảnh, filter, animation chữ, sticker, âm thanh, nhạc).
2. **Kho local** `assets/` trên máy chủ dự án.
3. **Tải từ internet** (chỉ khi bật "Tự tải tài nguyên thiếu"), **chỉ nguồn có giấy phép rõ ràng**:
   - Emoji: **đóng gói sẵn** bộ Noto Emoji (Apache 2.0) trong tool, gần như không cần tải.
   - Âm thanh: Freesound API (key miễn phí, người dùng tự nhập trong cài đặt), **chỉ lấy file CC0**.
   - Không cào web. Không dùng nguồn không rõ giấy phép.
4. Không tìm được → ghi vào **danh sách cần bổ sung** (`missing_assets.json` + hiển thị trên giao diện): cần gì, dùng ở video nào, giây thứ mấy, để làm gì. Người dùng thả file vào thư mục chỉ định, bấm "Tiếp tục", tool gắn đúng chỗ.

Quy tắc:
- **Không trích xuất file âm thanh/nhạc/hiệu ứng từ cache của CapCut ra dùng ngoài CapCut.** Tài nguyên CapCut chỉ được tham chiếu bên trong draft.
- Với khách là doanh nghiệp (cờ trong hồ sơ khách), ưu tiên nhạc có nhãn **Commercial** của CapCut.
- **Sổ nguồn** `assets/ledger.json`: mọi file tải về/thêm vào kho đều lưu nguồn, URL, giấy phép, ngày tải.
- Kho local tự quét và gắn nhãn (loại âm thanh, tâm trạng, tốc độ, độ dài) để đạo diễn chọn được.

## 8. Phong cách dựng

Preset trong `styles/*.yaml`. Sáu phong cách:

1. `kr_variety` — show giải trí Hàn (예능): chữ to nhiều màu có viền, bình luận chêm, emoji, SFX vui, zoom giật khi phản ứng.
2. `jp_telop` — テロップ Nhật: chữ nhấn lớn giữa màn, màu theo cảm xúc, nhịp vừa, SFX "pop" khi hiện chữ.
3. `tiktok_retention` — cắt rất nhanh, bỏ mọi khoảng lặng, phụ đề nhảy từng từ, zoom liên tục.
4. `storytelling` — nhịp chậm, chuyển cảnh mờ, nhạc điện ảnh, phụ đề gọn.
5. `healing` — ít cắt, giữ âm thanh hiện trường, nhạc lofi/acoustic nhỏ, chữ ít.
6. `professional` — sạch, cắt vấp, tiêu đề từng phần, ý chính hiện bên cạnh.

**Thêm (chủ dự án yêu cầu 03/10):** `makeup` — trang điểm / làm đẹp: mở bằng look hoàn thiện (cold open) → mặt mộc →
từng bước đúng thứ tự (tua nhanh đoạn tán, chậm ở chi tiết đắt, mũi tên hồng chỉ vùng đang trang điểm) → khoe kết quả
quay chậm có nhãn 完成 / 완성 / FINAL LOOK + so trước–sau. Không hứa hẹn quá sự thật, không đoán tên sản phẩm.

Nguyên liệu đạo diễn tự phối (liều lượng do preset quy định, không dùng hết mọi thứ cho mọi video):
- Cắt và nhịp: bỏ khoảng lặng, câu vấp, đoạn thừa; tăng tốc đoạn nhàm.
- Chuyển động hình: zoom giật, zoom chậm, lắc, dừng hình, quay chậm.
- Chữ: phụ đề thoại, chữ nhấn, bình luận chêm, emoji, tiêu đề dải trên.
- Âm thanh: nhạc nền theo tâm trạng từng đoạn, tự hạ nhạc khi có thoại (ducking), SFX ở điểm nhấn.
- Chuyển cảnh, filter, tông màu đồng bộ.

**Phụ đề CJK**: tiếng Nhật không có dấu cách → ngắt dòng theo số ký tự và cụm nghĩa; tiếng Hàn và Nhật có giới hạn ký tự/dòng và ký tự/giây riêng (tham khảo giá trị trong capcut-cli, cấu hình được). Font phải hỗ trợ Hangul/Kana/Kanji (ví dụ Noto Sans KR/JP).

## 9. Giao diện

Web app chạy local (FastAPI + trang HTML đơn giản, không cần build frontend), mở trên trình duyệt. Chủ dự án không phải gõ lệnh khi dùng hằng ngày; có file `start.bat` để khởi động.

Tùy chọn cho mỗi job:
- Chọn khách (hoặc "khách mới, AI tự chọn phong cách")
- ☐ Có hook
- ☐ Chia video dài
- ☐ Đổi khung theo cảnh
- ☐ Tự tải tài nguyên thiếu
- ☐ Xác nhận trước khi dựng

Các màn hình dừng chờ: xác nhận thể loại, bảng duyệt chia video, bảng chọn hook, chờ file voice, danh sách tài nguyên cần bổ sung. Hiển thị tiến trình và lỗi bằng tiếng Việt dễ hiểu.

## 10. Dữ liệu và schema

- `clients/<client_id>.yaml` — hồ sơ khách: phong cách, ngôn ngữ, font, màu chữ, logo, khung mặc định (4:3/1:1), kiểu nền, cờ đổi khung theo cảnh, kiểu hook ưa thích, mức độ hiệu ứng, cờ doanh nghiệp. **Commit `clients/example.yaml` thôi**; hồ sơ thật bị gitignore. Hồ sơ lần đầu có thể tạo bằng cách cho đạo diễn phân tích video mẫu khách thích.
- `jobs/<job_id>/job.json` — trạng thái job.
- `jobs/<job_id>/analysis/` — transcript.json, scenes.json, frames/, subjects.json.
- `jobs/<job_id>/plan/segments.json` — kết quả chia video + đoạn bị bỏ.
- `jobs/<job_id>/plan/hooks.json` — phương án hook và lựa chọn.
- `jobs/<job_id>/plan/edit_plan_videoNN.json` — kế hoạch dựng.
- Mọi output của đạo diễn là JSON, **validate bằng pydantic**; sai schema thì gọi lại kèm thông báo lỗi (giới hạn số lần thử).

Edit plan tối thiểu phải mô tả: danh sách clip (nguồn, in/out, tốc độ), khung/crop + keyframe, các lớp chữ (nội dung, thời gian, kiểu, vị trí), hiệu ứng hình (loại, thời gian, tham số), chuyển cảnh, nhạc nền (theo đoạn, mức ducking), SFX (thời điểm), hook (file voice, footage, chữ), tham chiếu tài nguyên (nguồn: capcut/local/downloaded + id/đường dẫn).

## 11. Gọi đạo diễn (Claude Code local)

- Tool gọi Claude Code ở chế độ không tương tác (headless) trên máy chủ dự án, đăng nhập bằng gói Pro. **Kiểm tra cờ lệnh thực tế** (`claude --help`, tài liệu chính thức) trước khi viết code; không đoán tên cờ.
- Prompt đặt trong `prompts/` dạng template, tách riêng từng việc: hiểu nội dung, chia video, hook, edit plan, sửa theo yêu cầu, caption/hashtag, tạo hồ sơ khách.
- Chỉ gửi văn bản (transcript, dữ liệu phân tích) và khung hình JPEG nhỏ; **không gửi video**. Giữ prompt gọn để tiết kiệm hạn mức Pro (khung 5 tiếng, dùng chung với chat).
- Thiết kế lớp `Director` dạng interface để sau này có thể thay backend (ví dụ chế độ copy–paste thủ công hoặc mô hình local) mà không sửa phần còn lại.
- Để test trong cloud: tạo `FakeDirector` trả JSON mẫu cố định.

### 11.1. Vai trò của đạo diễn: editor chuyên nghiệp

Mọi prompt gửi cho đạo diễn đều mở đầu bằng một phần vai trò chung, lưu tại `prompts/_editor_persona.md` và được tự động ghép vào đầu mọi template. Nội dung phần vai trò phải thể hiện:

- **Danh tính**: một editor video ngắn chuyên nghiệp nhiều năm kinh nghiệm, chuyên dựng TikTok cho thị trường Hàn, Nhật và các nước nói tiếng Anh; hiểu văn hóa xem video của từng thị trường (자막 kiểu 예능 của Hàn, テロップ của Nhật, nhịp nhanh của TikTok tiếng Anh).
- **Tư duy nghề**: mục tiêu số một là giữ chân người xem và kể câu chuyện rõ ràng; mỗi quyết định dựng phải phục vụ nội dung. Biết tiết chế: hiệu ứng, zoom, SFX dùng đúng lúc mới có sức nặng, lạm dụng làm video rẻ tiền. Tôn trọng chất liệu gốc và giọng của khách.
- **Kỹ năng**: cảm nhịp (pacing), chọn khoảnh khắc đắt giá, dựng hook, cắt theo cảm xúc và theo nhịp nhạc, bố cục khung dọc, phụ đề dễ đọc, phối âm thanh (thoại luôn rõ, nhạc và SFX làm nền).
- **Chuẩn mực**: hook và mọi chữ trên màn hình phải đúng với nội dung có thật trong footage; không bịa lời thoại, không gán cảm xúc sai; tuân thủ ràng buộc của hệ thống (thời lượng 60–150s, vùng an toàn, phong cách của hồ sơ khách).
- **Tuân thủ chính sách TikTok (chủ dự án chốt 27/09):** nội dung vi phạm Nguyên tắc cộng đồng TikTok (bạo lực thật,
  hành vi nguy hiểm, tự hại, gợi dục, an toàn trẻ em, thù ghét/quấy rối, chửi thề, ma túy/rượu/cờ bạc/vũ khí, tin sai
  gây hại, lộ thông tin cá nhân) bị CẮT BỎ: đạo diễn đánh dấu `policy_issues`, máy tự dò thêm từ tục trong transcript
  (`config/policy.yaml`), code tự cắt clip chạm vào các đoạn đó, hook/chữ trên màn hình/caption không được dùng.
  Cập nhật 28/09: caption, hashtag, chữ trên màn hình, hook và lời thoại **không được nhắc nền tảng khác ngoài TikTok**
  (YouTube, Instagram, "subscribe/구독/チャンネル登録"...) — lời thoại thì cắt, chữ thì đạo diễn phải viết lại.
  Cập nhật 07/10: người dùng có thể tick **"Giữ lại"** từng đoạn AI đánh dấu (bảng 🚫 trên trang job, lưu
  `job.data.policy_keep`) — đoạn đó không bị cắt nữa, tool lập lại kế hoạch dựng; người dùng tự chịu trách nhiệm.
- **Tự duyệt trước khi trả kết quả**: như một editor duyệt lại bản dựng của mình, đạo diễn phải tự kiểm tra trước khi trả JSON: mỗi hiệu ứng có lý do không, có chỗ nào quá dày hoặc quá nhạt không, video có trọn vẹn và đứng được một mình không, hook có đúng nội dung không, thời lượng có trong giới hạn không. Trong output có trường `editor_notes` (tiếng Việt, ngắn) giải thích các quyết định chính để người dùng hiểu vì sao dựng như vậy; trường này hiển thị trên giao diện ở các bước duyệt.

Phần vai trò chỉ viết một lần, dùng chung; các template riêng từng việc chỉ mô tả nhiệm vụ cụ thể.

## 12. Công nghệ

Python 3.11+, FFmpeg, faster-whisper (large-v3), PySceneDetect, MediaPipe/OpenCV, pydantic, FastAPI, pyCapCut và/hoặc capcut-cli (Node.js), yt-dlp, Noto Emoji, Freesound API. Quản lý phụ thuộc bằng `requirements.txt`; viết `install.bat` / hướng dẫn cài đặt từng bước cho Windows trong `docs/SETUP_WINDOWS.md`.

## 13. Cấu trúc thư mục đề xuất

```
app/            # mã nguồn chính (analysis, director, planner, assets, capcut_writer, web)
prompts/        # template prompt cho đạo diễn
styles/         # 6 preset phong cách
clients/        # hồ sơ khách (chỉ commit example.yaml)
assets/         # kho local + ledger.json (media bị gitignore, chỉ commit ledger mẫu)
config/         # cấu hình: đường dẫn CapCut, vùng an toàn, giới hạn phụ đề, model Whisper
samples/        # dự án CapCut mẫu (không chứa footage khách)
tests/          # test + fixtures
docs/           # CAPCUT_COMPAT.md, SETUP_WINDOWS.md, TESTING_WINDOWS.md
jobs/           # dữ liệu job (gitignore)
```

`.gitignore` phải chặn: `jobs/`, `clients/*` (trừ `example.yaml`), media trong `assets/` (`*.mp4 *.mov *.wav *.mp3 *.m4a ...`), `.env`, cache model.

## 14. Lộ trình

**Giai đoạn 0** — Nhiệm vụ mục 2 (tương thích CapCut 9.5.0). Xong khi có `docs/CAPCUT_COMPAT.md` và chủ dự án xác nhận.

**Giai đoạn 1** — Bản chạy được với **một phong cách** (`tiktok_retention`), chưa chia video:
phân tích → đạo diễn → phụ đề (ko/ja/en) → zoom, SFX, nhạc, ducking → hook (3 phương án, chờ voice) → khung 9:16 + bố cục 4:3/1:1 với crop thông minh → ghi draft CapCut → caption/hashtag → giao diện cơ bản.
Xong khi: trên máy Windows, một footage thật tạo ra draft mở được trong CapCut 9.5.0, dựng đúng kế hoạch, xuất được video.

**Giai đoạn 2** — Chia video dài thành video độc lập (mục 4), đủ 6 phong cách, hồ sơ khách đầy đủ + tạo hồ sơ từ video mẫu, tìm tài nguyên đủ 4 bước, sửa theo yêu cầu khách, giao diện hoàn chỉnh.

**Giai đoạn 3** — Xuất hàng loạt qua đêm và tối ưu dựa trên kinh nghiệm chạy thực tế.

## 15. Những điểm còn mở

- Máy có GPU NVIDIA hay không (ảnh hưởng tốc độ Whisper) → hỏi chủ dự án khi cần.
- Chèn nhạc/âm thanh từ thư viện online CapCut bằng code có tự động hoàn toàn được không → kết luận trong `docs/CAPCUT_COMPAT.md`. Phương án dự phòng: dự án mẫu chứa sẵn bộ âm thanh hay dùng.
- Lề vùng an toàn TikTok → kiểm tra trên app thật.
