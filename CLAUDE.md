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
  **Cập nhật 11/10 (chủ dự án chốt):** thêm **Gemini Pro** làm AI đạo diễn thứ hai, **chọn cho từng job** (ô "🤖 AI đạo
  diễn", `JobOptions.ai`, đổi được ở trang job) — chạy qua **Antigravity CLI** (`agy`) vì từ 18/06/2026 Google ngừng cho
  tài khoản AI Pro đăng nhập Gemini CLI; đăng nhập tài khoản Google gói Google AI Pro, vẫn KHÔNG dùng API key
  (`app/director/antigravity_cli.py`, `install_antigravity.bat`, `config/director.yaml → agy_*`).
- Voice cho hook: chủ dự án **tự thu tay** bằng Voice Studio (OmniVoice) rồi thả file vào. Tool KHÔNG tích hợp TTS.
  **Cập nhật 11/10 (chủ dự án yêu cầu):** TÙY CHỌN cho OmniVoice đọc thoại thuyết minh / lồng tiếng (mục 5d) — thu tay vẫn là
  mặc định; clone giọng chỉ khi chủ dự án tick xác nhận có quyền dùng giọng đó.

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
   - **Cập nhật 11/10 (chủ dự án: "phân tích footage lâu"):** nhận dạng thoại (GPU) chạy SONG SONG với dò cảnh + trích
     khung + dò mặt (CPU) và 2 bản làm sạch âm thanh; khung hình trích nhiều cái một lúc (`parallel.frame_workers` trong
     `config/analysis.yaml`); Whisper trên GPU chạy theo lô (`BatchedInferencePipeline`, `batched` / `batch_size` trong
     `config/whisper.yaml`, `without_timestamps: false` để vẫn chia câu; lỗi thì tự chạy lại cách thường); nhật ký ghi
     thời gian từng phần (`app/analysis/pipeline.py`).
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
- **Cách viết lời thuyết minh (chủ dự án yêu cầu 07/10), chọn khi tạo job:** mặc định **"AI xem video rồi VIẾT MỚI"**
  (`script_mode: rewrite`, prompt `dub_rewrite.md`) — AI xem ~16 khung hình + lời gốc chỉ để hiểu sự việc, tự viết kịch
  bản mới như creator bản xứ của nước đích (mở lời cuốn ngay giây đầu, không nói kín quá 90%), vẫn đúng sự thật, không
  bịa; hoặc **"Dịch sát"** (`translate`, cách cũ). Mặc định ở `config/dub.yaml → default_script_mode`.
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
  Cập nhật 07/10: ô **"Giữ nhạc nền gốc"** (`keep_bgm`) — tách giọng nói khỏi âm thanh gốc bằng Demucs (MIT, chạy trên
  máy, `requirements-bgm.txt`, `app/analysis/separate.py`), giữ nhạc + tiếng nền (hạ nhỏ dưới voice), không thêm nhạc
  AI; chưa cài Demucs thì dùng nhạc AI như thường và ghi lý do vào nhật ký.
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

## 5d. Chế độ "Lồng tiếng nhân vật" (chủ dự án yêu cầu 11/10)

- Ô tick "🎭 Lồng tiếng nhân vật" (`JobOptions.char_dub`, `config/char_dub.yaml`), một video, cần chọn ngôn ngữ đích
  (vd phim tiếng Nhật → Hàn). Không hook riêng, không review, không ⚡.
- AI chọn các ĐOẠN HAY hợp người xem TikTok (vào chuyện ngay, hài / gay cấn / cảm động, bỏ đoạn rề rà — luôn qua bảng
  duyệt; `HIGHLIGHT_SEGMENT_NOTE`), mỗi đoạn một video 60–120s; **cập nhật 11/10: chọn theo TÌNH HUỐNG ngắn 10–20 giây** (một màn cãi nhau,
  một cú hài, một pha bất ngờ — `situation_s` trong `config/char_dub.yaml`), ghép vài tình huống thành một video
  (`SegmentVideo.moments`, `check_moments`), không lấy một khúc dài liền; clip của kế hoạch dựng = đúng các tình huống đã
  duyệt (`situation_clips`); kế hoạch dựng chỉ cắt bỏ chỗ rề rà, giữ thứ tự, tốc độ
  1.0, không cắt giữa câu thoại, không "khác bản gốc" (không lật / filter mạnh) — `CHAR_DUB_RULE`.
- AI dịch từng câu thoại (khớp thời điểm câu gốc để khớp miệng) và ghi `speaker` = tên nhân vật từng câu (nhận ra qua
  lời thoại + khung hình gần câu đó; `make_char_dub`, prompt `dub_char.md`); không có lời dẫn.
  **Cập nhật 11/10 (chủ dự án: "không khớp", "nhân vật đang nói mà không có tiếng", "không cần edit nhiều"):** mốc giờ câu
  lồng tiếng do CODE lấy từ câu gốc Whisper (`app/planner/char_lines.source_lines`, câu > `max_line_s` tách ở chỗ ngắt),
  AI phải trả ĐÚNG mỗi câu gốc một câu dịch (`check_char_dub`); giọng gốc Demucs tách ra phát lại ở chỗ không có câu lồng
  (tiếng cười / hét / câu nghe sót — `keep_unvoiced`, builder `vocals_audio`); kế hoạch dựng tự bỏ zoom / hiệu ứng /
  sticker / SFX / chữ nhấn / chuyển cảnh / filter, không tự thêm chuyển động hình — chỉ chọn đoạn hay.
  **Cập nhật 11/10 ("nhiều khi không bắt được tiếng gốc"):** trước khi chọn tình huống, tool tách giọng bằng Demucs rồi
  nhận dạng LẠI lời thoại trên `vocals_00.wav` với bộ lọc giọng nói nhạy hơn (`whisper_options` trong
  `config/char_dub.yaml`: VAD threshold 0.3, lặng 500 ms, không bám câu trước — đối chiếu faster-whisper 1.2.1;
  `Runner._vocals_transcript`, bản cũ ở `transcript_mix.json`).
  **Cập nhật 11/10 ("tách nhạc nền lâu cực"):** Demucs CHỈ tách các tình huống đã duyệt (`separate_ranges`: nối các đoạn
  ± 1s đệm thành một file, tách một lần, đặt lại đúng giây gốc vào `bgm_00.wav` / `vocals_00.wav` dài bằng video; đổi tình
  huống thì tách lại — `job.data.bgm_ranges`), nhận dạng lại thoại chạy SAU bước duyệt trên `vocals_concat.wav` rồi đổi
  giây về gốc (`to_source_time`); nhật ký báo Demucs chạy GPU hay CPU; `install_gpu_torch.bat` đổi PyTorch của .venv sang
  bản CUDA 12.6 (bản cu128 của PyTorch 2.8 bỏ hỗ trợ GTX 10xx / Pascal — install_omnivoice.bat cũng dùng cu126).
  **Cập nhật 11/10 ("câu nói hay, hài, gay cấn — cái gì hấp dẫn"):** "đoạn hay" định nghĩa chung `HOOKY_KINDS`
  (câu nói hay / thoại đắt, hài, gay cấn, bất ngờ, cảm xúc, ấn tượng — cứ hấp dẫn là chọn, ghi loại trong ghi chú) CHỈ
  dùng cho chế độ chọn đoạn hay này. **Chủ dự án 11/10: "review phim và chọn đoạn hay là 2 chức năng khác nhau"** —
  review phim (chọn đoạn để KỂ CHUYỆN) và chia video dài giữ cách chọn đoạn riêng, không dùng `HOOKY_KINDS`.
- **Cập nhật 12/10 ("lồng tiếng nói nhầm ngôn ngữ gốc"):** tiếng gốc lấy theo loại chữ thật của lời thoại khi AI báo
  khác (`script_language` trong `understand` — AI báo trùng tiếng đích thì tool tưởng khỏi dịch); mọi kịch bản thuyết minh /
  lồng tiếng / review bị chặn khi có câu `text` không viết bằng ngôn ngữ đích (`check_target_language`, AI phải viết lại);
  OmniVoice bỏ qua câu còn tiếng gốc (`wrong_language`, ghi ⚠️ vào nhật ký).
- Chủ dự án thu voice THEO NHÂN VẬT: mỗi nhân vật một file (đọc hết câu của nhân vật đó, nghỉ ~1 giây) — tool cắt đúng vào
  các câu (`dub_io.split_upload_speaker`); sửa tên nhân vật AI đoán nhầm ngay trên trang voice (`set_speakers`).
- Âm thanh: tiếng nói gốc tách bỏ bằng Demucs, NHẠC + TIẾNG NỀN GỐC GIỮ NGUYÊN (hạ nhỏ dưới giọng lồng), không thêm
  nhạc AI; chưa cài Demucs thì dùng nhạc AI và ghi lý do vào nhật ký. Voice đến đâu ghi CapCut đến đấy như các chế độ khác.
- ~~Nhận diện nhân vật chỉ do AI đoán theo ngữ cảnh~~ **Cập nhật 11/10 (chủ dự án: "cứ bắt sót câu, sót ý; giọng của nhân
  vật nào thì phải chuẩn"):** (1) **nghe lại chỗ sót** — trên `vocals_concat.wav`, chỗ có tiếng người (`voiced_regions`)
  mà chưa có câu (`uncovered_speech`) được ghép lại nhận dạng KHÔNG VAD, bỏ câu "bịa" quen thuộc (`HALLUCINATIONS`),
  thêm vào lời thoại (`Runner._rescue_gaps`, `rescue_*` trong `config/char_dub.yaml`); nhận dạng lại trên giọng tách
  nhạc chạy thường (`batched: false`); (2) **nhóm giọng** — máy đo cao độ (tự tương quan) + âm sắc (MFCC) từng câu, gom
  nhóm G1, G2… (`app/analysis/speech_gaps.voice_groups`, chỉ numpy, không tải model), ghi vào đề bài `dub_char.md`
  (`VOICE_NOTE`, mỗi câu `[giọng Gx · cao ~Hz]`), lưu `plan/voice_groups_videoNN.json`; `check_char_dub` bắt AI xem lại
  nhóm giọng ≥ 4 câu bị gán lẫn tên (< 60% cùng tên) và câu dịch ngắn bất thường (sót ý); trang voice hiện giọng máy đo
  + "đặt tên cả nhóm"; OmniVoice clone chỉ lấy mẫu từ nhóm giọng chính của nhân vật. SpeechBrain (chính xác hơn) chưa
  dùng vì kéo theo torchaudio CPU có thể làm hỏng PyTorch GPU.
  **Cập nhật 11/10 ("bị lẫn giọng cũ"):** lồng tiếng nhân vật tách nhạc bằng `htdemucs_ft` (`demucs_model`, `demucs_shifts`
  → cờ `--shifts`, đối chiếu demucs 4.1.0; đổi model thì tự tách lại — `job.data.bgm_model`); giọng gốc tắt rộng thêm
  `unvoiced_pad_s` quanh mỗi câu và tắt cả khoảng hở < `unvoiced_min_gap_s` (`builder.merge_close`); nhạc nền gốc hạ
  `bgm_duck_db` (-14) dưới giọng lồng để che giọng gốc còn sót.
- **Giọng AI bằng OmniVoice (chủ dự án yêu cầu 11/10, tùy chọn — áp dụng cho mọi chế độ có voice thuyết minh):** nút
  "🤖 Cho OmniVoice đọc" trên trang voice; mỗi nhân vật (`speaker`, không có thì "Người dẫn") một giọng: "Mô tả giọng"
  (`instruct` — AI đề xuất trong `DubScript.cast`), "OmniVoice tự chọn", hoặc "Clone từ giọng gốc" (3–10 giây cắt từ phần
  giọng nói Demucs tách ra `analysis/audio/vocals_00.wav`, kèm lời thoại gốc làm `ref_text`) — CHỈ khi tick xác nhận có
  quyền (`job.data.tts.clone_ok`), không tick thì tự đổi sang mô tả giọng. Mỗi câu đọc vừa khít thời lượng câu gốc
  (`duration`, `fit_duration` trong `config/tts.yaml`), ghi thẳng `voice/videoNN_dubMM.wav` rồi dựng như voice thu tay.
  OmniVoice (k2-fsa, Apache-2.0, API đối chiếu mã nguồn 0.2.1) chạy ở tiến trình riêng `app/tts/omnivoice_worker.py` bằng
  python của môi trường đã cài (`config/tts.yaml → python`, `requirements-tts.txt`); logic phía tool ở `app/tts/voices.py`.
  Clone khác ngôn ngữ (giọng Nhật → đọc Hàn) sẽ có chút âm sắc tiếng gốc (theo tài liệu OmniVoice).
  **Cập nhật 11/10 (chủ dự án yêu cầu): "🎤 Giọng mẫu tải lên"** — cách tạo giọng thứ 4 (`mode: upload`): chủ dự án tải file
  giọng mẫu cho từng nhân vật (+ lời đọc trong file, không bắt buộc), lưu `voice/refs/tai_len_<tên>.<đuôi>`, giữ cho các
  lần đọc sau; khi đọc đổi sang WAV mono 24 kHz ≤ `max_ref_s` (dài hơn thì lấy đoạn đầu, bỏ lời đọc — `prepare_sample`)
  rồi clone như giọng gốc. Cũng CHỈ khi tick xác nhận quyền (`clone_ok`).
  **Cập nhật 11/10 (chủ dự án muốn dùng bản OmniVoice "chuẩn hơn" của Voice Studio):** trang chủ → ⚙️ Cài đặt → 🤖 OmniVoice
  chọn python + model (tên HF hoặc thư mục) lưu `config/local.yaml → tts_python / tts_model` (`voices.load_cfg` ghép với
  `config/tts.yaml`), nút 🔎 Kiểm tra (`check_omnivoice`: bản omnivoice, torch, GPU, model là thư mục?); worker bị tắt khi
  quá `timeout_s` hoặc bấm Dừng (`run_worker`).

## 5c. Chế độ "Phụ đề tiếng Việt" (chủ dự án yêu cầu 08/10)

- Mục đích: chủ dự án XEM HIỂU video nước ngoài, không đăng. Ô tick "🇻🇳 Chỉ phụ đề tiếng Việt" (`JobOptions.vi_sub`).
- Job chỉ chạy: phân tích (Whisper nhận MỌI ngôn ngữ) → dịch từng câu sang tiếng Việt theo lô (prompt `subtitle_vi.md`,
  kèm câu trước/sau làm bối cảnh, lưu `plan/subtitle_vi.json`) → xuất `deliver/<tên video>_vi.srt` + draft CapCut giữ
  nguyên video & tiếng gốc, phụ đề trắng viền đen (`app/planner/visub.py`). Không hiểu nội dung / kế hoạch / caption.

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
  **Cập nhật 07/10:** chỉ còn **2 dòng tiêu đề phía trên** (bỏ 2 dòng dưới — `bottom_titles: false`), **nền mặc định
  trắng**, **chữ tiêu đề đen** (viền trắng mảnh) — `config/layout.yaml → four_titles`.
  **Cập nhật 11/10:** ô Khung video có thêm 4:5 / 3:4 / 9:10 / 9:16 (mọi tỉ lệ trong `RATIOS` của
  `app/capcut_writer/layout.py`; 9:16 = kín màn hình, chữ đè theo `overlay`).
  **Cập nhật 15/10 (chủ dự án): BỎ ô "Khung video" + "Đổi khung theo cảnh" trên trang chủ — mọi job mới giữ KHUNG VIDEO GỐC,
  không cắt, không thu phóng** (`job.data.default_ratio = "source"` → `Runner._keep_frame`: khối = `nearest_ratio` của
  video gốc, `crop_ratio` None, style `keep_frame` → builder không crop / không zoom / không chuyển động / không góc máy;
  bố cục cố định như `review_story` cũng theo khung gốc — `layout_for`; content nhiều phim + dừng hình cũng vậy). Job cũ giữ
  khung đã chọn.
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

**Thêm (chủ dự án yêu cầu 07/10):**
- **Chuyển cảnh liên tục** (ô tick ⚡, `JobOptions.hype`, `config/hype.yaml`): cắt thật nhiều cảnh 3–5 giây (kiểm tra
  nới 2.5–6s); AI đánh dấu cảnh gay cấn `highlight`, CODE tự xếp các cảnh đó lên ĐẦU, cảnh còn lại về SAU theo thời gian
  (`reorder_hype`). Không dùng cùng "Chỉ thay tiếng".
- **Ghép nhiều video** (nhiều dòng ở ô footage; chủ dự án chốt 08/10): tool nối các video thành `source/montage.mp4`
  (cùng khung theo hướng đa số, 30 fps, video thiếu tiếng được bù lặng — `app/analysis/montage.py`), lưu mốc từng video
  (`montage_parts`), dùng TOÀN BỘ footage. AI chọn lọc đoạn hay từ ≥ 80% số video, ghép thành **MỘT câu chuyện ý nghĩa
  dài ~2 phút** (100–140s — chặng đường, quá trình, khoảng thời gian đáng nhớ, tình bạn đẹp...), theo mạch mở–cao trào–
  kết; cảnh 3–5s, khoảnh khắc đắt ≤ 10s; **GIỮ tiếng gốc** + nhạc nền cảm xúc + hiệu ứng, chuyển cảnh mềm; clip không vắt
  qua 2 video; không chia video. Không tự xếp gay cấn lên đầu (tick ⚡ nếu muốn). Cấu hình `montage_*` trong
  `config/hype.yaml`.

**Thêm (chủ dự án yêu cầu 09/10): Review phim / hoạt hình** (ô tick 🎬, `JobOptions.review`, `config/review.yaml`): AI
tìm các ĐOẠN HAY (luôn qua bảng duyệt chia video), mỗi đoạn thành **một video review 60–90 giây** (cảnh theo đúng thứ tự
phim, ≤ 12s/cảnh); AI xem khung hình rồi viết **lời review** (kể lại + bình luận, phủ 60–95% thời lượng, prompt
`dub_review.md`) bằng ngôn ngữ đích (không chọn thì tiếng gốc); chủ dự án thu voice như chế độ Đổi ngôn ngữ; tiếng phim
**hạ nhỏ** dưới voice (`original_audio`), không tắt hẳn. Không dùng cùng "Chỉ thay tiếng" / "Phụ đề tiếng Việt"; tắt ⚡.
Cập nhật 09/10: lời review là **KỂ CHUYỆN** (mở đầu – mâu thuẫn – cao trào – kết, nối nhân – quả, động cơ / cảm xúc
nhân vật), KHÔNG thuật lại "ai đang làm gì": AI viết `story_vi` (dàn ý) trước; code chặn khi > 30% câu kiểu tả cảnh
(`check_story`, `max_describe_share`); dàn ý in ở đầu mỗi video trong `dub_scripts.txt`.
Cập nhật 09/10 (video mẫu chủ dự án gửi — review SpongeBob tiếng Hàn): **chuyển cảnh rất nhanh** (cảnh 1–3s, trung bình
≤ `avg_clip_s` 3s, tối đa 6s), **một câu kể chạy liền qua nhiều cảnh** (`span` trong check_dub / repair_dub), giọng kể thì
quá khứ (~습니다/~었죠); bố cục `review_story` (`config/layout.yaml`): nền tối, 2 dòng tiêu đề trắng + xanh lá, khối phim
9:10 cố định, phụ đề trắng viền đen cụm ngắn (≤ 10 ký tự Hàn) ở ~2/3 khối.
Cập nhật 09/10: mỗi video review dài **2:30** (`min_video_s` 130 – `max_video_s` 150, đoạn phim gốc 140–420s);
**tốc độ đọc riêng của giọng review** `voice_cps` trong `config/review.yaml` (tiếng Hàn 8.7 chữ/giây — đo từ voice mẫu
"스펀지밥이 잡지에서 베프 퀴즈를 발견했습니다." = 20 chữ / 2.3s); tốc độ đo thật khi dựng lưu riêng
`config/local.yaml → review_voice_cps`, không lẫn với giọng thuyết minh (`review_dub_cfg`).
**Chủ dự án chốt 09/10 (thay các mục "tiếng phim hạ nhỏ" / "ngừng kể ở khoảnh khắc đắt" ở trên): phim gốc CHỈ LẤY
HÌNH — tiếng phim TẮT HẲN** (`original_audio.mute: true`); **toàn bộ âm thanh là giọng review nói LIỀN MẠCH** từ đầu tới
cuối (+ nhạc nền nhẹ): lời phủ ≥ 90%, 2 câu cách nhau ≤ `max_gap_s` 0.6s, câu cuối sát cảnh cuối (`check_continuous`);
không clip replay / lặp lại; điều quan trọng nhân vật nói thì người review kể lại bằng lời của mình.
**HÌNH CHẠY THEO GIỌNG (chủ dự án yêu cầu 09/10):** khi dựng, tool đo độ dài voice THẬT từng câu rồi co / giãn các cảnh
của câu đó cho khớp (giữ số lần cắt; co thì bỏ cảnh < `min_clip_s`; giãn thì kéo phần phim liền sau, hết chỗ thì chậm nhẹ
tới 0.8x) — câu nối liền cách `voice_gap_s`, video dài đúng bằng tổng giọng (`app/planner/review_sync.py`). Trang voice
không còn "chỗ trống" cố định cho review; thu cả bài một file thì tool cắt theo tỉ lệ số chữ. AI được xem khung hình của
TỪNG cảnh (tối đa `frames` 80). Tốc độ giọng review: base `voice_cps` ko 10 (đo 22 chữ / 2s), sau đó dùng ĐÚNG tốc độ đo
thật (`review_voice_cps`, kể cả nhanh hơn).
**QUY TRÌNH REVIEW CHỐT 09/10 (thay "hình chạy theo giọng" ở trên): VIẾT LỜI TRƯỚC → THU VOICE → DỰNG TỪ VOICE.**
(1) AI xem khung hình cả đoạn phim, viết TRƯỚC một bài lời đọc kể chuyện liền mạch, độ dài theo tốc độ giọng
(`make_review_script`, prompt `dub_review.md`); mỗi câu ghi ĐOẠN PHIM nó kể (giây gốc, theo thứ tự, không chồng, đủ dài —
`check_review_script`). (2) Trang voice + `dub_scripts.txt` hiện CẢ BÀI để đọc liền một mạch vào MỘT file (tool cắt
theo tỉ lệ số chữ). (3) Khi dựng, tool cắt cảnh trong đoạn phim của từng câu, mỗi cảnh ~`cut_s` 2s, tổng đúng bằng câu
đọc + `voice_gap_s` (`app/planner/review_sync.build_from_voice`); kế hoạch AI chỉ còn dùng cho tiêu đề / nhạc / filter /
zoom. Câu chưa có voice tạm tính theo số chữ để dựng thử.
Giao diện (09/10): thanh tiến trình đặt tên bước riêng theo chế độ (`STEP_VI_MODE`, `job_mode` trong
`app/web/server.py`) + ghi rõ chế độ ở đầu trang job; review phim KHÔNG có hook riêng (`Job.use_hook`, kể cả job cũ đã
tick) vì câu mở đầu bài lời đọc là hook.
**CHỐT 11/10 (thay mọi mục "chia nhiều video / đoạn hay / 2:30" ở trên): review = MỘT video TÓM GỌN CẢ PHIM, CHỈ Ý
CHÍNH, thời lượng CHỦ DỰ ÁN CHỌN khi tạo job** (ô "⏱️ Thời lượng video review", `JobOptions.review_s`, lựa chọn
`durations` / mặc định `default_s` trong `config/review.yaml`). Không bước chia đoạn / bảng duyệt (`Job.picks_segments`
= split hoặc char_dub); `review_target` đặt độ dài bài đọc 95–100% thời lượng chọn (kế hoạch AI nới 85%); bài phải kể tới
KẾT (`min_reach` 0.85 trong `check_review_script`); lời thoại gửi AI rải đều cả phim (`format_transcript_spread`), phân
tích lấy `max_frames_review` 80 khung; prompt `dub_review.md` mục "MỘT video tóm gọn CẢ phim — CHỈ Ý CHÍNH".
**Review LUÔN ở NGÔI THỨ 3 (chủ dự án 11/10):** người kể là người ngoài, không xưng tôi / mình / chúng ta (저는·제가·저희·
내가·우리는 / 私·僕·俺 / I·me·we·us), không nói chuyện với người xem; lời nhân vật trong ngoặc kép không tính — luật trong
`dub_review.md` + `review_polish.md`, code chặn bằng `check_third_person` (gọi trong `check_story`).
**Review nói LIÊN TỤC (chủ dự án 11/10):** khi dựng, mỗi câu voice được cắt sạch lặng đầu / cuối (bản ở
`voice/_lien_mach/`, `voice_trim_keep_s` 0.03), 2 câu nghỉ `voice_gap_s` 0.05s (bộ xếp voice dùng đúng khoảng này cho review).
**Lời review hay & tự nhiên (chủ dự án 09/10: "viết thoại chưa hay, chưa tự nhiên"):** (1) lượt 2 biên tập —
AI đọc lại cả bài như biên tập viên bản xứ, sửa câu cứng / dịch máy / lặp từ nối / nhịp đều đều, giữ số câu + đoạn phim
(`polish_review_script`, prompt `review_polish.md`, `polish: true` trong `config/review.yaml`; sai thì giữ bản nháp);
(2) văn mẫu `config/review_style.txt` — chủ dự án dán lời video review họ thích, AI học giọng / nhịp (cả 2 lượt);
(3) nút "✍️ Viết lại theo góp ý" trên trang voice (`Runner.rewrite_review`, gửi góp ý + bản trước; voice cũ → *_cu).
**REVIEW BỎ LỬNG (chủ dự án yêu cầu 14/10) — chế độ RIÊNG, review cũ ở trên giữ nguyên:** thẻ "🧨 Review bỏ lửng"
(`JobOptions.cliff`, đi cùng `review=True` để dùng chung mọi thứ của review; `config/cliff.yaml`, `app/director/cliff.py`).
Kể HẾT phim, KHÔNG BỎ CẢNH: AI chia cả phim thành các PHẦN liền nhau (phần sau bắt đầu đúng chỗ phần trước dừng, phủ kín
từ đầu tới cuối — `check_parts`, hở nhỏ tự nối `repair_parts`; phim dài chia lượt hỏi song song như `long_parts` rồi nối,
phần quá ngắn ở chỗ nối gộp vào phần trước), prompt `cliff_segment.md`, luôn qua bảng duyệt. Mỗi phần = một video
**1:30–2:00 TÍNH CẢ short**: đầu video là đoạn SHORT 5–15 giây kịch tính nằm trong phần, GIỮ NGUYÊN hình + tiếng gốc
(không nhạc / zoom / câu hook — builder `cold_clip`, sửa giây được trên bảng duyệt; **cập nhật 14/10: có PHỤ ĐỀ** — lời thoại gốc trong short dịch sang ngôn ngữ đích, prompt `cliff_hook_subs.md`, lưu `plan/hook_subs_videoNN.json`, cùng tiếng thì dùng nguyên lời gốc — `cold_subs`), rồi lời review (prompt
`dub_cliff.md` + biên tập `cliff_polish.md`) kể phủ kín đoạn phim của phần (`check_coverage`: ≥ 85%, không nhảy > 30s,
kể từ đầu phần tới cuối phần), phần 2 trở đi nhắc nhanh bối cảnh, phần nào (trừ phần cuối) cũng kết BỎ LỬNG (không "xem
phần sau"), phần cuối kể tới kết phim. **Ngôi kể chọn khi tạo job** (`cliff_pov`): ngôi 3 như review cũ, hoặc ngôi 1 —
người kể LÀ nhân vật chính (`narrator_vi` do AI nhận ra lúc chia phần) xưng "tôi" (`check_first_person`). Ngôn ngữ
Hàn / Nhật / Anh như review.
**CONTENT NHIỀU PHIM TỪ BÀI TIKTOK ẢNH (chủ dự án yêu cầu 14/10):** thẻ "🎞️ Content nhiều phim" (`JobOptions.films`,
`config/films.yaml`, `app/director/films.py`, `app/planner/films_build.py`). Bước riêng: `post` (bài gốc: chủ dự án TỰ GÕ
tiêu đề + tải ảnh lên `post/` — **cập nhật 14/10: bỏ ô dán link / yt-dlp**, chủ dự án nhập tiêu đề tay) → `idea` (AI xem ảnh + tiêu đề, nhận ra các PHIM, viết content MỚI: mỗi câu gắn phim, `shot`
video / freeze, cảnh cần tìm; prompt `films_idea.md`; góp ý → viết lại, vd "bỏ phim 3") → `films_wait` (chủ dự án chọn file
từng phim) → `analyze` (mỗi phim một footage, KHÔNG nối; chế độ nhanh `fast`: chỉ dò cảnh + `frames_per_film` khung, không
Whisper / dò mặt / làm sạch âm thanh) → `match` (AI tìm cảnh cho từng câu TRONG ĐÚNG phim đó, mỗi phim một lượt song song,
prompt `films_match.md`; nút "🔎 tìm lại cảnh" giữ voice) → `dub` (bài đọc thành DubScript có `story_vi` → dùng chung trang
voice / đọc cả bài / OmniVoice với review) → voice → `write`. **Dừng hình (chủ dự án chọn 14/10):** video chạy tới
`freeze_t` rồi đứng hình bằng ẢNH TOOL TỰ CẮT TỪ PHIM (cắt đúng vùng khối hình), zoom chậm, SFX "tách", tên nhân vật hiện
giữa khối; dừng hình ≤ `image_share` 30% video. Tiếng phim tắt; bố cục như review; tên phim hiện khi sang phim mới; caption
viết cùng content. Video `video_s` 60–120s.
**Voice đến đâu ghi CapCut đến đấy (chủ dự án yêu cầu 09/10, mọi chế độ có voice thuyết minh / review):** job ra
nhiều video thì video nào ĐỦ voice được ghi draft CapCut NGAY ở bước chờ voice (`Runner.write_ready_videos`, lưu
`job.data.ready_drafts` + dấu vân tay voice — thu lại câu nào thì ghi lại), không chờ các video khác; đủ hết thì bước
write ghi lại toàn bộ như thường. Trang voice báo "✅ Đã ghi dự án CapCut" cho từng video.

Nguyên liệu đạo diễn tự phối (liều lượng do preset quy định, không dùng hết mọi thứ cho mọi video):
- Cắt và nhịp: bỏ khoảng lặng, câu vấp, đoạn thừa; tăng tốc đoạn nhàm.
- Chuyển động hình: zoom giật, zoom chậm, lắc, dừng hình, quay chậm.
- Chữ: phụ đề thoại, chữ nhấn, bình luận chêm, emoji, tiêu đề dải trên.
- Âm thanh: nhạc nền theo tâm trạng từng đoạn, tự hạ nhạc khi có thoại (ducking), SFX ở điểm nhấn.
- Chuyển cảnh, filter, tông màu đồng bộ.

**Phụ đề CJK**: tiếng Nhật không có dấu cách → ngắt dòng theo số ký tự và cụm nghĩa; tiếng Hàn và Nhật có giới hạn ký tự/dòng và ký tự/giây riêng (tham khảo giá trị trong capcut-cli, cấu hình được). Font phải hỗ trợ Hangul/Kana/Kanji (ví dụ Noto Sans KR/JP).

## 9. Giao diện

**Cập nhật 11/10 (chủ dự án): trang chủ làm lại** — bỏ thẻ "Kho tài nguyên" và "So sánh video" (bỏ cả `/compare`; mã
quét kho vẫn dùng khi dựng); form tạo video theo 3 bước: chọn video → chọn MỘT chế độ bằng thẻ (`mode`: normal / dub /
voice_only / review / char_dub / vi_sub, server đổi sang các cờ JobOptions cũ) → tùy chọn (ẩn cái không hợp chế độ) +
"Nâng cao" (AI đạo diễn, nhạc, mã khách); cài đặt luồng / tự xóa / dự án mẫu nằm dưới danh sách video.
**Cập nhật 11/10 (chủ dự án: "dựng video TikTok lỗi vì chưa chọn ngôn ngữ mà không có chỗ chọn"):** thẻ Dựng video TikTok
có ô ngôn ngữ (mặc định giữ nguyên; video gốc không phải Hàn / Nhật / Anh thì chọn → thuyết minh như Đổi ngôn ngữ); job đã lỗi
vì thiếu ngôn ngữ (`job.data.need_language`) hiện khung chọn ngôn ngữ trên trang job (`/jobs/{id}/language`), chạy tiếp dùng
lại `understanding.json` (`reuse_understanding`), không hỏi lại AI.
**Cập nhật 11/10 (chủ dự án):** mục "Kiểu dựng" trên trang chủ chỉ còn "✨ AI tự chọn" (các preset vẫn trong `styles/`, AI
chọn theo nội dung); bỏ ô "Giữ nhạc nền gốc" của chế độ Chỉ thay tiếng (mã `keep_bgm` vẫn còn, Lồng tiếng nhân vật vẫn tách
giọng bằng Demucs).

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
- Backend Gemini = Antigravity CLI (11/10, đối chiếu `agy --help` + chạy thử thật bản 1.3.3 trên máy chủ dự án):
  `agy -p "<đọc de_bai.md…>" --output-format json --json-schema schema.json [--model] [--effort]`; `-p` KHÔNG đọc stdin →
  đề bài ghi vào `de_bai.md` + khung hình cùng thư mục làm việc tạm, AI tự đọc file / xem ảnh (không cần xin quyền);
  kết quả ở `structured_output`; công cụ cần xin quyền (RunCommand) tự bị từ chối — KHÔNG dùng
  `--dangerously-skip-permissions` (cập nhật 11/10: đề bài luôn kèm `TOOLS_NOTE` — chỉ đọc file, không web / URL / lệnh; AI
  vẫn lỡ dùng công cụ bị chặn — vd `ReadUrlContent` — thì `ToolDenied` → tự hỏi lại tối đa 2 lần kèm `RETRY_NOTE`);
  `agy` tự cập nhật ngầm, tìm ở `%LOCALAPPDATA%\agy\bin\agy.exe` nếu không có PATH.
- **Hỏi AI song song trong một job (chủ dự án 11/10: "Gemini chậm, video > 10 phút chia ra làm rồi gộp"):** bước chọn
  đoạn của video dài hơn `long_video.split_over_s` (600s) chia thành vài phần ~10 phút, điểm chia ở khoảng lặng dài nhất
  gần điểm chia đều (`long_parts`), mỗi phần một lượt hỏi (chỉ chọn trong phần của mình — `restrict`), chạy song song
  rồi gộp (`make_segments_long`); lập kế hoạch / viết thoại nhiều video cũng chạy song song. Số lượt cùng lúc
  `parallel_calls` (2) trong `config/director.yaml`, `app/jobs/parallel.py` (gắn job cho luồng con để nút Dừng vẫn chạy).
  **Cập nhật 15/10 ("đợi lượt hỏi AI lâu quá"):** giới hạn số lượt hỏi AI cùng lúc trên MỌI job đặt ở TỪNG LƯỢT GỌI AI
  (`limits.ai_slot` trong `Director.run`), không giữ cả bước nữa; số lượt chỉnh trên giao diện ⚙️ Cài đặt
  (`config/local.yaml → parallel_ai`, mặc định `config/app.yaml → parallel.director` = 3).
- **Nhanh hơn (chủ dự án 11/10: "chậm quá"):** ≥ 6 khung hình thì ghép thành ẢNH LƯỚI 3×3 có nhãn tên file trước khi gửi
  AI (`app/director/contact_sheet.py`, `contact_sheet` trong `config/director.yaml`) — AI đọc 9 file thay vì 80; dùng cho cả
  Claude lẫn Antigravity. Phân tích bỏ phần chế độ không dùng (Phụ đề tiếng Việt: không dò cảnh / mặt; Chỉ thay tiếng: không
  dò mặt). Mỗi bước job ghi thời gian (`job.data.step_times`, hiện ở đầu trang job).
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
