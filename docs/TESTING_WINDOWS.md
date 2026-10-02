# Hướng dẫn kiểm tra trên máy Windows

## Bước 35 — Che chữ in sẵn: hạn chế che, che phải đẹp `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **🔁 Dựng lại draft** (tool tự dò lại vùng chữ kèm thời gian).
2. Mở draft trong CapCut, kiểm tra:
   - cảnh nào chữ sát mép: được cắt chặt hơn (giờ chấp nhận tới 25%) thay vì che;
   - dải che CHỈ hiện đúng lúc chữ gốc hiện (phụ đề cứng câu nào hiện thì che câu đó), lúc không có chữ thì không che;
   - dải che nửa trong suốt (vẫn thấy mờ hình phía sau), bo tròn góc, chỉ rộng vừa hơn chữ một chút;
   - phụ đề cứng nằm gần hàng phụ đề của tool → dải che đặt đúng hàng phụ đề mới, nhìn như một thanh phụ đề.
3. Muốn chỉnh trong `config\text_cover.yaml`: `cover_alpha` (0.6; tăng nếu chữ gốc còn lộ), `cover_round`, `cover_pad`,
   `min_scale` (giảm để cắt tránh nhiều hơn, che ít hơn).

## Bước 34 — Chữ in sẵn trên footage: tự cắt tránh, không được thì che `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Chọn footage có chữ in sẵn (phụ đề cứng tiếng Trung/Hàn, tiêu đề,
   logo chữ). Tính năng chạy khi bước AI hiểu nội dung báo "có chữ in sẵn" (xem ghi chú editor ở bước xác nhận).
   Job cũ: bấm **🔁 Dựng lại draft**.
2. Nhật ký: "Dò được N vùng chữ in sẵn trên footage" và "Chữ in sẵn: cắt chặt hơn để tránh ở X cảnh, che ở Y chỗ".
3. Mở draft trong CapCut, kiểm tra:
   - chữ sát mép (phụ đề cứng ở đáy, tiêu đề ở đỉnh): khung được cắt chặt hơn một chút, chữ nằm NGOÀI khung;
   - chữ không tránh được (giữa khung, hoặc phải cắt mất quá 20%): có **dải nền tối** đè đúng chỗ chữ.
     Dải che dựng bằng một hàng ký tự "■" + nền chữ cùng màu — kiểm tra nó có che kín, đúng vị trí, không lệch.
     Nếu lệch / không kín: chụp màn hình gửi lại (có thể chỉnh `cover_pad`), hoặc tắt che: `cover: false`.
4. Thông số trong `config\text_cover.yaml`: `min_scale` (cắt tối đa bao nhiêu để tránh chữ), `cover`, màu, độ mờ.
   Vùng chữ dò được lưu ở `jobs\<job>\analysis\text_boxes.json` (xóa file này để dò lại).

## Bước 33 — Đổi ngôn ngữ: tự TẮT HẲN tiếng gốc của video `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job Đổi ngôn ngữ cũ: bấm **🔁 Dựng lại draft** (muốn AI viết thêm câu
   cho chỗ trước đây để tiếng cười gốc thì bấm **🌐 Viết lại thuyết minh**).
2. Mở draft trong CapCut, kiểm tra:
   - mọi clip video (kể cả phần hook) có âm lượng 0 — không còn nghe tiếng gốc;
   - chỉ còn: voice thuyết minh / lời dẫn + voice hook + nhạc nền + SFX;
   - nhật ký có dòng "Đã tắt hẳn tiếng gốc của video".
3. Muốn giữ tiếng gốc nhỏ như trước (-20 dB dưới voice, -6 dB chỗ khác): `config\dub.yaml` → `mute_original: false`.
4. Chế độ dựng thường (không Đổi ngôn ngữ) vẫn giữ tiếng gốc vì lời thoại chính là nội dung.

## Bước 32 — So sánh video gốc và video đã edit (khác bao nhiêu %) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Xuất video từ CapCut như bình thường (File → Export).
3. Cách 1 — trang chủ, ô **🔍 So sánh video gốc và video đã edit**: chọn video gốc + video đã xuất → **So sánh**.
   Cách 2 — trang job đã xong → mở **🔍 So sánh với video gốc** (video gốc đã điền sẵn), chỉ cần chọn file đã xuất.
4. Trang kết quả: số % khác tổng + từng phần (🖼️ hình, 🔊 tiếng, ⏱️ thời lượng) kèm chi tiết, ví dụ
   "40% khung hình gần như trùng khung gốc (trong đó 10% là cảnh lật ngang)".
5. Video dài 5–10 phút có thể mất 1–2 phút. Phần tiếng cần FFmpeg (đã cài theo SETUP_WINDOWS); thiếu thì chỉ tính hình +
   thời lượng (trang kết quả ghi rõ).
6. Thử: so một video với CHÍNH nó → khoảng 0%; so hai video khác hẳn nhau → gần 100%. Báo lại nếu con số thấy vô lý.

## Bước 31 — Đổi ngôn ngữ: kịch bản viết theo nước của khán giả (bản địa hóa) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: **✍️ Viết hook mới** + **🎬 Lập lại kế hoạch dựng** +
   **🌐 Viết lại thuyết minh** (hoặc tạo job mới).
2. Thử video tiếng Trung / Hàn đổi sang tiếng Nhật (hoặc Anh). Trong bảng thu voice, câu nào AI đổi cho hợp khán giả
   có dòng **🌏 Bản địa hóa: …** (vd so món lạ với món Nhật quen, đổi đơn vị, đổi cách đùa).
3. Đọc nghĩa tiếng Việt: giọng có tự nhiên như người nước đó nói không (Nhật: です・ます nhẹ nhàng; Hàn: 해요체;
   Anh: thân mật kiểu TikTok Mỹ), chi tiết văn hóa lạ có được giải thích ngắn không, có đúng sự việc trong video không.
4. Hook, tiêu đề, caption cũng viết theo cách của nước đó.
5. Muốn chỉnh hướng dẫn cho từng nước: `config\localize.yaml` (giọng, đơn vị, điều nên tránh, từ không dùng).

## Bước 30 — Phản chiếu ngang một số cảnh (chế độ Đổi ngôn ngữ / dựng lại) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job Đổi ngôn ngữ cũ: bấm **🔁 Dựng lại draft** (job phân tích từ
   trước vẫn dùng được; muốn AI đánh giá lại có chữ/logo hay không thì tạo job mới).
2. Nhật ký bước ghi draft: "Phản chiếu ngang N cảnh (để bản dựng khác bản gốc)".
3. Mở draft trong CapCut, chọn từng clip → mục **Phản chiếu** (Mirror) của các cảnh được lật phải đang bật. Kiểm tra:
   - khoảng 40% số cảnh bị lật, cảnh mở đầu giữ nguyên; trong cùng một cảnh, các cú cắt cùng chiều;
   - phụ đề / tiêu đề / sticker KHÔNG bị ngược (chỉ hình video bị lật);
   - footage có chữ in sẵn, logo, bảng hiệu, nhãn sản phẩm: tool tự KHÔNG lật (tránh chữ ngược) — nếu vẫn thấy chữ
     ngược ở cảnh nào, bỏ tick Phản chiếu cảnh đó trong CapCut và báo lại.
4. Chỉnh tỉ lệ trong `config\dub.yaml` → `style_override` → `mirror: {share: 0.4}` (0 = tắt, 0.5 = một nửa số cảnh).
   Muốn dùng cho kiểu dựng khác: thêm dòng `mirror: {share: 0.3}` vào `styles\<kiểu>.yaml`.

## Bước 29 — Khung video đúng như bạn chọn (4:3 / 1:1 / 16:9) `[CẦN KIỂM TRA TRÊN MÁY]`

Trước đây bố cục "4 dòng tiêu đề" luôn ép khối video 16:9, bỏ qua lựa chọn 4:3 / 1:1. Đã sửa.
1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ → ô **Khung video (khối giữa màn)**: 4:3 · 1:1 (vuông) · 16:9 (tràn ngang như video mẫu) ·
   Theo kiểu dựng (16:9; thể thao 9:10). Tạo job với 4:3, rồi một job với 1:1.
   Job cũ (đã chọn 4:3 lúc tạo): bấm **🔁 Dựng lại draft** là ra khung 4:3.
3. Mở draft trong CapCut, kiểm tra:
   - khối video đúng 4:3 (1080×810) / 1:1 (1080×1080), cắt bám người (podcast / giải trí);
   - 4 dòng tiêu đề dời theo khối, KHÔNG đè lên video; với 1:1 dải trên/dưới hẹp nên chữ tiêu đề nhỏ hơn —
     nếu vẫn chạm video hoặc quá nhỏ, báo lại để chỉnh `title_rows` / `title_scale_max` trong `config\layout.yaml`;
   - phụ đề vẫn nằm trong khối video, nhãn chủ đề ở góc trên phải khối.
4. Lưu ý: chọn 4:3 / 1:1 cũng áp dụng cho kiểu thể thao (thay khối 9:10). Muốn giữ 9:10 → chọn "Theo kiểu dựng".

## Bước 28 — Hook dài hơn: 1–2 câu đời thường rồi mới vào câu hook `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **✍️ Viết hook mới** (hook cũ chưa có câu dẫn).
2. Bảng **🎣 Chọn hook**: mỗi phương án có **💬 Câu dẫn** (1–2 câu bình thường, gần gũi) + câu hook (in đậm).
3. `hook_scripts.txt`: đọc LIỀN MẠCH câu dẫn rồi câu hook trong CÙNG một file `video01_hook.wav` (~6–12 giây).
4. Mở draft: phần hook có 2 cảnh — câu dẫn chạy trên cảnh bối cảnh (zoom chậm), câu hook chạy trên cảnh mạnh
   (zoom giật). Điểm chuyển cảnh tool ước lượng theo độ dài chữ — nếu lệch so với giọng đọc, kéo lại trong CapCut.
5. Hook dài hơn 12 giây: nhật ký nhắc "vượt 12s khuyến nghị" — nên thu nhanh/gọn hơn.

## Bước 27 — Mở đầu chỉ show món ăn / sản phẩm, không ai nói → tự đệm lời dẫn mở đầu `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **🌐 Viết lại thuyết minh**.
2. Chọn video nấu ăn mở đầu bằng cảnh show món thành phẩm (chưa ai nói), bật **🌐 Đổi ngôn ngữ**.
3. Bảng thu voice: câu đầu tiên là **🗣️ lời dẫn: show món thành phẩm** (hoặc tương tự), bắt đầu ngay đầu video.
   Đọc nghĩa tiếng Việt: giọng gần gũi như video nấu ăn, gợi thèm (tả đúng món đang thấy) và gợi tò mò cách làm;
   không hứa điều video không có.
4. Thu, tải lên, mở draft: voice mở đầu cất lên ngay cảnh đầu tiên.
5. Tắt nếu không muốn: `config\dub.yaml` → `narration` → `opening` → `enabled: false`.

## Bước 26 — Đổi ngôn ngữ: lời dẫn ở cảnh hay / hành động đáng chú ý `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job Đổi ngôn ngữ đã có thuyết minh cũ: bấm **🌐 Viết lại thuyết minh**.
2. Thử video nấu ăn (hoặc vlog) có đoạn dài không ai nói.
3. Bảng **🎙️ Thu voice thuyết minh**: câu có nhãn **🗣️ lời dẫn: <hành động>** là câu AI viết thêm ở chỗ không có giọng
   nói, kèm hành động lúc đó (vd "thêm gia vị", "lật miếng thịt"). Kiểm tra:
   - AI chỉ nói ở cảnh hay / hành động đáng chú ý, KHÔNG nói liên tục; chỗ thao tác lặp lại, chờ đợi để im (nhạc);
   - lời dẫn tả đúng cái đang thấy (đọc nghĩa tiếng Việt), không bịa nguyên liệu / số lượng.
4. Thu và tải lên như các câu khác. Mở draft: lời dẫn vang lên đúng lúc hành động bắt đầu.
5. Chỉnh trong `config\dub.yaml` → `narration`: `max_cover_ratio` (lời dẫn tối đa bao nhiêu % thời gian lặng,
   mặc định 60%), `min_gap_s`, `keep_reactions`.

## Bước 25 — Chế độ "Đổi ngôn ngữ" (thuyết minh + phụ đề, dựng lại khác bản gốc) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ → chọn footage (tiếng Hàn / Nhật / Anh / Trung) → ô **🌐 Đổi ngôn ngữ video**: chọn ngôn ngữ đích
   (vd "Đổi sang tiếng Nhật"). Các tùy chọn khác (hook, chia video...) dùng như cũ. Bấm Bắt đầu dựng.
   - Video tiếng Trung lần đầu: kiểm tra nhật ký bước nhận dạng thoại nhận đúng `zh` (Whisper large-v3 hỗ trợ).
3. Nhật ký sau bước AI hiểu nội dung: "Đổi ngôn ngữ: zh → ja (thuyết minh + phụ đề ja)".
4. Sau bước kế hoạch dựng: trang job hiện **🎙️ Thu voice thuyết minh** — bảng từng câu (tên file, thời lượng chỗ
   trống, câu cần thu + nghĩa tiếng Việt). File `jobs\<job>\dub_scripts.txt` có cùng nội dung.
5. Thu từng câu bằng Voice Studio, đặt tên `video01_dub01.wav`, `video01_dub02.wav`... (hoặc 1.wav, 2.wav... — tool
   tự xếp theo thứ tự), chọn TẤT CẢ file một lượt → **Tải lên**. Đủ file là tool tự dựng tiếp.
   Chưa thu kịp: bấm **⏭️ Dựng luôn** (câu thiếu voice chỉ có phụ đề); tải thêm sau ở trang Xong rồi bấm 🔁 Dựng lại draft.
6. Mở draft trong CapCut, kiểm tra:
   - voice thuyết minh nằm đúng chỗ từng câu; tiếng gốc nhỏ hẳn dưới voice (~-20 dB), chỗ không có voice to hơn;
   - phụ đề là câu ngôn ngữ đích (không còn lời gốc), ngắt dòng đọc được;
   - mọi cảnh đều khác bản gốc: cắt cận bám người, có chuyển động/zoom, filter màu, nhạc + tiêu đề mới,
     thứ tự cảnh giữ nguyên;
   - voice dài hơn chỗ trống: được tăng tốc tối đa 1.25x (nhật ký ghi câu nào bị tràn → thu lại ngắn hơn).
7. Chữ gốc in sẵn trên hình (vd phụ đề tiếng Trung có sẵn): tool không xóa được — che bằng CapCut nếu cần.
8. Tinh chỉnh trong `config\dub.yaml`: mức tiếng gốc (`original_db`), tốc độ tối đa (`max_speed`), tốc độ nói (`max_cps`).

## Bước 24 — Không nhắc nền tảng khác ngoài TikTok `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Tạo job mới (job cũ: 🎬 Lập lại kế hoạch dựng để caption/chữ được
   kiểm tra lại; muốn cắt cả lời thoại thì chạy lại từ bước AI hiểu nội dung).
2. Chọn footage có câu kiểu "subscribe my YouTube", "유튜브 구독과 좋아요", "チャンネル登録よろしく" hoặc nhắc Instagram.
3. Trang job → mục **🚫 Đoạn vi phạm chính sách TikTok**: có dòng loại "nhắc tới nền tảng khác ngoài TikTok".
   Mở draft trong CapCut, tua tới mốc đó: câu nhắc nền tảng khác đã bị cắt.
4. Mở `deliver\videoNN_captions.txt`: caption và hashtag không có YouTube / Instagram / #shorts / #reels / #쇼츠...
5. Nếu footage có logo/watermark YouTube, Instagram suốt video: tool không cắt được, AI sẽ ghi chú ở "Điều cấm" —
   hãy tự che/crop trong CapCut. Danh sách từ nằm ở `config\policy.yaml` (`other_platforms`), thêm bớt tùy ý.

## Bước 24 — Video thứ 2 không phải đợi video 1 phân tích xong; có % tiến độ `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Tạo liên tiếp 2 job. Trước đây video 2 phải đợi video 1 xong CẢ bước phân tích (có khi 10–20 phút). Bây giờ:
   - hai video phân tích cùng lúc; chỉ riêng lúc **nhận dạng thoại** (GPU) là lần lượt — nhật ký video 2 hiện
     "Đang đợi lượt GPU (nhận dạng thoại) — video khác đang dùng GPU…" rồi tự chạy tiếp;
   - "Dò cảnh… 10% / 20% …" và "Dò khuôn mặt… 10% …" hiện dần trong nhật ký, không còn đứng im lâu.
3. Dò cảnh nhanh hơn khoảng gấp đôi (chỉ xét 1/2 số khung). Nếu thấy bỏ sót điểm chuyển cảnh: sửa `frame_skip: 0`
   trong `config\analysis.yaml`.
4. Nếu máy quá chậm khi 2 video phân tích cùng lúc (CPU 100%): sửa `analyze: 1` trong `config\app.yaml`.

## Bước 23 — Tuân thủ chính sách TikTok: đoạn vi phạm tự bị cắt `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Tính năng áp dụng cho **job mới** (job cũ: bấm "Chạy lại" từ bước
   AI hiểu nội dung, hoặc tạo job mới).
2. Chọn một footage có vài câu chửi thề / đoạn nhạy cảm (ví dụ vlog có người văng tục, video có đoạn cãi nhau).
3. Nhật ký sau bước "AI hiểu nội dung": dòng "Phát hiện N đoạn vi phạm chính sách TikTok (~X s) — sẽ cắt bỏ."
4. Trang job (bước xác nhận nội dung, bảng chia video, trang Xong): mục **🚫 Đoạn vi phạm chính sách TikTok** — bấm
   để xem từng đoạn (giây, loại vi phạm, lý do; "máy tự dò" = từ tục tool tự tìm trong lời thoại).
5. Mở draft trong CapCut, tua tới các mốc đó: phần vi phạm phải KHÔNG còn (clip bị cắt quanh chỗ đó), hook không
   dùng đoạn đó, chữ trên màn hình và caption không có từ tục.
6. Nếu AI đánh dấu nhầm (cắt mất đoạn hay): mở `jobs\<job>\plan\understanding.json`, xóa mục đó trong
   `policy_issues`, rồi bấm "🎬 Lập lại kế hoạch dựng".
7. Danh sách từ tục máy tự dò nằm trong `config\policy.yaml` (`bad_words`) — thêm/bớt từ tùy ý; `enabled: false`
   để tắt hẳn tính năng.

## Bước 22 — Tự xóa job không hoạt động quá 2 ngày `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Lúc mở, tool tự dọn một lần, sau đó mỗi giờ một lần.
2. Trang chủ, ô 🗂️ Các video: "Tự xóa job không hoạt động quá: [2 ngày]" — đổi được (1/2/3/7 ngày hoặc không tự xóa).
3. Job cũ hơn 2 ngày (tính từ lần hoạt động gần nhất) biến khỏi danh sách; job đang chạy / xếp hàng không bị xóa.
4. Kiểm tra: draft trong CapCut và file footage gốc vẫn còn. Lưu ý: caption (`deliver\...captions.txt`) nằm trong
   thư mục job nên cũng bị xóa theo — copy caption ra trước nếu cần giữ lâu.

## Bước 21 — Chạy nhiều video cùng lúc (nhiều luồng) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ, ô **🗂️ Các video**: dòng "Đang chạy 0/3 luồng · chạy cùng lúc: [3]". Đổi số nếu muốn (1–6).
3. Tạo liên tiếp 2–3 job (ví dụ 1 podcast, 1 video hài, 1 vlog) — không cần đợi job trước xong.
   - Danh sách hiện "đang chạy" cho từng video; quá số luồng thì hiện "xếp hàng #1".
   - Trong lúc video khác đang chạy, trang chủ KHÔNG tự tải lại nữa (chỉ danh sách video tự cập nhật) → chọn file,
     chọn kiểu dựng, tick tùy chọn bình thường.
   - Bước **phân tích** chạy lần lượt (GPU): trang job của video sau hiện "Đang đợi lượt phân tích (GPU)…".
   - Bước **hỏi đạo diễn AI** tối đa 2 video cùng lúc.
4. Theo dõi GPU / RAM (Task Manager). Nếu máy chậm hoặc Claude báo hết hạn mức nhanh: giảm số luồng ở trang chủ,
   hoặc sửa `director: 1` trong `config/app.yaml`.

## Bước 20 — Lấy hiệu ứng / nhạc từ một dự án CapCut vào kho `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`.
2. Trang chủ → ô Kho tài nguyên → **📦 Lấy hiệu ứng / nhạc từ một dự án CapCut**. Chọn MỘT cách:
   - chọn dự án trong danh sách (dự án CapCut trên máy), hoặc
   - tải lên file **.zip** của thư mục dự án (dự án từ máy khác: nén thư mục trong
     `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\<tên dự án>`), hoặc
   - chọn thư mục dự án.
   Có thể ghi nhãn tâm trạng cho nhạc (vd "vui"). Bấm **Lấy tài nguyên**.
3. Trang kết quả liệt kê từng hiệu ứng / chuyển cảnh / sticker / nhạc: "✅ dùng được ngay" hoặc "⏳ cần CapCut tải".
   Với "cần CapCut tải": dự án đã được chép vào CapCut → mở nó trong CapCut 1 lần, chờ tải xong, đóng lại.
4. Tạo job mới: đạo diễn AI có thể chọn các hiệu ứng / nhạc đó (kể cả khi sau này bạn xóa dự án gốc trong CapCut).

## Bước 19 — Giải trí: đổi góc máy liên tục, không cảnh nào để nguyên gốc; tool tự sửa lỗi vặt của AI `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`. Vào job giải trí bị lỗi → **Chạy lại bước này** (hoặc 🎬 Lập lại kế hoạch dựng).
2. Nhật ký: nếu AI có lỗi vặt (chồng nhau vài phần giây, replay quên quay chậm, chữ nằm ngoài clip) sẽ thấy dòng
   "Tự sửa: …" thay vì "chưa hợp lệ" rồi gọi lại AI — nhanh hơn nhiều. Cũng tự sửa: clip mở đầu lặp lại đoạn phía sau
   (đánh dấu "repeat"), tên hiệu ứng/chuyển cảnh/nhạc viết lệch (ví dụ thêm "(Đang thịnh hành)") → khớp tên thật trong kho
   hoặc bỏ nếu không có.
3. Mở draft: dựng theo thứ tự (có thể mở bằng 1 khoảnh khắc đắt), **góc máy đổi liên tục** (~2.5 giây đổi cận ↔ trung,
   cắt sang người đang nói / đang cười), mọi cảnh đều có chuyển động.
4. Muốn đổi góc nhanh/chậm hơn: `max_hold_s` trong phần `camera` của `styles/entertainment.yaml`.

## Bước 18 — Làm giàu kho tài nguyên (theo README_NguonTaiNguyen) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`.
2. **Tự tải (Freesound + Openverse, chỉ CC0 / Public Domain):** trang chủ → ô Kho tài nguyên → để tick
   "Tự tải thêm cái còn thiếu" → **🔍 Quét & làm giàu kho**. Không có key Freesound vẫn tải được từ Openverse.
   Lần đầu có thể mất vài phút (14 nhóm SFX × 3 file + 12 nhóm nhạc × 2 bài). Trang kết quả liệt kê từng nhóm và file vừa tải.
   Kiểm tra: `assets\sfx\chuyen_canh\`, `assets\music\cam_dong\`… có file; `assets\CREDITS.csv` mở bằng Excel được.
3. **Nhập tay (Pixabay, Mixkit, YouTube Audio Library, Incompetech):** tải file về, xếp thư mục như README
   (ví dụ `KhoTaiNguyen\SFX\ChuyenCanh`, `KhoTaiNguyen\Nhac\CamDong`) → **📁 Nhập cả thư mục** → Chọn thư mục… →
   chọn nguồn → **Nhập vào kho**. Xem file có vào đúng nhóm không.
4. Với **Incompetech** (bắt buộc ghi tác giả): dựng một video có dùng bài đó → file `deliver\video01_captions.txt`
   có phần "GHI NGUỒN" ở cuối.
5. Nghe thử vài file tải về; file nào dở thì xóa khỏi `assets\...` (kho ít mà chuẩn hơn kho nhiều mà rác).

## Bước 17 — Cắt theo nhịp nhạc, dò tiếng cười, góc máy cho giải trí, vlog giữ âm thanh hiện trường `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`. Cần **tạo job MỚI** (bước phân tích mới dò tiếng cười và tạo bản âm thanh lọc nhẹ).
2. **Dò tiếng cười / hò reo / hét**: trong nhật ký job có dòng "Dò tiếng cười / hò reo / cao trào". Mở file
   `jobs\<job>\analysis\audio_events.json`, so vài mốc `laugh` với video xem có đúng chỗ cười không.
3. **Giải trí / hài**: chọn kiểu **Giải trí / show / hài**. Trong draft: cận người đang nói, đổi cận ↔ trung nhanh
   (~3 giây), lúc có tiếng cười thì **cắt sang người đang cười**; chữ nhấn / SFX / zoom rơi đúng chỗ cười.
4. **Vlog / du lịch**: chọn kiểu **Vlog**. Nghe âm thanh hiện trường (sóng, phố, gió) có còn rõ hơn trước không.
   (Muốn lọc ồn nhẹ/mạnh hơn: `denoise_light` trong `config/analysis.yaml`, `afftdn=nf=-40` → số âm hơn = nhẹ hơn.)
5. **Cắt theo nhịp nhạc** (Vlog, Giải trí, Cắt nhanh): nhật ký có dòng "Cắt theo nhịp nhạc '<bài>': dời X/Y điểm cắt"
   hoặc "Bài '<bài>' chưa có dữ liệu nhịp". Trong CapCut bật hiển thị nhịp của bài nhạc (nếu có) và xem điểm cắt
   có trúng nhịp không.
   - Nhạc thư viện CapCut: tool đọc file nhịp `.beat` của CapCut. **Chưa biết chắc định dạng file này** — nếu nhật ký
     báo "chưa có dữ liệu nhịp", hãy gửi Claude 1 file trong `%LOCALAPPDATA%\CapCut\User Data\Cache\music\`
     có đuôi `.beat` (file nhỏ, chỉ chứa mốc nhịp, không phải nhạc).
   - Nhạc trong kho `assets\music` (Freesound / file của bạn): tool tự dò nhịp, luôn dùng được.

## Bước 16 — Nhạc nền mức gốc -5 dB, node lên xuống theo lời thoại `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`. Vào job cũ bấm **🔁 Dựng lại draft** (không tốn lượt AI).
2. Mở draft trong CapCut, bấm vào đoạn nhạc nền → bảng Âm thanh:
   - Ở chỗ **không có thoại**, âm lượng hiện **-5.0 dB**.
   - Có các **node (keyframe) âm lượng**: đầu mỗi câu thoại nhạc hạ xuống (ví dụ -15 dB), hết câu nhạc lên lại -5 dB,
     mỗi lần chuyển có fade ngắn. Kiểm tra CapCut hiển thị đúng số dB (nếu thấy số khác -5.0, chụp gửi Claude).
3. Chỉnh: mức gốc `music_base_db` trong `config/audio.yaml`; mức hạ khi có thoại `duck_db` trong
   `styles/<kiểu>.yaml` (podcast -14, vlog -8, thể thao -9, còn lại -10). Rồi Dựng lại draft.

## Bước 15 — Podcast: góc máy tự cắt cận người đang nói `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`.
2. Tạo **job MỚI** (để bước phân tích đo cử động miệng từng người) với một đoạn podcast / phỏng vấn 2 người,
   chọn kiểu **Podcast / phỏng vấn / talk show**. (Job cũ bấm Dựng lại draft vẫn có cắt cận, nhưng chỉ bám người
   chính, không biết ai đang nói.)
3. Mở draft trong CapCut, xem:
   - Mở đầu ~2 giây toàn cảnh, sau đó cắt **cận người đang nói**; đổi người nói → cắt sang người kia đúng đầu câu.
   - Một người nói lâu → cứ ~4–5 giây đổi cận ↔ trung cảnh; ~20 giây có một cảnh toàn.
   - Câu xen ngắn ("ừ", "はい") không làm nhảy cảnh.
   - Mặt không bị cắt mất, hình không quá vỡ khi cận (footage 1080p phóng 2 lần).
4. Nhật ký job có dòng "Góc máy theo người nói: 2 người, … cảnh cận, … trung, … toàn".
5. Nếu cận quá sát / chưa đủ: sửa `close_zoom` (2.0) / `medium_zoom` (1.4) trong `styles/podcast.yaml`;
   đổi cảnh nhanh/chậm hơn: `max_hold_s`. Rồi bấm **🔁 Dựng lại draft**.

## Bước 14 — (thay bằng Bước 16: nhạc nền theo dB)

## Bước 13 — Chia video dài thành nhiều video `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`.
2. Tạo job với một footage DÀI (5–20 phút), bật **Chia video dài thành nhiều video** (và **Có hook voice** nếu muốn).
3. Job dừng ở **✂️ Duyệt chia video**: xem các video AI đề xuất (giây bắt đầu–kết thúc, độ dài, nội dung) và các
   **đoạn bị bỏ kèm lý do**. Thử: sửa giây một video, bỏ tick một video, tick một đoạn bị bỏ → **Xác nhận và dựng tiếp**.
4. **Chọn hook**: mỗi video có 3 phương án riêng, chọn cho TẤT CẢ video trong một lần bấm.
5. **Thu voice**: có ô tải lên riêng cho từng video (video01, video02…). Tải đủ thì tool tự dựng tiếp.
6. Khi xong: trang job liệt kê từng video (draft `khach_<job>_video01`, `video02`…, thời lượng, tiêu đề, caption riêng).
   Mở từng draft trong CapCut: mỗi video phải tự đứng được (có mở, diễn biến, kết), không có chữ "Part 1/2",
   dài 60–150 giây (trừ khi cả footage quá ngắn — có nhãn "ngắn hơn 1 phút").
7. Thử nút **✂️ Chia lại video**: AI chia lại, hook / kế hoạch / voice cũ phải làm lại (voice cũ đổi tên `_cu`).

Dòng lệnh (không bắt buộc): `.venv\Scripts\python tools\run_job.py new "D:\footage\dai.mp4" --split --hook`

## Bước 12 — Kiểu "Thể thao" theo video mẫu boxing `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`. Tạo job với một trận boxing / bóng đá, chọn kiểu dựng
   **Thể thao – bình luận & phân tích tình huống** (hoặc để AI tự chọn).
2. Mở draft trong CapCut, so với video mẫu:
   - Nền đen, video phóng to gần vuông (9:10) ở giữa, bám theo võ sĩ / cầu thủ; không có dòng tiêu đề.
   - Phụ đề chữ vàng viền đen, cụm rất ngắn (2–7 chữ) nhảy theo lời bình, nằm ở khoảng 2/3 khối video.
   - **Mũi tên xanh lá** chỉ vào găng / chân / bóng đúng lúc lời bình nhắc tới. Kiểm tra: mũi tên có hiện không
     (ký tự "→" trong font CapCut), **có xoay đúng hướng không** (ví dụ chỉ xuống-phải), có chỉ gần đúng chỗ không.
   - Replay quay chậm ở pha quyết định, chuyển cảnh mờ.
3. Nếu mũi tên xoay ngược chiều / không hiện / to nhỏ: chụp màn hình gửi Claude.

## Bước 11 — Bố cục mới theo video mẫu (4 dòng tiêu đề + khối 16:9) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`. Tạo job mới (hoặc job cũ bấm **🎬 Lập lại kế hoạch dựng** — cần AI viết
   4 dòng tiêu đề mới).
2. Mở draft trong CapCut, so với video mẫu:
   - Nền đen; video 16:9 tràn ngang ở giữa màn.
   - 2 dòng chữ lớn phía trên + 2 dòng phía dưới, hiện suốt video, mỗi dòng gần tràn chiều ngang.
   - Phụ đề thoại nằm trong khối video (mép dưới); nhãn chủ đề nhỏ góc trên phải khối video.
3. **Cỡ chữ tiêu đề** là ước lượng: nếu to quá (tràn ra ngoài) hoặc nhỏ quá, báo Claude; hoặc tự sửa
   `char_width_per_size` trong `config/layout.yaml` (to quá → tăng, ví dụ 0.0017 → 0.0022; nhỏ quá → giảm).
4. Muốn quay lại bố cục cũ (khối 4:3 / 1:1 + nền mờ): đổi `preset: four_titles` thành `preset: classic`.

## Bước 10 — Lỗi "Không thấy dự án mẫu CapCut" `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`.
2. Trang chủ → ô Kho tài nguyên → mở **🧩 Dự án mẫu CapCut**: dòng "đang dùng" cho biết tool đang lấy khuôn ở đâu.
   Danh sách chọn liệt kê mọi dự án CapCut trên máy. Chọn dự án mẫu của bạn (hoặc "Mẫu có sẵn trong tool") → **Lưu**.
3. Mở lại job bị lỗi → bấm **Chạy lại bước này**. Job phải chạy tiếp tới Xong.
4. Nếu dùng "Mẫu có sẵn trong tool": mở draft vừa tạo trong CapCut, kiểm tra mở được, chữ / âm thanh / clip đúng,
   xuất được video.

## Bước 9 — Nút "🔍 Quét tài nguyên" (CapCut + kho trên máy + Freesound CC0) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, rồi `.venv\Scripts\pip install -r requirements.txt`, đóng và mở lại `start.bat`.
2. **Lấy key Freesound (miễn phí, làm 1 lần):** đăng ký tài khoản ở https://freesound.org, mở
   https://freesound.org/apiv2/apply, điền tên ứng dụng bất kỳ (ví dụ "tooledit"), bấm tạo, copy **API key**.
   Ở trang chủ tool, mở **⚙️ Cài đặt Freesound**, dán key, bấm **Lưu** → hiện "✅ đã lưu key".
   (Key lưu ở `config/local.yaml` trên máy bạn, không đưa lên GitHub.)
3. Bấm **🔍 Quét tài nguyên** (để tick "Tải thêm cái còn thiếu từ internet"). Chờ vài chục giây.
   Trang kết quả hiện: số tài nguyên từ CapCut, số file trong kho máy, bảng "Tài nguyên cần thiết"
   (có sẵn / đã tải / còn thiếu), danh sách file vừa tải kèm link nguồn và giấy phép CC0.
4. Kiểm tra thư mục `assets\sfx\...` và `assets\music\...` trong thư mục tool có file .mp3 mới, và
   `assets\ledger.json` ghi nguồn từng file.
5. Nếu có job từng thiếu SFX/nhạc: bấm nút **🔁 Dựng lại draft job …** ở cuối trang kết quả, mở draft trong
   CapCut, nghe SFX / nhạc mới có ở đúng chỗ không.
6. Thử **➕ Thêm file âm thanh của bạn vào kho**: chọn loại, nhãn, file → "Đã thêm vào kho".

Lưu ý: nhạc/hiệu ứng **thư viện online của CapCut** không tải bằng code được — CapCut chỉ tải khi bạn dùng
thử chúng trong app. Tool tự thấy mọi thứ bạn đã dùng trong bất kỳ dự án CapCut nào.

## Bước 8 — Mọi thao tác trên giao diện, kho tự lấy từ CapCut, dựng sinh động hơn `[CẦN KIỂM TRA TRÊN MÁY]`

1. Cập nhật: mở PowerShell trong thư mục tool, chạy `git pull` rồi `.venv\Scripts\pip install -r requirements.txt`.
   Đóng cửa sổ `start.bat` cũ (nếu đang mở) rồi mở lại `start.bat`.
2. **Kho tài nguyên tự động**: ở trang chủ, ô "📚 Kho tài nguyên" hiện số nhạc / SFX / hiệu ứng / chuyển cảnh / sticker
   mà tool tự quét được từ **tất cả dự án CapCut** trên máy. Không cần dự án `bo_suu_tap_nhac` nữa.
   Muốn kho nhiều hơn: mở CapCut, thêm vài bài nhạc, SFX, hiệu ứng, sticker vào một dự án bất kỳ, lưu, đóng CapCut,
   tải lại trang chủ → số phải tăng. (Chỉ tính những thứ CapCut đã tải về máy.)
3. Tạo job mới có tick **Có hook**. Tới bước **🎙️ Thu voice hook**: bấm **Chọn tệp** chọn file voice (wav/mp3/m4a) →
   **Tải lên và dựng tiếp**. Không phải chép file vào thư mục nào.
4. Khi job **✅ Xong**: kiểm tra có nút **🏠 Về trang chủ** (trên cùng và trong ô "🛠️ Thao tác"), và các nút:
   - **🔁 Dựng lại draft** — đóng CapCut trước khi bấm; draft được ghi đè.
   - **🎬 Lập lại kế hoạch dựng** — AI lập kế hoạch mới rồi dựng lại.
   - **🎣 Chọn hook khác** — quay lại bảng chọn hook; voice cũ đổi tên thành `video01_hook_cu.*`, cần tải voice mới.
   - **✍️ Viết hook mới** — AI viết 3 phương án mới.
   - **🗑️ Xóa job** — xóa dữ liệu job (draft trong CapCut vẫn giữ).
5. **Dựng sinh động hơn**: mở draft trong CapCut, xem có thêm hiệu ứng hình ở điểm nhấn, sticker, chuyển cảnh giữa
   các đoạn, filter màu, chữ nhấn nhiều màu có animation. Các thứ này lấy từ kho ở bước 2, nên kho càng nhiều thì
   bản dựng càng phong phú. Báo lại cho Claude chỗ nào quá dày / quá nhạt.

## Bước 7 — Giao diện mới, 6 kiểu dựng, kho nhạc/SFX `[CẦN KIỂM TRA TRÊN MÁY]`

1. Cập nhật: `git pull` rồi `.venv\Scripts\pip install -r requirements.txt`. Mở `start.bat`.
2. Bấm **📂 Chọn file…**: hộp thoại Windows hiện ra (có thể nằm sau cửa sổ trình duyệt), chọn video.
3. Chọn **Kiểu dựng**: "AI tự chọn" hoặc một trong: Cắt nhanh (TikTok), Podcast/phỏng vấn, Thể thao – bình luận &
   phân tích tình huống (có replay quay chậm + chữ phân tích), Vlog, Giải trí/show, テロップ Nhật.
4. **Kho nhạc/SFX để đạo diễn chọn nhạc hợp từng video:**
   - Trong CapCut tạo dự án mới tên **`bo_suu_tap_nhac`**. Kéo vào timeline 10–30 bài nhạc nhiều tâm trạng khác nhau
     (vui, hype/thể thao, chill/lofi, cảm động, hồi hộp, hài...) và 10–20 hiệu ứng âm thanh (pop, whoosh, ding, boom,
     tiếng cười...). Không cần sắp xếp. Lưu, đóng CapCut.
   - Trang chủ, ô **Kho tài nguyên** sẽ hiện số nhạc / SFX đọc được.
   - (Tùy chọn) Ghi tâm trạng từng bài trong `config\capcut_labels.yaml` mục `moods` (music_id lấy bằng
     `.venv\Scripts\python tools\inspect_draft.py <thư mục dự án bo_suu_tap_nhac>`), ghi bài Commercial ở
     `commercial_music_ids`.
5. Dựng thử một video thể thao (boxing/bóng đá/bóng chày có bình luận) với kiểu "Thể thao" hoặc "AI tự chọn".

## Bước 6 — Giao diện web (start.bat) `[CẦN KIỂM TRA TRÊN MÁY]`

```powershell
cd $HOME\Documents\tooledit
git pull
.venv\Scripts\pip install -r requirements.txt
```

Sau đó nhấp đúp **`start.bat`**: trình duyệt mở http://127.0.0.1:8765 (cửa sổ đen phải để mở; đóng nó là tắt tool).
1. Trang chủ: dán đường dẫn footage, chọn tùy chọn, bấm **Bắt đầu**. Trang job tự làm mới khi đang chạy.
2. Khi dừng ở **Chọn hook**: chọn một phương án, bấm **Chọn hook này**.
3. Khi dừng ở **Thu voice hook**: thả file vào thư mục ghi trên trang, bấm **Đã thả file, tiếp tục**.
4. Khi **Xong**: trang hiện tên draft CapCut, caption + hashtag, ghi chú editor, bảng tài nguyên cần bổ sung.
   Nhớ đóng CapCut trước khi tool ghi draft.

## Bước 5c — Dựng lại job cũ với nền mờ + chữ hook to, và xuất caption `[CẦN KIỂM TRA TRÊN MÁY]`

```powershell
cd $HOME\Documents\tooledit
git pull
.venv\Scripts\python tools\run_job.py continue 20260925_02 --redo write
```

Không hỏi lại đạo diễn cho hook/kế hoạch (dùng kết quả cũ); chỉ ghi lại draft và hỏi thêm một lượt để viết
caption. Kiểm tra trong CapCut: phần trống trên/dưới khối 4:3 là **bản mờ của chính video** (không còn đen),
chữ hook to hơn và rung. Mở `jobs\20260925_02\deliver\video01_captions.txt` xem caption + hashtag.

## Bước 5b — Chọn cỡ và kiểu chữ hook (dự án thử chữ) `[CẦN KIỂM TRA TRÊN MÁY]`

Phản hồi lần chạy 1: chữ hook quá nhỏ (cỡ 16, gần bằng cỡ mặc định 15) và chưa được trang trí.
Dự án `test_chu_v1`: giây 0–6 cùng một câu ở cỡ 15/20/25/30/40/50; giây 6–12 năm kiểu A–E ở cỡ 30
(A vàng viền đen dày; B chữ trắng trên khung đỏ; C chữ đen trên khung vàng bo tròn; D trắng viền đen rất dày +
hiệu ứng vào và rung; E đỏ viền trắng + hiệu ứng vào).

```powershell
Expand-Archive -Path "$HOME\Downloads\test_chu_v1.zip" -DestinationPath "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft"
```

(Hoặc tự tạo: `.venv\Scripts\python tools\build_text_test.py`.) Báo lại: cỡ nào vừa cho chữ hook, cỡ nào cho
phụ đề, kiểu nào đẹp nhất, chữ có bị tràn khỏi khung không.

## Bước 5 — Dựng trọn một video từ footage thật (Giai đoạn 1) `[CẦN KIỂM TRA TRÊN MÁY]`

**Lần chạy 1 (2026-09-25, job 20260925_02):** chạy trọn quy trình không lỗi. Hiểu nội dung 28s, viết hook
(3 phương án đúng yêu cầu: khác kiểu nhau, có mốc nguồn, tránh chuyện 八百長), chọn phương án 2, kế hoạch dựng
39s; ghi draft `test_20260925_02_video01` dài 106.0 giây; 6 tài nguyên cần bổ sung. Còn chờ: mở trong CapCut
và xuất video.

Quy trình: phân tích → đạo diễn hiểu nội dung → 3 phương án hook → chọn hook → thu voice → kế hoạch dựng →
ghi draft CapCut (phong cách tiktok_retention). Dùng lại job 20260925_02 đã phân tích (không phân tích lại):

```powershell
cd $HOME\Documents\tooledit
git pull
.venv\Scripts\python tools\run_job.py continue 20260925_02 --hook --client test
```

1. Tool hỏi đạo diễn (hiểu nội dung, rồi viết 3 hook) và **dừng lại**, in bảng 3 phương án hook.
2. Chọn một phương án, ví dụ số 2:

   ```powershell
   .venv\Scripts\python tools\run_job.py continue 20260925_02 --choose 1=2
   ```

   Tool xuất `jobs\20260925_02\hook_scripts.txt` (câu cần thu) và dừng chờ voice.
3. Thu câu hook, lưu thành `jobs\20260925_02\voice\video01_hook.wav` (hoặc .mp3/.m4a). Muốn thử nhanh có
   thể chép tạm một file âm thanh bất kỳ đổi tên như vậy.
4. **Đóng CapCut**, rồi chạy tiếp:

   ```powershell
   .venv\Scripts\python tools\run_job.py continue 20260925_02
   ```

   Đạo diễn lập kế hoạch dựng, tool ghi draft `test_20260925_02_video01` vào thư mục draft của CapCut.
5. Mở CapCut, mở draft đó. Kiểm tra: hook đầu video (voice + chữ lớn dải trên), footage 16:9 thành khối 4:3
   giữa màn và bám theo người nói, phụ đề tiếng Nhật ở dải dưới (tên đã sửa đúng 貴闘力/曙), chữ nhấn,
   zoom, nhạc Keep It High nhỏ lại khi có thoại, tổng thời lượng 60–150 giây. Thử xuất video.
6. Gửi lại: toàn bộ chữ in ra trong PowerShell + nhận xét từng mục + ảnh chụp nếu có chỗ sai.

Ghi chú: `jobs\20260925_02\missing_assets.json` liệt kê SFX đạo diễn muốn dùng nhưng chưa có trong kho
(Giai đoạn 1 chưa có kho SFX). Nếu tool báo không thấy dự án mẫu, sửa `template_name` trong
`config\capcut.yaml` cho đúng tên dự án mẫu trong CapCut.

## Bước 2b — Demo v2: thêm âm thanh local (ĐÃ XONG: mở được, nghe kkk2.wav, xuất OK)

`demo_tool_v2` giống demo v1, thêm file `C:\Users\balha\Downloads\kkk2.wav` (lấy từ mẫu lần 3) ở giây 0–4
trên một track âm thanh riêng. File đó phải còn nguyên chỗ cũ.

1. Đóng hẳn CapCut. Giải nén:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\demo_tool_v2.zip" -DestinationPath "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft"
   ```

2. Mở `demo_tool_v2`: giây 0–4 phải nghe **kkk2.wav** chồng lên nhạc; track âm thanh không báo "thiếu file".
3. Xuất thử video.

## Bước 4 — Chạy thử đạo diễn AI (Claude Code)

**Kết quả lần 1 (2026-09-25, job 20260925_02):** chạy được sau khi đăng nhập Claude Code, mất 24 giây.
Tóm tắt đúng nội dung; đề xuất jp_telop có lý do; 7 khoảnh khắc có mốc giây; tự sửa tên nhận dạng sai
(高藤力 → 貴闘力, 明物 → 曙) dựa trên chữ trong khung hình; phát hiện footage có sẵn テロップ; tự nêu lưu ý
không được viết câu đùa 八百長 như sự thật. Sau đó đã thêm các trường riêng cho những nhận định này.


Cần: đã cài và đăng nhập Claude Code (docs/SETUP_WINDOWS.md mục 5), đã có một job phân tích xong.

```powershell
cd $HOME\Documents\tooledit
git pull
.venv\Scripts\python tools\director_understand.py 20260925_02
```

Tool chép 12 khung hình vào `%LOCALAPPDATA%\tooledit\director\understand\` (ngoài repo, để Claude Code
không đọc CLAUDE.md của dự án), rồi gọi `claude -p` với khuôn JSON. Gửi lại phần "ĐẠO DIỄN NHẬN XÉT"
và nhận xét: tóm tắt có đúng nội dung không, phong cách đề xuất có hợp lý không, các mốc giây có đúng không.

## Bước 3 — Cài đặt và chạy thử phân tích footage

**Kết quả lần 1 (2026-09-25):** video 1920x1080, 173.8 giây, tiếng Nhật. Chạy trên `cuda` (GTX 1080 Ti,
large-v3, int8_float32): làm sạch âm thanh 8s, nhận dạng thoại ~45s, dò cảnh ~32s (7 cảnh), trích 40 khung
~15s, dò mặt ~130s → tổng 230s. Nhận đúng tiếng Nhật, 38 câu; tên riêng có chỗ nghe nhầm.
Sau đó đã tối ưu dò mặt (đọc tuần tự + thu nhỏ khung) → cần chạy lại để đo `[CẦN KIỂM TRA TRÊN MÁY]`.


1. Làm theo `docs/SETUP_WINDOWS.md` (cài Python, FFmpeg, thư viện, GPU).
2. Chọn một footage thật ngắn (1–3 phút, có người nói tiếng Hàn/Nhật/Anh; footage của chính anh/chị
   hoặc đã được khách đồng ý). Chạy:

   ```powershell
   cd $HOME\Documents\tooledit
   .venv\Scripts\python tools\analyze_footage.py "D:\duong\dan\video.mp4"
   ```

3. Chép phần "TÓM TẮT" in ra gửi Claude, kèm nhận xét: ngôn ngữ đúng không, câu thoại có đúng
   không, chạy mất bao lâu, chạy trên `cuda` hay `cpu`.
4. Mở thư mục `jobs\<job_id>\analysis\frames` xem ảnh có đúng cảnh không.
   **Không gửi/commit thư mục jobs** (có footage của khách).

## Bước 2 — Mở draft demo do tool tạo (ĐÃ XONG: mở được, đạt hết, xuất video OK)

`demo_tool_v1` được tạo hoàn toàn bằng code (`tools/build_demo_draft.py`) từ dự án mẫu, dùng lại
các clip có sẵn trong mẫu (j1/final.mp4, j2/final.mp4, clips/02.mp4). Các clip đó phải còn nguyên chỗ cũ.

1. **Đóng hẳn CapCut.** Xóa các draft thăm dò cũ (`capcut_template_probe*`) nếu còn.
2. Giải nén `demo_tool_v1.zip` vào thư mục draft:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\demo_tool_v1.zip" -DestinationPath "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft"
   ```

3. Mở CapCut → dự án `demo_tool_v1` (dài 15 giây). Kiểm tra từng mục, ghi Đạt/Không đạt:

   | Giây | Cần thấy |
   |---|---|
   | 0–4 | Clip dọc **zoom chậm** vào; chữ vàng viền đen "TEST 1" ở trên có **hiệu ứng vào/rung/ra**; phụ đề trắng viền đen tiếng Hàn rồi tiếng Nhật ở dưới; hiệu ứng "Lệch flash" giây 0–1; sticker emoji giây 2–4 |
   | ~4 | **Chuyển cảnh** "Lấp lánh mùa đông" |
   | 4–8 | Clip ngang thành **khối 4:3 nằm giữa**, không méo; filter "Hè thư thái"; chữ "TEST 2" ở dải trên, phụ đề tiếng Anh ở dải dưới |
   | 8–11 | Clip ngang thành **khối 1:1 (vuông)**, lấy phần lệch trái; chữ "TEST 3" ở dải trên |
   | 11–15 | Clip dọc phóng to, **lia từ trái sang phải** |
   | cả video | Nhạc "Keep It High": to ở 0–4s, **nhỏ hẳn từ giây 4** |

4. Thử **xuất video** (Export) để chắc chắn xuất được.
5. Báo lại mục nào không đạt (chụp màn hình càng tốt).

## Bước 1b — Thử vòng 2 (ĐÃ XONG: cả probe2 và probe3 đều hiện `TRONG_CONTENT`)

Kết quả vòng 1: draft thăm dò vẫn hiện chữ gốc `地獄の合図は深`. Nghĩa là CapCut không đọc 4 file
timeline kia, mà đọc bản thứ 5 `Timelines\<id>\attachment\patch\mini_draft.json`.

1. **Đóng hẳn CapCut.** Trong thư mục draft, xóa draft thăm dò cũ `capcut_template_probe` (nếu còn).
2. Giải nén `capcut_probe_vong2.zip` vào thư mục draft:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\capcut_probe_vong2.zip" -DestinationPath "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft"
   ```

3. Mở CapCut, lần lượt mở 2 dự án và xem chữ ở giây 0–3:
   - `capcut_template_probe2`: mong đợi hiện `MINI_DRAFT`.
   - `capcut_template_probe3` (đã xóa mini_draft.json): hiện nhãn nào (`GOC_CONTENT`, `GOC_TEMPLATE2`,
     `TRONG_CONTENT`, `TRONG_TEMPLATE2`), chữ gốc, hay báo lỗi?
4. Báo lại hai kết quả.

## Bước 1 — CapCut 9.5.0 đọc bản timeline nào? `[CẦN KIỂM TRA TRÊN MÁY]`

Draft 9.5.0 có 4 bản timeline giống nhau. Draft thăm dò `capcut_template_probe` là bản sao của mẫu.
Trong đó, lớp chữ đầu tiên (giây 0–3) ở mỗi bản mang một nhãn khác nhau.

1. **Đóng hẳn CapCut.**
2. Giải nén `capcut_template_probe.zip` (Claude gửi trong chat) vào thư mục draft:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\capcut_template_probe.zip" -DestinationPath "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft"
   ```

   Nếu có Python và repo, có thể tự tạo draft thăm dò:

   ```powershell
   python tools\make_probe_draft.py "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft\<thư_mục_mẫu>"
   ```

3. Mở CapCut. Draft `capcut_template_probe` có hiện trong danh sách không? Mở nó ra được không?
4. Xem lớp chữ ở đầu video (giây 0–3). Nó ghi chữ gì?
   - `GOC_CONTENT` → CapCut đọc `draft_content.json` ở gốc
   - `GOC_TEMPLATE2` → đọc `template-2.tmp` ở gốc
   - `TRONG_CONTENT` → đọc `Timelines\<id>\draft_content.json`
   - `TRONG_TEMPLATE2` → đọc `Timelines\<id>\template-2.tmp`
   - vẫn là chữ cũ `地獄の合図は深`, hoặc báo lỗi, hoặc không mở được → chụp màn hình gửi lại
5. Báo lại kết quả, rồi xóa draft thăm dò trong CapCut.

## Bước 0 — Tạo và gửi dự án CapCut mẫu (cho báo cáo tương thích)

1. Mở **CapCut 9.5.0**, tạo dự án mới, tỷ lệ 9:16. Thêm:
   - 2–3 clip test ngắn (quay bất kỳ, **không dùng footage của khách**);
   - 1 lớp chữ (gõ thử cả tiếng Hàn/Nhật nếu được);
   - 1 hiệu ứng, 1 chuyển cảnh giữa 2 clip, 1 filter, 1 sticker;
   - 1 âm thanh hoặc bài nhạc **từ thư viện của CapCut**.
2. Đặt tên dự án là `capcut_template`, lưu, rồi **đóng hẳn CapCut**.
3. Mở PowerShell, xem thư mục draft:

   ```powershell
   explorer "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft"
   ```

   (Nếu không thấy, trong CapCut vào Cài đặt → xem "Vị trí lưu bản nháp" và báo lại đường dẫn.)
4. Chép thư mục `capcut_template` vào repo tại `samples\capcut_template\`.
   `.gitignore` đã chặn video/âm thanh/ảnh, chỉ các file JSON được commit.
5. (Không bắt buộc) chạy thử script kiểm tra, cần Python 3.11+:

   ```powershell
   cd <thư mục repo>
   python tools\inspect_draft.py samples\capcut_template
   ```

6. (Không bắt buộc) nếu có Node.js:

   ```powershell
   npx capcut-cli@0.26.0 version samples\capcut_template
   npx capcut-cli@0.26.0 diagnose samples\capcut_template -H
   ```

   Chép toàn bộ kết quả gửi lại.
7. Commit và push thư mục mẫu (hoặc tải file lên cho Claude), xem mục dưới.

### Cách đưa dự án mẫu lên GitHub

**Cách 1 (dễ nhất):** nén thư mục dự án thành `.zip` (chuột phải → Nén thành tệp ZIP), rồi kéo thả
file zip vào khung chat với Claude. Claude sẽ tự bỏ video/ảnh và commit phần JSON.

**Cách 2 (dùng git trong PowerShell):**

```powershell
# Chỉ làm 1 lần: cài git và khai báo tên
winget install --id Git.Git -e
# (đóng rồi mở lại PowerShell sau khi cài)
git config --global user.name "Ten cua ban"
git config --global user.email "email-github-cua-ban@example.com"

# Tải repo về và chuyển sang nhánh làm việc
cd $HOME\Documents
git clone https://github.com/phamvanson12398/tooledit.git
cd tooledit
git checkout claude/new-session-lqnr47
git pull

# Chép dự án mẫu vào repo, BỎ QUA video/âm thanh/ảnh
robocopy "$env:LOCALAPPDATA\CapCut\User Data\Projects\com.lveditor.draft\capcut_template" "samples\capcut_template" /E /XF *.mp4 *.mov *.mkv *.wav *.mp3 *.m4a *.aac *.jpg *.jpeg *.png *.webp

# Kiểm tra: danh sách chỉ nên có file .json / .tmp / nhỏ, KHÔNG có video
git status

git add samples
git commit -m "Thêm dự án CapCut 9.5.0 mẫu"
git push
```

Lần đầu `git push` sẽ mở trình duyệt để đăng nhập GitHub, bấm đồng ý là xong.
