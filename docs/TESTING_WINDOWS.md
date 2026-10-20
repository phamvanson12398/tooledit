# Hướng dẫn kiểm tra trên máy Windows

## Bước 118 — Bán content: thời lượng "AI tự chọn" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. **💰 Bán content** → ô **⏱️ Thời lượng video** chọn **🤖 AI tự chọn theo nội dung (luôn trên 60 giây)** → Bắt đầu.
3. Đầu trang job ghi "🤖 AI tự chọn độ dài". Xong: video dài hơn 60 giây, dài / ngắn tùy nội dung (tối đa ~2 phút,
   chỉnh `auto_s` trong `config\sell.yaml`).

## Bước 117 — Bán content: nửa thuyết minh, nửa tiếng gốc `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Tạo job **💰 Bán content** với video có lời nói / phản ứng hay (vd khách khen món, câu nói hài).
3. Trang voice: ở phần dàn ý có dòng **"🔊 Giữ tiếng gốc (không cần đọc): sau câu N — giây…"** nếu AI chọn giữ đoạn nào
   (AI tự quyết — video không có đoạn đắt thì không có dòng này). Chỉ cần đọc các câu như thường.
4. Mở CapCut: ở đúng chỗ đó video phát nguyên hình + tiếng gốc (các đoạn khác tắt tiếng gốc), có phụ đề dịch lời gốc,
   nhạc nền nhỏ lại; giọng đọc dẫn vào trước và nói tiếp sau, không lặp lại điều nhân vật vừa nói.
5. Tiếng gốc to / nhỏ quá: chỉnh `orig_audio.volume` trong `config\sell.yaml`; muốn tắt hẳn kiểu này: `enabled: false`.

## Bước 116 — Chế độ mới "▶️ Bán content YouTube" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. Trang chủ → chọn MỘT video nguồn (dưới 1 tiếng 30 phút) → thẻ **▶️ Bán content YouTube** → ngôn ngữ → thời lượng
   (**🤖 AI tự chọn** hoặc 10 / 12 / 15 / 18 / 20 phút) → (tùy chọn) tick **⏸️ Dừng cho tôi duyệt dàn ý** → giọng đọc →
   Bắt đầu.
3. Video nguồn dài hơn 90 phút: job báo lỗi ngay ở bước phân tích (không phân tích phí).
4. Có tick dừng: trang job hiện **▶️ Duyệt dàn ý video YouTube** (góc làm, 3 tiêu đề, các chương + thời lượng). Thử góp ý
   (vd "bỏ chương 4, thêm chương về giá cả") → **🔁 Lập lại dàn ý** (nhanh, không xem lại video) → **✅ Duyệt**.
   Không tick: job tự chạy tới bước chờ voice.
5. Nhật ký: "AI viết lời N chương (song song)", "✍️ Xong lời chương k/N…". Trang voice hiện cả bài (đọc liền một file hoặc
   OmniVoice / giọng Voice Studio tự đọc — bài dài nên đọc mất vài phút tới vài chục phút).
6. Xong: mở dự án CapCut — dài đúng thời lượng (± voice thật), có phụ đề, tên chương hiện giữa màn đầu mỗi chương, cảnh
   khớp lời, nhạc nền + tiếng động thưa. Mở `jobs\<mã job>\deliver\youtube_video01.txt`: tiêu đề, mô tả có mốc chương
   (00:00 …) khớp với video, tag, ý tưởng ảnh bìa.
7. Kiểm tra lời không nhắc TikTok, có thể có câu kêu gọi đăng ký kênh ở giữa / cuối.

## Bước 115 — Thêm tiếng Đức `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. Ô **🌐 Ngôn ngữ video mới** có thêm **Đổi sang tiếng Đức (Deutsch)**.
3. Thử một job ngắn (vd **💰 Bán content** hoặc **🌐 Đổi ngôn ngữ**) chọn tiếng Đức:
   - kịch bản trên trang voice viết bằng tiếng Đức, nghĩa tiếng Việt bên dưới;
   - phụ đề, tiêu đề, chữ nhấn, caption bằng tiếng Đức.
4. Cho **🤖 OmniVoice** đọc (hoặc giọng Voice Studio): nghe xem đọc tiếng Đức có chuẩn không — tool gửi mã ngôn ngữ
   `de` cho OmniVoice; nếu đọc sai giọng / sai ngôn ngữ thì báo mình.
5. Sau lần thu voice đầu, tool tự đo tốc độ đọc thật của giọng Đức (lần sau viết bài vừa giọng hơn).

## Bước 114 — Bán content: phụ đề ngôn ngữ đích luôn có (nền tối che phụ đề cũ) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Job Bán content đã xong mà thiếu phụ đề: trang job → 🛠️ **🔁 Dựng lại draft** (không phải hỏi lại AI, voice giữ nguyên).
3. Mở CapCut: có phụ đề ngôn ngữ đích (Hàn / Nhật / Anh) ở dưới; video gốc có phụ đề in sẵn thì phụ đề mới có nền đen mờ
   che lên phụ đề cũ. Phụ đề tiếng Việt (chữ vàng nhỏ) vẫn như trước — tắt ở trang job trước khi xuất video đăng.
4. Nền chưa che hết phụ đề cũ: tăng `pad_w` / `pad_h` (hoặc `alpha` lên 1 = đen đặc) trong `config\sell.yaml → sub_cover`
   rồi dựng lại draft.

## Bước 113 — Kho cảnh chung (cảnh đẹp từ "Ý tưởng từ video dài" bù cho Bán content / Ý tưởng) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Chạy một job **💡 Ý tưởng từ video dài** MỚI tới ✅ Xong (job đã xong trước bản cập nhật này chưa có cảnh trong kho).
   Nhật ký cuối job: "📦 Đã lưu N cảnh đẹp vào kho cảnh chung". Mở thư mục `library\clips` trong thư mục tool:
   có các file `L1_<mã job>.mp4`… — mở xem vài file: cảnh đẹp, không có chữ / logo, dài 2–12 giây.
3. Tạo job **💰 Bán content** với video ngắn CÙNG kiểu khung (ngang thì ngang, dọc thì dọc) và cùng chủ đề (vd video
   ngắn về đồ ăn Nhật, kho có cảnh ẩm thực). Nhật ký: "Kho cảnh chung: … cảnh cùng khung AI được bù…".
4. Sau khi dựng: nhật ký "Dùng … cảnh từ kho cảnh chung: L…" (nếu AI thấy cần). Mở CapCut: cảnh kho phải ĐÚNG thứ lời đang
   nói; thư mục `media` của dự án có file `L…mp4` (đóng gói đủ, xóa kho cũng không hỏng dự án).
5. Video gốc đủ cảnh / kho không có cảnh hợp → không dùng cảnh kho, dựng như cũ (làm chậm nhẹ / dùng lại cảnh lật ngang).
6. Đổi giới hạn trong `config\library.yaml` nếu cần: `max_gb` (dung lượng kho), `max_uses` (mỗi cảnh dùng tối đa mấy
   video), `max_share` (cảnh kho chiếm tối đa bao nhiêu % video), `enabled: false` để tắt hẳn.

## Bước 112 — Chế độ mới "💡 Ý tưởng từ video dài" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. Trang chủ → chọn MỘT video dài (vd vlog du lịch 20–60 phút) → thẻ **💡 Ý tưởng từ video dài** → ngôn ngữ (Hàn /
   Nhật / Anh) → (không bắt buộc) ô **Gợi ý chủ đề / khán giả**, vd "khán giả Hàn thích du lịch Nhật" → thời lượng
   (mặc định 65 giây) → giọng đọc (giọng Voice Studio để tự đọc, hoặc tự thu) → Bắt đầu.
3. Phân tích video dài sẽ lâu hơn bình thường (nhận dạng lời + trích ~600 khung). Bước "AI xem kho cảnh + nghĩ ý tưởng":
   nhật ký báo "AI xem video (… phút) theo N phần", rồi "Danh mục cảnh phần k/N: … cảnh" (các phần chạy song song).
4. Job dừng ở trang **💡 Chọn ý tưởng muốn làm**: kiểm tra
   - có ~8 ý tưởng, mỗi ý tưởng có tên, góc kể, câu mở đầu, bấm "🎞️ … cảnh" xem danh sách cảnh — mô tả cảnh có ĐÚNG với
     video không;
   - ý tưởng thiếu cảnh nằm ở mục "bị bỏ" kèm lý do.
5. Thử ô góp ý (vd "thêm ý tưởng về ẩm thực") → **💡 Nghĩ lại ý tưởng**: lần này nhanh (không xem lại video).
6. Tick 2 ý tưởng → **✅ Làm các ý tưởng đã tick** → mỗi ý tưởng một kịch bản → đọc voice (hoặc OmniVoice tự đọc) → job
   ✅ Xong với 2 dự án CapCut `…_video01`, `…_video02`.
7. Mở CapCut từng dự án: lời đọc nói gì thì hình thấy đúng thứ đó; video dài > 60 giây; 2 short ít trùng cảnh; hình
   không lấy lung tung các đoạn không liên quan của video dài. Có lời nói sai sự thật (tên, số liệu bịa) thì ghi lại
   gửi mình.

## Bước 111 — Bán content: thêm tiếng "click" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Thả vài file tiếng click vào `assets\sfx\click\` (hoặc dùng thử một tiếng click trong thư viện âm thanh CapCut ở bất kỳ
   dự án nào để tool tự quét được).
3. Job Bán content có sẵn: trang job → 🛠️ **🔁 Dựng lại draft** (không phải hỏi lại AI); job mới thì chạy như thường.
4. Mở CapCut: track tiếng động có whoosh → click → swoosh luân phiên khi đổi câu, và click lúc chữ nhấn bật lên (chỗ
   không có tiếng khác). Thiếu tiếng click thì danh sách "cần bổ sung" của job ghi "click".

## Bước 110 — Bán content: giọng Voice Studio tự đọc, nhiều bản, chữ nhấn + tiếng động, không đè chữ, AV1 `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. (Một lần) Tab **🎙️ Voice Studio** → lưu một giọng mẫu (tick xác nhận quyền) hoặc một giọng mô tả.
3. Trang chủ → **💰 Bán content** → chọn video (vd video game tiếng Nhật) → ngôn ngữ → **🎞️ Số bản: 2** →
   **🎙️ Giọng đọc: giọng vừa lưu** → Bắt đầu. Không cần làm gì thêm:
   - nhật ký: "🎙️ Giọng Voice Studio … OmniVoice tự đọc cả bài", nếu voice ngắn thì "tự viết dài thêm … (một lần)";
   - job tự tới ✅ Xong với 2 dự án CapCut `…_video01`, `…_video02`.
4. Mở 2 dự án trong CapCut:
   - 2 bản có câu mở đầu, tiêu đề, thứ tự cảnh KHÁC nhau;
   - có chữ to giữa màn (chữ nhấn) ở nhiều câu, tiếng "pop" ở đầu, tiếng whoosh khi đổi câu (track âm thanh riêng);
   - video game có sẵn tiêu đề / phụ đề Nhật in trên hình → tool KHÔNG thêm tiêu đề / phụ đề đè lên nữa.
5. Video AV1 (tải từ YouTube): nhật ký "Video gốc nén bằng AV1 … đổi sang H.264"; CapCut mở dự án phát hình bình thường
   (thư mục `media` của dự án chứa `capcut_src_00.mp4`).
6. Không thấy tiếng động: kho chưa có SFX whoosh / pop → thả file vào `assets\sfx\whoosh\`, `assets\sfx\pop\` (hoặc
   dùng thử các tiếng đó trong CapCut một lần để tool tự quét được).

## Bước 109 — Sửa "Lỗi ở bước plan: division by zero" (Bán content, video cắt cảnh dày) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Mở job đang báo lỗi → bấm **Chạy lại bước này** (không cần tạo job mới, phần phân tích giữ nguyên).
3. Bước "AI viết kịch bản mới + chọn cảnh" phải chạy qua, tới trang chờ đọc cả bài.
4. Vẫn lỗi: chụp nhật ký (log) gửi mình.

## Bước 108 — Tab "🎙️ Voice Studio" (OmniVoice như tool TTS + thư viện giọng mẫu) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat` (cần OmniVoice đã cài như Bước 95 — 🔎 Kiểm tra OmniVoice phải ✅).
2. Thanh trên cùng có 2 nút **🎞️ Dựng video** / **🎙️ Voice Studio** → bấm Voice Studio.
3. Mở **➕ Giọng mẫu mới**: chọn file giọng 3–10 giây, đặt tên, gõ lời đọc trong file (hoặc để trống cho OmniVoice tự
   nhận dạng — lần đầu sẽ tải thêm model nhận dạng, hơi lâu), tick **Tôi xác nhận có quyền dùng giọng mẫu này**.
4. Gõ chữ cần đọc, chọn ngôn ngữ → **🔊 Đọc**. Ô ⏳ Tiến độ hiện từng bước; xong tự tải lại trang, file nằm ở **🎧 File
   đã đọc** (nghe thử / ⬇️ tải). File cũng ở thư mục `studio\outputs` trong tool.
5. Giọng vừa dùng nằm trong **📚 Thư viện giọng mẫu** → lần sau bấm **Dùng** (hoặc chọn ở ô 1️⃣) là đọc ngay, không phải
   tải file lại. Lần đọc thứ 2 với cùng giọng phải nhanh hơn (đã lưu prompt.pt).
6. Thử **⚙️ 3️⃣ Thông số**: tốc độ 1.2, seed 42 → đọc 2 lần cùng chữ → 2 file phải giống nhau; tick "Lưu các thông số
   này làm mặc định" → mở lại trang thấy giữ nguyên.
7. Thử **📝 Mô tả giọng** (vd `female, young adult, high pitch`) không cần file mẫu; tick "Lưu mô tả này vào thư viện".
8. Lỗi đỏ ❌ ở ô Tiến độ: chụp gửi mình (kèm dòng INFO phía trên).

## Bước 107 — Bán content: voice đủ dài + viết theo phụ đề trên hình `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Tạo job **mới** (job cũ đã phân tích với ít khung hình) với video có **phụ đề in trên hình**:
   - nhật ký bước phân tích: trích khoảng 60–70 khung (mỗi giây một khung);
   - trang voice: kịch bản phải có đủ các ý của phụ đề gốc, đúng thứ tự (đối chiếu bằng dòng 🇻🇳).
3. Thử với video **không có phụ đề**: kịch bản tả theo hình ảnh, đủ chi tiết.
4. Đọc cả bài như bình thường. Nếu voice ngắn hơn ~57 giây, job **dừng ở trang voice** với khung ⚠️ "Voice mới dài …s":
   - bấm **📏 Viết dài thêm cho đủ thời lượng** → AI viết lại dài hơn đúng theo tốc độ giọng bạn vừa đọc → đọc lại;
   - hoặc **Vẫn dựng với voice này** nếu chấp nhận phần cuối chỉ có hình + nhạc.
5. Mở CapCut: track voice phải kéo gần hết chiều dài video (không còn nửa sau chỉ có nhạc như ảnh bạn gửi).
6. Từ lần thứ 2 trở đi, tool đã nhớ tốc độ giọng bạn → kịch bản viết ra đủ dài ngay, ít khi phải bấm 📏.

## Bước 106 — Bán content: có lại ô chọn video, bỏ ô định hướng (AI tự viết theo nội dung gốc) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. Bấm thẻ **💰 Bán content**: bước 1 phải có ô **Chọn video** + nút **📂 Chọn file…**; bước 2 không còn ô "Định hướng nội
   dung", chỉ còn ngôn ngữ + thời lượng.
3. Chọn video ~1 phút → Bắt đầu. Ở trang voice, đọc dàn ý (📖): dòng đầu ghi "Góc kể: …" do AI tự chọn theo video. Kiểm
   tra kịch bản đúng với nội dung video, không bịa tên quán / giá / địa chỉ mà video không có.

## Bước 105 — Chế độ "💰 Bán content" + sửa lỗi "vượt quá độ dài file" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. (Nên làm) Thả vài file nhạc nền vào `assets\music\` — chỉ nhạc file mới được chép vào dự án CapCut. Không có thì tool
   dùng nhạc thư viện CapCut (CapCut tự tải khi mở) và ghi chú trong nhật ký.
3. Trang chủ → chọn video ~55–60 giây → thẻ **💰 Bán content** → chọn ngôn ngữ giọng đọc → gõ **🎯 Định hướng nội dung**
   (vd sản phẩm, điểm muốn nhấn, giá / địa chỉ thật, có cần kêu gọi follow / mua không) → thời lượng (mặc định 65 giây)
   → 🚀 Bắt đầu dựng.
4. Chờ tới bước "Chờ bạn đọc cả bài": kiểm tra
   - câu đầu là câu mở thu hút, nội dung mạch lạc, câu kêu gọi hành động (nếu có) nằm cuối;
   - chữ toàn bằng ngôn ngữ đã chọn, không có điều video / định hướng không nói.
   Chưa ưng → gõ góp ý → **✍️ Viết lại theo góp ý**.
5. Đọc cả bài vào MỘT file (nghỉ ~1 giây giữa các câu) rồi tải lên ô **Một file cả bài** (hoặc **🤖 Cho OmniVoice đọc**).
6. Xong, mở CapCut, mở dự án `<khách>_<job>_video01`:
   - video dài > 60 giây; cảnh đổi theo lời (không theo thứ tự gốc), cảnh khớp câu đang nói;
   - KHÔNG còn tiếng gốc; voice nằm trên một track âm thanh riêng, nhạc nền trên track riêng;
   - cảnh dùng lại (nếu có) được lật ngang, không đứng cạnh nhau;
   - KHÔNG có ô đỏ "thiếu file": trong thư mục dự án có thư mục `media` chứa video nguồn + voice + nhạc. Thử đổi tên
     file video gốc ở chỗ cũ → mở lại dự án → vẫn chạy được (vì đã dùng bản trong `media`).
7. Lỗi cũ "Đoạn …µs vượt quá độ dài file …" (clip lố cuối file vài mili-giây): chạy lại job đó (Chạy tiếp / dựng lại)
   → không còn báo lỗi.

## Bước 104 — Bỏ ô "Khung video": mọi video mới giữ khung GỐC, không cắt, không thu phóng `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. Trang chủ không còn ô **🖼️ Khung video** và ô **🔲 Đổi khung theo cảnh**; chỉ còn dòng "Khung video: giữ đúng khung
   video gốc, không cắt, không thu phóng".
3. Tạo một job mới (bất kỳ chế độ nào: dựng thường, đổi ngôn ngữ, review, review bỏ lửng, content nhiều phim) → mở
   CapCut kiểm tra:
   - video ngang 16:9 hiện đủ cả khung (không bị cắt hai bên), video dọc tràn màn hình;
   - không có keyframe zoom / chuyển động trên các clip; dừng hình (content nhiều phim) đứng yên, không zoom;
   - tiêu đề / phụ đề nằm đúng phía trên / trong khối hình.
4. Job tạo TRƯỚC khi cập nhật vẫn dựng theo khung đã chọn lúc đó.

## Bước 103 — Review phim: có voice mà CapCut hổng voice + phụ đề từng đoạn `[CẦN KIỂM TRA TRÊN MÁY]`

Nguyên nhân: kiểu dựng có "cắt theo nhịp nhạc" dời điểm cắt cho trúng beat → cảnh cuối của một câu ngắn đi một chút → tool
tưởng câu đó nằm ngoài video và bỏ luôn voice + phụ đề của câu (chỗ hổng trên timeline). Giờ review không dời điểm cắt
theo nhịp nữa (cảnh vốn cắt đúng theo giọng), và dù cảnh bị cắt bớt thì câu vẫn được giữ.

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`. **Đóng CapCut.**
2. Job review bị hổng: trang job → 🛠️ **🔁 Dựng lại draft** (voice đã thu giữ nguyên).
3. Mở CapCut: track voice và 2 hàng phụ đề phải liền từ đầu tới cuối, không còn khúc trống; đếm số khối voice = số câu
   trên trang voice.

## Bước 102 — Bớt "Đợi lượt hỏi đạo diễn AI" + chỉnh số lượt hỏi AI cùng lúc `[CẦN KIỂM TRA TRÊN MÁY]`

Trước đây cả một bước (lập kế hoạch, viết thuyết minh…) giữ lượt hỏi AI kể cả lúc bước đó đang làm việc khác (tách nhạc,
nhận dạng lại thoại…) nên video khác phải chờ. Giờ chỉ giữ lượt đúng lúc AI đang trả lời.

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Trang chủ → ⚙️ Cài đặt → **Số lượt hỏi AI cùng lúc (mọi video)**: mặc định 3, chọn 1–6 (có tác dụng ngay).
3. Chạy 3–4 video cùng lúc: nhật ký ít thấy "Đợi lượt hỏi đạo diễn AI" hơn; khi phải đợi thì ghi rõ "đang có N lượt khác chạy".
4. Nếu Claude / Gemini báo lỗi giới hạn (quá nhiều yêu cầu) → giảm số này xuống 2–3.

## Bước 101 — Content nhiều phim: bỏ ô dán link, tự gõ tiêu đề `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm **Ctrl + F5** ở trang chủ.
2. Thẻ **🎞️ Content nhiều phim** giờ không còn ô "Link bài TikTok"; ô **📝 Tiêu đề / mô tả bài** là bắt buộc (gõ hoặc dán
   tiêu đề bài), ảnh của bài vẫn tải lên như cũ. Không cần cài yt-dlp nữa (bỏ qua lệnh pip ở Bước 98).
3. Gõ tiêu đề + chọn ảnh + chọn ngôn ngữ → **Bắt đầu** → job chạy, AI dùng đúng tiêu đề bạn gõ.

## Bước 100 — Bước plan lỗi "sai khuôn 3 lần" → hỏi bạn có dùng bản gần nhất không `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Khi job báo "Lỗi ở bước plan: Đạo diễn trả kết quả sai khuôn 3 lần", trang job hiện khung **🛟 Có lấy kế hoạch dựng gần
   nhất không?** kèm danh sách lỗi còn lại của từng video.
3. Bấm **✅ Dùng bản này, làm tiếp** → tool dựng tiếp ngay, không hỏi lại AI. Không ưng → bấm **Chạy lại bước này**.
4. Job cũ đang lỗi sẵn từ trước khi cập nhật thì chưa có bản lưu → bấm Chạy lại bước này một lần; lần sau lỗi sẽ có nút.
5. Nếu AI trả về hoàn toàn không đọc được thì không có bản nào để dùng — trang ghi rõ, chỉ còn cách Chạy lại.

## Bước 99 — Sửa "có voice rồi nhưng không thêm vào dự án CapCut" `[CẦN KIỂM TRA TRÊN MÁY]`

Nguyên nhân tìm được trong code: (1) job đã **✅ Xong** rồi bạn mới tải / thu lại voice hoặc cho OmniVoice đọc → tool không
dựng lại; (2) tải voice lên đúng lúc job **đang chạy** (đang ghi draft, OmniVoice đang đọc) → lượt đó bị bỏ qua.

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`. **Đóng CapCut** trước khi thử.
2. Thử (1): chọn một job đã xong → tải lại 1–2 file voice (hoặc 🤖 OmniVoice đọc lại một câu) → đợi vài giây, nhật ký phải có
   "✅ Đã cập nhật voice mới vào dự án CapCut: video 01". Mở CapCut → câu đó có voice mới.
   Lưu ý: video được ghi lại như bấm 🔁 Dựng lại draft — chỉnh tay trong CapCut của video đó sẽ mất.
3. Thử (2): lúc job đang chạy, tải thêm voice → khi lượt đang chạy xong, tool tự chạy thêm một lượt và đưa voice vào.
4. CapCut đang mở → nhật ký báo "⚠️ … chưa ghi được vào dự án CapCut … Đóng CapCut rồi bấm 🔁 Dựng lại draft".
5. Vẫn còn trường hợp thiếu voice: chụp nhật ký (log) + trang voice gửi mình, ghi rõ câu nào có ✅ mà CapCut không có.

## Bước 98 — Chế độ mới "🎞️ Content nhiều phim (từ bài TikTok ảnh)" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, rồi (không còn bắt buộc từ Bước 101) cài lại thư viện trong PowerShell ở thư mục tool:

   ```powershell
   .venv\Scripts\pip install -r requirements.txt
   ```

2. Mở lại `start.bat` → trang chủ → thẻ **🎞️ Content nhiều phim** → dán **link bài TikTok ảnh**, chọn **các ảnh của
   bài** (lưu ảnh từ app TikTok hoặc chụp màn hình — tool KHÔNG tự tải được ảnh của bài ảnh), chọn ngôn ngữ → Bắt đầu.
3. Nhật ký: "Lấy được tiêu đề bài từ link…" (nếu báo không lấy được thì dán tiêu đề vào ô trên trang, không sao).
4. AI viết xong → trang **🎞️ Chọn file từng phim**: kiểm tra AI nhận đúng tên phim chưa, đọc thử content (bấm "Xem … câu").
   Bấm 📂 chọn file cho từng phim → **Lưu và chạy tiếp**. Thiếu phim / muốn đổi → gõ góp ý (vd "bỏ phim 3") → ✍️.
5. Tool phân tích từng phim (chế độ nhanh: chỉ dò cảnh + khung hình — ghi lại mất bao lâu mỗi phim), AI tìm cảnh,
   rồi tới trang voice: đọc cả bài một file (hoặc 🤖 OmniVoice — dùng "Mô tả giọng", không clone được vì tiếng phim tắt).
6. Mở CapCut kiểm tra:
   - cảnh có đúng nhân vật / sự việc câu đang nói không (sai nhiều → 🛠️ **AI tìm lại cảnh trong phim**, voice giữ nguyên);
   - **dừng hình**: video chạy rồi đứng hình, ảnh zoom chậm, tên nhân vật hiện giữa khối hình, có tiếng "tách";
   - ảnh dừng hình khớp đúng khung video (không lệch / méo) và chiếm khoảng 30% video;
   - khi sang phim mới có tên phim ở góc trên khối hình.
7. Gửi mình: phim nào AI tìm cảnh sai, ảnh dừng hình có bị lệch không, thời gian phân tích mỗi phim.

## Bước 97 — Chế độ mới "🧨 Review bỏ lửng" (kể hết phim thành nhiều phần) `[CẦN KIỂM TRA TRÊN MÁY]`

Chế độ **🎬 Review phim** cũ vẫn giữ nguyên, đây là một thẻ riêng.

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Trang chủ → chọn một phim dài (vd 1 tiếng) → bấm thẻ **🧨 Review bỏ lửng** → chọn ngôn ngữ (Hàn / Nhật / Anh) →
   chọn **🗣️ Ngôi kể** (ngôi thứ 3 hoặc ngôi thứ 1) → **🚀 Bắt đầu dựng**.
3. Đầu trang job phải ghi "🧨 Review bỏ lửng · ngôi thứ …". Sau bước phân tích, AI chia phim → trang **🧨 Duyệt các phần**:
   - các phần nối liền nhau (giây kết thúc phần trước = giây bắt đầu phần sau), phần đầu từ đầu phim, phần cuối tới hết phim;
   - mỗi phần có dòng **🎬 Short mở đầu** (5–15 giây, sửa được giây) và **🧨 Bỏ lửng** (phần cuối: **🏁 Kết phim**).
   Kiểm tra short có đúng pha kịch tính không, chỗ bỏ lửng có hợp không → **✅ Xác nhận và dựng tiếp**.
4. Trang voice: mỗi phần một bài lời đọc. Đọc thử: ngôi kể đúng lựa chọn chưa (ngôi 1 = nhân vật chính xưng "tôi");
   phần 2 trở đi mở bằng 1–2 câu nhắc bối cảnh; câu cuối mỗi phần dừng ở chỗ gay cấn, không có "xem phần sau".
5. Thu voice (hoặc 🤖 OmniVoice đọc) → mở CapCut kiểm tra từng video:
   - giây đầu là short **giữ nguyên hình + tiếng gốc**, không nhạc, chỉ có **phụ đề** = lời thoại gốc dịch sang
     ngôn ngữ video (phim cùng tiếng thì phụ đề nguyên lời gốc; chữ vàng tiếng Việt bên dưới chỉ để kiểm tra, tắt
     trước khi xuất). Đối chiếu phụ đề có khớp lúc nhân vật nói không;
   - ngay sau short là tiêu đề + lời review + nhạc nhẹ, tiếng phim tắt;
   - tổng mỗi video khoảng **1:30–2:00**.
6. Video quá ngắn / dài, hoặc phần kể bị nhảy cóc: chụp trang duyệt + trang voice gửi mình. Các con số chỉnh trong
   `config\cliff.yaml` (độ dài video, độ dài short, độ dài phim mỗi phần `min_raw_s` / `max_raw_s`).

## Bước 96 — Lồng tiếng / thuyết minh luôn nói ĐÚNG ngôn ngữ đã chọn `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Tạo job mới với chính video vừa bị lỗi (vd phim tiếng Nhật, chọn ngôn ngữ đích tiếng Hàn), cùng chế độ (Lồng tiếng
   nhân vật / Đổi ngôn ngữ). Job cũ thì bấm **Làm lại** từ bước hiểu nội dung (job cũ có thể đã lưu nhầm tiếng gốc).
3. Nhật ký phải có dòng "Đổi ngôn ngữ: ja → ko" (đúng tiếng gốc → tiếng đích), KHÔNG được có "Video gốc đã là ko".
4. Trang voice: cột câu đọc phải toàn bằng ngôn ngữ đích. Nếu AI lỡ để câu tiếng gốc, tool bắt AI viết lại (tối đa vài
   lần); vẫn sót thì bấm "🤖 Cho OmniVoice đọc" → nhật ký báo "⚠️ … câu chưa được dịch … OmniVoice KHÔNG đọc các câu này"
   (không đọc nhầm tiếng gốc nữa) → bấm viết lại thuyết minh.
5. Vẫn nghe tiếng gốc: chụp nhật ký + trang voice gửi mình (ghi rõ chữ trên trang voice đúng ngôn ngữ chưa, hay chỉ giọng
   đọc sai).

## Bước 95 — Chọn đúng bản OmniVoice muốn dùng (vd bản trong Voice Studio) + nút kiểm tra `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Trang chủ → cột phải → **⚙️ Cài đặt** → **🤖 OmniVoice (giọng AI)**: dòng tiêu đề cho biết tool đang dùng python nào,
   model nào.
3. Muốn dùng bản OmniVoice của Voice Studio: tìm file `python.exe` trong thư mục cài Voice Studio (thường có thư mục kiểu
   `venv\Scripts\python.exe` / `python\python.exe`), dán đường dẫn vào ô Python. Nếu Voice Studio có thư mục model
   OmniVoice riêng (đã tải sẵn) thì dán đường dẫn thư mục đó vào ô Model.
4. Bấm **🔎 Kiểm tra OmniVoice** → phải thấy "✅ Dùng được OmniVoice bản … trên GPU …". Nếu ❌: chụp màn hình gửi mình,
   kèm ảnh thư mục cài Voice Studio.
5. Vào job đang chờ voice → 🤖 Cho OmniVoice đọc → nghe so với Voice Studio.
6. OmniVoice chạy quá 1 tiếng hoặc bấm ⏹️ Dừng → tool tắt hẳn tiến trình OmniVoice (không còn chạy ngầm chiếm GPU).

## Bước 94 — Lồng tiếng nhân vật: bớt "lẫn giọng cũ" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Mở job Lồng tiếng nhân vật (cũ cũng được) → bấm Chạy tiếp / dựng lại draft. Tool tự TÁCH LẠI nhạc nền bằng model kỹ
   hơn `htdemucs_ft` (lần đầu tải model ~320 MB; tách chậm hơn ~4 lần nhưng chỉ tách các tình huống đã duyệt).
3. Mở draft trong CapCut, nghe các câu lồng tiếng: giọng gốc tiếng Nhật còn lẫn phía dưới không? Đuôi câu gốc còn lọt
   ra sau giọng lồng không?
4. Nếu vẫn còn lẫn, chỉnh `config/char_dub.yaml` rồi dựng lại:
   - `demucs_shifts: 2` (tách 2 lượt lấy trung bình — sạch hơn, chậm gấp đôi);
   - `bgm_duck_db: -18` (nhạc nền hạ sâu hơn khi giọng lồng nói);
   - `unvoiced_pad_s: 0.5` (tắt giọng gốc rộng hơn quanh mỗi câu);
   - `keep_unvoiced: false` (KHÔNG phát lại giọng gốc ở đâu cả — mất tiếng cười / hét gốc nhưng hết lẫn hẳn).

## Bước 93 — Lồng tiếng nhân vật: bớt sót câu / sót ý, nhận đúng giọng nhân vật `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`. Cần Demucs (đã cài) — các phần mới chạy trên giọng nói đã tách nhạc.
2. Tạo job **🎭 Lồng tiếng nhân vật** mới (job cũ: bấm làm lại từ bước chia đoạn để chạy lại phần nhận dạng).
3. Nhật ký sau bước duyệt đoạn hay:
   - "Nghe lại chỗ sót: thêm N câu Whisper bỏ lỡ (…)" — các câu nghe được thêm (tiếng kêu ngắn, nói nhỏ, nói chen).
   - "Video 01: máy đo được K nhóm giọng trên M câu thoại (G1, G2…) — gửi AI để ghi đúng nhân vật."
4. Trang voice → mở **✏️ AI đoán nhầm nhân vật?**: mỗi câu có cột "Giọng máy đo" (G1 · cao ~260Hz…); bảng nhóm giọng
   cho biết AI gán mỗi nhóm cho ai. Nhóm nào gán lẫn nhiều tên → gõ tên vào "Đặt tên cả nhóm" → 💾 Lưu (cả nhóm đổi một lần).
   Khung này tự mở sẵn khi có nhóm bị gán lẫn.
5. So với trước: còn câu nhân vật mở miệng mà không có câu lồng tiếng không? Câu dịch còn thiếu ý không (AI bị bắt dịch lại
   câu ngắn bất thường)? Ghi lại vài chỗ còn sai (giây + nhân vật) gửi mình để chỉnh ngưỡng.
6. Chỉnh được trong `config/char_dub.yaml`: `rescue_rel_db` (to hơn = bắt cả tiếng nhỏ hơn), `voice_group_threshold`
   (nhỏ hơn = tách nhiều nhóm hơn, vd 2 nhân vật giọng gần giống nhau bị gộp thì giảm xuống 0.28).

## Bước 92 — OmniVoice: tải lên giọng mẫu để clone `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Mở job đang chờ voice (Lồng tiếng nhân vật / Đổi ngôn ngữ / Review) → khung **🤖 Hoặc để OmniVoice đọc thay**.
3. Ở nhân vật muốn dùng giọng mẫu: chọn **🎤 Giọng mẫu tải lên (cần quyền)**, bấm chọn file (3–10 giây, một người nói rõ,
   không nhạc nền; .wav / .mp3 / .m4a), gõ lời đọc trong file nếu biết (không bắt buộc).
4. Tick ô **Tôi xác nhận CÓ QUYỀN dùng giọng để clone** → bấm **🤖 Cho OmniVoice đọc**.
5. Nhật ký có dòng "🎤 <tên nhân vật>: clone từ giọng mẫu bạn tải lên (…)". Nghe thử voice: giọng giống file mẫu.
6. Mở lại trang job: dưới ô chọn file có "✅ đã có: tai_len_…" — lần đọc sau không cần tải lại.
7. Không tick ô xác nhận → tool KHÔNG dùng giọng mẫu (nhật ký báo), đọc bằng giọng mô tả / tự chọn.

## Bước 91 — Dựng video TikTok: chọn được ngôn ngữ (video gốc tiếng Trung / Việt…) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm Ctrl+F5.
2. Trang chủ → thẻ **✂️ Dựng video TikTok**: giờ có ô **🌐 Ngôn ngữ video mới** (mặc định "Giữ nguyên ngôn ngữ gốc").
   Video gốc tiếng Hàn / Nhật / Anh thì để nguyên; tiếng Trung, Việt… thì chọn Hàn / Nhật / Anh.
3. Job cũ đang lỗi "Video gốc nói tiếng … Chọn ngôn ngữ…": mở trang job → khung **🌐 Chọn ngôn ngữ cho bản TikTok** →
   chọn ngôn ngữ → bấm **▶️ Chạy tiếp với ngôn ngữ này**. Job chạy tiếp, KHÔNG hỏi lại AI bước hiểu nội dung.
   (Job lỗi trước bản cập nhật này chưa có khung chọn: bấm "Chạy lại bước này" một lần để hiện khung.)

## Bước 90 — Gemini lỡ định mở web (ReadUrlContent) → tool dặn trước + tự hỏi lại `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Mở job đang lỗi "Gemini (Antigravity) không trả lời vì định dùng công cụ bị chặn (ReadUrlContent)" → bấm **Chạy tiếp**.
3. Nếu Gemini lại định mở web, nhật ký ghi "Gemini định dùng công cụ bị chặn (…) — hỏi lại kèm lời nhắc chỉ đọc file…"
   rồi tự chạy tiếp; chỉ khi hỏi lại 2 lần vẫn vậy mới báo lỗi (khi đó đổi job sang Claude ở trang job rồi Chạy tiếp).

## Bước 89 — Sửa install_gpu_torch.bat báo "No module named 'torchaudio'" `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`.
2. Nhấp đúp `install_gpu_torch.bat` lại. Không còn lỗi torchaudio; dòng "[2/3] Dang co torch 2.x.x - cai lai ban GPU
   cu126 …" rồi tải khoảng 2.5 GB (không bấm chuột vào cửa sổ).
3. Cuối cùng phải thấy "GPU chay duoc: NVIDIA GeForce GTX 1080 Ti 2.0". Mở lại `start.bat`, tạo job Lồng tiếng nhân vật:
   nhật ký Demucs ghi chạy GPU.

## Bước 88 — Nhanh hơn: AI xem khung hình dạng ảnh lưới, bỏ phân tích thừa, ghi thời gian từng bước `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Tạo job (vd Review phim). Nhật ký có dòng "Ghép 80 khung hình thành 9 ảnh lưới cho AI xem nhanh hơn" ở các bước AI.
3. So thời gian các bước AI với trước (nhất là "AI viết bài lời đọc" của review): phải nhanh hơn rõ.
4. Đầu trang job có dòng ⏱️ thời gian từng bước (Phân tích …, AI hiểu nội dung …). Nếu vẫn chậm, chụp dòng này gửi lại.
5. Kiểm tra AI vẫn kể khớp hình (câu nào kể đoạn phim nào vẫn đúng). Nếu thấy AI xem ảnh lưới kém chính xác hơn, mở
   `config/director.yaml` đổi `contact_sheet: {enabled: false, …}` để quay lại cách cũ.
6. Chế độ 🇻🇳 Phụ đề tiếng Việt: bước phân tích nhanh hơn hẳn (không dò cảnh, không dò mặt). 🎙️ Chỉ thay tiếng: không dò mặt.

## Bước 87 — Review phim: MỘT video tóm gọn cả phim, chỉ ý chính, chọn thời lượng trước `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm Ctrl+F5.
2. Trang chủ → bấm thẻ **🎬 Review phim / hoạt hình** → xuất hiện ô **⏱️ Thời lượng video review** (1:00 … 5:00,
   mặc định 2:30). Ô "Chia video dài" không còn hiện ở chế độ này.
3. Chọn ví dụ 1:30, tạo job với một tập phim / hoạt hình. Đầu trang job ghi "🎬 Review phim / hoạt hình · 1:30".
4. Job KHÔNG dừng ở bảng duyệt chia đoạn nữa — đi thẳng tới trang voice với MỘT bài lời đọc.
5. Đọc bài: chỉ kể các ý chính (nhân vật, biến cố, bước ngoặt, cao trào) và kể tới KẾT phim; độ dài khoảng 1:25–1:30
   khi đọc (trang voice báo tổng thời lượng).
6. Phim rất dài (trên 1 tiếng): AI đọc lời thoại rải đều cả phim + 80 khung hình — nếu bài kể thiếu ý quan trọng, dùng
   nút "✍️ Viết lại theo góp ý" để nói ý nào cần thêm.

## Bước 86 — Review phim luôn kể ở ngôi thứ 3 `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Tạo job Review phim (hoặc bấm "✍️ Viết lại theo góp ý" ở job review cũ).
3. Đọc bài lời đọc trên trang voice: người kể gọi nhân vật bằng tên / anh ta / cô ấy…, KHÔNG xưng "tôi / mình / chúng
   ta" (tiếng Hàn không 저는·제가·저희·우리는; tiếng Nhật không 私·僕·俺), không nói chuyện với người xem.
4. Nếu AI lỡ viết ngôi 1, tool tự bắt viết lại (nhật ký có thể ghi lỗi "phải kể ở NGÔI THỨ 3" rồi thử lại).

## Bước 85 — Tách riêng: "chọn đoạn hay" (Lồng tiếng nhân vật) khác Review phim `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Job **Lồng tiếng nhân vật**: bảng duyệt vẫn ghi loại từng tình huống ("câu nói hay: …", "hài: …", "gay cấn: …").
3. Job **Review phim**: AI chọn đoạn theo kiểu cũ của review — mỗi đoạn là một câu chuyện nhỏ trọn vẹn để KỂ LẠI
   (không còn danh sách "câu nói hay / hài / gay cấn…" của chế độ chọn đoạn hay).
4. Thanh tiến trình trang job: Review ghi "AI chọn đoạn phim để kể", Lồng tiếng nhân vật ghi "AI chọn đoạn hay (TikTok)".
   Thẻ trên trang chủ cũng mô tả rõ hai chức năng khác nhau.

## Bước 84 — Phân tích footage nhanh hơn: chạy song song + nhận dạng thoại theo lô trên GPU `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`.
2. Tạo job mới với một video dài khoảng 10 phút. Mở nhật ký job (trang job), xem các dòng mới:
   - "Nhận dạng thoại xong sau m:ss (… câu, cuda)"
   - "Dò cảnh xong sau m:ss", "Dò khuôn mặt xong sau m:ss"
   - "Phân tích xong <tên video> sau m:ss (video dài … phút)"
   Gửi lại cho mình các dòng này nếu vẫn thấy lâu, để biết phần nào chậm nhất.
3. Nhận dạng thoại và dò cảnh / mặt giờ chạy CÙNG LÚC, nên các dòng nhật ký xen kẽ nhau là bình thường.
4. Nếu thấy dòng "Nhận dạng theo lô lỗi (… out of memory …) — chạy lại cách thường" thì mở `config/whisper.yaml`,
   đổi `batch_size: 8` thành `batch_size: 4` (hoặc `batched: false` để tắt hẳn).
5. Kiểm tra phụ đề / câu thoại của job vẫn chia câu hợp lý (không gộp thành câu dài 30 giây).

## Bước 83 — Trang chủ mới: 3 bước, chọn chế độ bằng thẻ; bỏ Kho tài nguyên + So sánh video `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, bấm Ctrl+F5 trên trình duyệt.
2. Trang chủ không còn thẻ "📚 Kho tài nguyên" và "🔍 So sánh video" (trang job cũng bỏ mục so sánh).
3. Form "Tạo video mới" có 3 bước: **1 Chọn video** → **2 Bạn muốn làm gì?** (6 thẻ: Dựng video TikTok / Đổi ngôn ngữ /
   Chỉ thay tiếng / Review phim / Lồng tiếng nhân vật / Chỉ phụ đề tiếng Việt) → **3 Tùy chọn** (ô tick dạng nút tròn +
   ô khung video có hình minh họa). AI đạo diễn, nhạc nền, mã khách nằm trong "⚙️ Nâng cao".
4. Bấm từng thẻ chế độ: ô ngôn ngữ chỉ hiện khi chế độ cần; các tùy chọn không dùng được với chế độ đó tự ẩn
   (vd Lồng tiếng nhân vật: ẩn hook, chia video, ⚡).
5. Tạo thử một job mỗi chế độ (vd Lồng tiếng nhân vật + tiếng Hàn) → mở trang job, dòng chế độ ở đầu trang phải đúng.
6. Danh sách "Các video" bên phải vẫn tự cập nhật mỗi 3 giây; số luồng / tự xóa job / dự án mẫu CapCut nằm trong
   "⚙️ Cài đặt" dưới danh sách.
7. Thử thu nhỏ cửa sổ trình duyệt (hoặc mở trên điện thoại cùng mạng): các thẻ xếp thành một cột, không bị tràn ngang.

## Bước 82 — AI chọn "đoạn hay" rộng hơn: câu nói hay, hài, gay cấn, bất ngờ, cảm xúc… `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Tạo job mới **Lồng tiếng nhân vật** (từ Bước 85: chỉ chế độ này, Review phim chọn đoạn theo cách riêng). Ở bảng duyệt, ghi chú từng đoạn / tình huống giờ ghi
   rõ loại: "câu nói hay: …", "hài: …", "gay cấn: …", "bất ngờ: …", "cảm xúc: …".
3. Kiểm tra có những đoạn chỉ hay vì CÂU THOẠI (không có hành động) — trước đây AI hay bỏ qua loại này.

## Bước 81 — Tách nhạc nền nhanh hơn: chỉ tách các tình huống đã duyệt + Demucs chạy GPU `[CẦN KIỂM TRA TRÊN MÁY]`

1. Đóng `start.bat`, `git pull`.
2. Nhấp đúp **`install_gpu_torch.bat`** (tải ~2,5 GB). Cuối cùng phải thấy `Thay GPU: True` và `GPU chay duoc: NVIDIA
   GeForce GTX 1080 Ti ...`. Thấy `False` hoặc chữ LOI → chụp màn hình gửi Claude.
3. Mở `start.bat`, Ctrl+F5. Tạo job **Lồng tiếng nhân vật** mới với một video dài. Sau khi duyệt các tình huống, nhật ký
   phải có: "Tách nhạc nền khỏi giọng nói — chỉ N tình huống đã duyệt (~X phút), Demucs chạy bằng GPU…", rồi "Lời thoại
   gốc trong các tình huống: A → B câu…". Bước này giờ chạy SAU khi duyệt (trước đây chạy cả phim trước khi chọn).
4. So thời gian với lần trước. Nếu nhật ký ghi "Demucs chạy bằng CPU — CHẬM" → làm lại bước 2.
5. OmniVoice (nếu đã cài bằng install_omnivoice.bat bản cũ — cu128, không dùng được GTX 1080 Ti): xóa thư mục
   `omnivoice-env` trong thư mục tool rồi nhấp đúp lại `install_omnivoice.bat` (giờ cài bản cu126).

## Bước 80 — Lồng tiếng bắt đủ câu thoại gốc hơn; review nói liền mạch, gần như không hở `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. **Lồng tiếng nhân vật** (job MỚI): sau bước AI hiểu nội dung, nhật ký có "Nhận dạng lại lời thoại trên giọng nói đã
   tách nhạc…" rồi "Lời thoại gốc: A → B câu…" — B thường lớn hơn A (bắt thêm câu ngắn / câu nói chen nhạc). Bước này
   cần Demucs + GPU, mất thêm vài phút. Mở `dub_scripts.txt` / trang voice: các câu ngắn như "え？", "うわっ" phải có.
   Chỗ nào nhân vật vẫn nói mà không có câu lồng: tool phát giọng gốc ở đó (như Bước 75) — ghi lại giây gửi Claude.
3. **Review** (job cũ cũng được): bấm **🔁 Dựng lại draft** (không cần thu lại). Nhật ký báo video ngắn hơn trước một
   chút. Mở CapCut nghe: các câu nối sát nhau, chỉ còn nghỉ ~0,05 giây; không còn khoảng lặng ở đầu / cuối từng câu.
   Bản voice đã cắt lặng nằm ở `jobs\<job>\voice\_lien_mach\` (file gốc của bạn giữ nguyên).
4. Thấy hơi gấp quá: tăng `voice_gap_s` (vd 0.1) trong `config\review.yaml` rồi dựng lại; thấy cụt chữ đầu / cuối câu:
   tăng `voice_trim_keep_s` (vd 0.06).

## Bước 79 — Video dài chia phần cho AI làm song song (nhanh hơn, nhất là với Gemini) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Tạo job với một video **dài hơn 10 phút** có tick chia video / review / lồng tiếng nhân vật (các chế độ có bước "AI
   chọn đoạn"). Nhật ký phải có dòng "Video dài N phút → chia K phần (…) cho AI chọn đoạn song song rồi gộp lại".
3. Bảng duyệt chia video: các video của mọi phần nằm chung một bảng theo thứ tự thời gian; ghi chú editor ghi
   "Phần 1 … | Phần 2 …". Kiểm tra không có đoạn bị cắt ngang câu ở chỗ chia phần.
4. Job ra nhiều video: bước lập kế hoạch / viết thoại chạy 2 video cùng lúc (nhật ký hiện "Lập kế hoạch dựng video 01…"
   và "…video 02…" gần như cùng lúc).
5. So thời gian với trước. Nếu AI báo hết hạn mức / quá tần suất: mở `config\director.yaml`, đổi `parallel_calls: 2`
   thành `1` (chạy lần lượt như cũ). Muốn chia phần ngắn hơn: giảm `split_over_s` (giây).

## Bước 78 — 🤖 AI đạo diễn Gemini Pro qua Antigravity CLI (thay Gemini CLI) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Đóng `start.bat`, `git pull`.
2. Nhấp đúp **`install_antigravity.bat`** — máy đã có `agy` thì nó bỏ qua bước cài, mở `agy` để kiểm tra đăng nhập
   (đã đăng nhập thì `/quit` luôn).
3. Mở `start.bat`, Ctrl+F5. Ô **🤖 AI đạo diễn** ghi "Gemini Pro (Antigravity CLI)" → chọn, tạo một job ngắn.
4. Nhật ký job hiện "Đang hỏi đạo diễn AI Gemini qua Antigravity (…)". Xem tóm tắt nội dung có tả đúng hình trong
   video không (Gemini xem khung hình bằng cách đọc file ảnh — đã thử được với ảnh mẫu "CON MEO 58").
5. Lỗi "định dùng công cụ bị chặn (RunCommand)" lặp lại → chụp nhật ký gửi Claude. Lỗi "chưa đăng nhập" → gõ `agy`
   trong PowerShell để đăng nhập lại. Job cũ đang để Gemini (Gemini CLI) tự chạy bằng Antigravity, không cần đổi.

## Bước 77 — (ĐÃ THAY bằng Bước 78: Gemini CLI không đăng nhập được gói AI Pro nữa) 🤖 Chọn AI đạo diễn cho từng job: Claude hoặc Gemini Pro `[CẦN KIỂM TRA TRÊN MÁY]`

1. Đóng `start.bat`, `git pull`.
2. Nhấp đúp **`install_gemini.bat`** (xem docs/SETUP_WINDOWS.md mục Gemini): đăng nhập "Sign in with Google" bằng tài
   khoản có gói Google AI Pro, gõ `/quit`. Kiểm tra: PowerShell gõ `gemini --version` → `0.63.0`.
3. Mở `start.bat`, Ctrl+F5. Trang chủ có ô **🤖 AI đạo diễn** → chọn **Gemini Pro**, tạo một job ngắn.
4. Nhật ký job hiện "Đang hỏi đạo diễn AI Gemini (…)"; đầu trang job ghi "🤖 AI: Gemini Pro". Kiểm tra AI có hiểu đúng
   nội dung video (bước hiểu nội dung gửi kèm khung hình — xem tóm tắt có tả đúng hình không).
5. Thử đổi AI: ở trang job (khi job đang chờ / lỗi) chọn Claude → **🔁 Đổi AI cho job này** → Chạy tiếp.
6. Báo lỗi "Gemini CLI chưa đăng nhập" → làm lại bước 2. Báo "hết hạn mức" → đợi, hoặc đổi job sang Claude.

## Bước 76 — Trang chủ gọn hơn: chỉ "AI tự chọn", thêm khung video, bỏ ô giữ nhạc nền `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Mục **Kiểu dựng** chỉ còn ô "✨ AI tự chọn".
3. Ô **Khung video** có: 4:3, 16:9, 1:1, 4:5, 3:4, 9:10, 9:16 (dọc kín màn hình), Tự động. Thử tạo job với 4:5 và 9:16,
   mở draft CapCut: khối video đúng tỉ lệ; 9:16 thì hình kín màn hình, tiêu đề + phụ đề đè lên hình.
4. Không còn ô "🎵 Giữ nhạc nền gốc" dưới "Chỉ thay tiếng".

## Bước 75 — 🎭 Lồng tiếng nhân vật: khớp miệng, không còn chỗ "đang nói mà không có tiếng", không edit thừa `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Job MỚI là tốt nhất. Với job cũ: bấm **🎬 Lập lại kế hoạch dựng** — AI dịch lại theo cách mới, số câu có thể khác nên
   voice đã thu phải thu / cho OmniVoice đọc lại.
3. Trang voice + `dub_scripts.txt`: số câu = đúng số câu thoại gốc; mỗi câu ghi đúng giây của câu gốc (kể cả câu rất
   ngắn như "え？" → "어?").
4. Mở draft CapCut, kiểm tra:
   - Không có zoom, sticker, chữ nhấn, SFX, chuyển cảnh, filter — hình y như phim gốc, chỉ có các tình huống nối nhau +
     phụ đề + tiêu đề.
   - Giọng lồng bắt đầu đúng lúc nhân vật mở miệng.
   - Có thêm một track âm thanh `vocals_00.wav` (giọng gốc): nó chỉ phát ở chỗ KHÔNG có câu lồng (tiếng cười, hét…),
     tắt trong các câu lồng. Chỗ nào nghe lẫn tiếng Nhật thì đó là câu Whisper không nhận ra — báo Claude giây thứ mấy.
     Không muốn giữ giọng gốc: sửa `keep_unvoiced: false` trong `config\char_dub.yaml` rồi bấm 🔁 Dựng lại draft.

## Bước 74 — Cài OmniVoice bằng một cú nhấp đúp (`install_omnivoice.bat`) `[CẦN KIỂM TRA TRÊN MÁY]`

Dùng khi bấm 🤖 Cho OmniVoice đọc mà báo "chưa cài OmniVoice".
(Sửa 11/10: bản đầu của file này tự tắt sau bước 2 do lỗi cú pháp — `git pull` để lấy bản đã sửa rồi nhấp đúp lại;
môi trường `omnivoice-env` đã tạo dở được dùng tiếp, không cần xóa.)

1. Đóng cửa sổ `start.bat`. Mở PowerShell trong thư mục tool, chạy `git pull`.
2. Mở `config\tts.yaml`: dòng `python:` phải là `python: ""` (để trống — tool tự tìm). Nếu bạn đã điền gì đó mà không
   chắc đúng, xóa đi cho về `""`.
3. Nhấp đúp **`install_omnivoice.bat`**. Chờ 10–30 phút (không bấm chuột vào cửa sổ). Cuối cùng phải thấy
   `OmniVoice OK - dung GPU: True` (có GPU NVIDIA) hoặc `False` (chạy CPU, chậm). Có chữ LỖI → chụp màn hình gửi Claude.
4. Mở lại `start.bat`, Ctrl+F5, vào job đang chờ voice, bấm **🤖 Cho OmniVoice đọc**. Lần đầu OmniVoice tải model vài GB
   (nhật ký hiện "OmniVoice: tải model…") — chờ xong, mỗi câu sẽ có voice.
5. Vẫn báo lỗi thì câu lỗi giờ ghi rõ python nào đang được dùng — chụp gửi Claude.

## Bước 73 — Sửa lỗi "UnicodeEncodeError: 'charmap' codec can't encode character" khi bấm 🤖 Cho OmniVoice đọc `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Mở lại job đang chờ voice, bấm **🤖 Cho OmniVoice đọc**.
3. Không còn lỗi `'charmap'`. Nếu giờ hiện "chưa cài omnivoice ở môi trường python này" → đó là lỗi THẬT trước đây bị
   che: OmniVoice chưa cài, hoặc `python:` trong `config\tts.yaml` trỏ sai. Kiểm tra bằng PowerShell:
   `C:\omnivoice-env\Scripts\python -c "import omnivoice; print('ok')"` (đổi đường dẫn theo máy bạn) — in `ok` là
   đúng; báo lỗi thì cài theo docs/SETUP_WINDOWS.md mục "OmniVoice".

## Bước 72 — 🎭 Lồng tiếng nhân vật: chọn TÌNH HUỐNG 10–20 giây thay vì một khúc dài `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Tạo job mới: một video tiếng Nhật dài (vd 10–20 phút), tick **🎭 Lồng tiếng nhân vật**, 🌐 chọn **tiếng Hàn**.
   (Job cũ đã chia đoạn xong thì vẫn chạy kiểu cũ — muốn thử kiểu mới phải tạo job mới.)
3. Bảng **✂️ Duyệt chia video**: mỗi video có dòng **🎬 N tình huống ghép thành video** — bấm mở ra thấy danh sách từng
   tình huống (vd `30.0–45.0s (15s) — cú hài`). Kiểm tra: mỗi tình huống khoảng 10–20 giây, là một màn trọn vẹn (cãi
   nhau, cú hài, pha bất ngờ…); cột Độ dài = TỔNG các tình huống (60–120 giây).
4. Xác nhận → mở draft CapCut: video là các tình huống nối nhau theo thứ tự phim, chỗ rề rà giữa các tình huống đã bị
   bỏ, không cắt giữa câu thoại.
5. Nếu sửa giây bắt đầu / kết thúc của video trong bảng: tool chỉ giữ các tình huống nằm trong khoảng mới.

## Bước 71 — 🤖 OmniVoice đọc thoại thay bạn (giọng AI, clone giọng nhân vật) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Cài OmniVoice theo docs/SETUP_WINDOWS.md mục "OmniVoice", sửa `python:` trong `config\tts.yaml`.
   Kiểm tra nhanh: `C:\omnivoice-env\Scripts\python -c "import omnivoice, torch; print(torch.cuda.is_available())"`
   (True = có GPU, đọc nhanh).
2. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5. Mở một job đang chờ voice (lồng tiếng nhân vật / đổi ngôn
   ngữ / review).
3. Khung **🤖 Hoặc để OmniVoice đọc thay**: mỗi nhân vật đã có sẵn mô tả giọng do AI đề xuất (vd "male, young adult, high
   pitch") — sửa nếu muốn. Chọn **Clone từ giọng gốc** cho nhân vật nào muốn giống giọng gốc → tick ô xác nhận CÓ QUYỀN.
4. Bấm **🤖 Cho OmniVoice đọc** (chọn một video hoặc tất cả). Nhật ký hiện "OmniVoice: tải model…", "OmniVoice: 3/40 …";
   lần đầu tải model mất vài phút.
5. Xong: mỗi câu đã có voice, tool tự dựng tiếp (video nào đủ voice thì ghi CapCut luôn). Mở draft nghe: mỗi nhân vật một
   giọng, đọc khớp thời lượng câu gốc. Câu nào không ưng → thu tay đè lên đúng câu đó rồi dựng lại.
6. Nếu báo "Chưa chạy được OmniVoice": kiểm tra lại đường dẫn `python:` trong `config\tts.yaml` và bước 1.

## Bước 70 — Chế độ "🎭 Lồng tiếng nhân vật" (Nhật → Hàn, giữ nền gốc) `[CẦN KIỂM TRA TRÊN MÁY]`

0. Cần Demucs để giữ nhạc + tiếng nền gốc (đã cài khi làm "Giữ nhạc nền gốc" — xem docs/SETUP_WINDOWS.md mục Demucs).
1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Trang chủ: chọn MỘT video tiếng Nhật, tick **🎭 Lồng tiếng nhân vật**, ô 🌐 chọn **tiếng Hàn** → Bắt đầu.
   Đầu trang job ghi "🎭 Lồng tiếng nhân vật"; các bước: AI tìm đoạn hay (TikTok) → Chờ duyệt đoạn hay → AI cắt bỏ đoạn
   rề rà → AI dịch thoại + nhận diện nhân vật → Chờ voice từng nhân vật → Ghép giọng mới + nền gốc → CapCut.
3. Bảng duyệt: các đoạn AI chọn phải là đoạn "dính" (hài / gay cấn / cảm động); đoạn rề rà nằm ở "Đoạn bị bỏ" kèm lý do.
4. Trang voice: mục **🎭 Thu voice theo nhân vật** — mỗi nhân vật một ô tải. Mở "✏️ Sửa tên người nói" nếu AI đoán nhầm,
   sửa rồi bấm Lưu. Thu mỗi nhân vật một file (đọc hết câu của nhân vật đó theo thứ tự trong `dub_scripts.txt`, nghỉ
   ~1 giây giữa các câu) → tải vào ô của nhân vật đó.
5. Mở draft trong CapCut: không còn giọng Nhật; nhạc + tiếng động gốc vẫn nghe (nhỏ hơn lúc có giọng lồng); giọng Hàn
   đúng lúc nhân vật mở miệng, đúng giọng từng nhân vật; phụ đề tiếng Hàn.

## Bước 69 — Voice đến đâu ghi CapCut đến đấy `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Dùng một job review (hoặc đổi ngôn ngữ) có 2–3 video, đang ở bước **Chờ bạn đọc cả bài** / **Chờ voice thuyết minh**.
3. Thu và tải lên voice của **riêng video 01** (ô "Một file cả bài" của video 01).
4. Đợi vài giây, tải lại trang: dưới tiêu đề "🎬 Video 01" có dòng **✅ Đã ghi dự án CapCut … khach_<job>_video01**;
   nhật ký có "✅ Video 01 đủ voice — đã ghi dự án CapCut". Job vẫn chờ voice các video còn lại.
5. Mở CapCut (hoặc bấm vào màn hình chính CapCut để làm mới danh sách): dự án `…_video01` đã có, mở xem / chỉnh được.
6. Thu lại một câu của video 01 rồi tải lên → draft video 01 được ghi lại (đóng dự án đó trong CapCut trước khi tải).
7. Tải xong voice các video còn lại → job tự dựng tiếp tới Xong như thường.

## Bước 68 — Lời review hay & tự nhiên hơn: biên tập 2 lượt, văn mẫu, viết lại theo góp ý `[CẦN KIỂM TRA TRÊN MÁY]`

1. (Nên làm) Mở `config\review_style.txt` bằng Notepad, xóa đoạn mẫu tiếng Hàn của tool, dán LỜI ĐỌC của 1–3 video review
   bạn thấy hay (chép từ phụ đề), lưu lại. AI sẽ học giọng / nhịp kể theo văn mẫu này.
2. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5. Tạo job MỚI với ô 🎬 (job cũ: 🌐 Viết lại thuyết minh).
3. Bước "AI viết bài lời đọc" giờ lâu hơn một chút (AI viết xong rồi tự biên tập lại lượt 2). Đọc khung 📜 Bài lời đọc:
   câu phải trôi, câu dài ngắn xen kẽ, không lặp một từ nối liên tục.
4. Chưa ưng: gõ góp ý vào ô **✍️ Chưa hay / chưa tự nhiên? Góp ý để AI viết lại** (vd "câu cứng quá, nói như kể chuyện
   với bạn bè, mở đầu chưa cuốn") → bấm **Viết lại theo góp ý** → vài phút sau có bài mới. Voice đã tải của video đó
   được cất thành `*_cu` (không mất).
5. Muốn tắt lượt biên tập cho nhanh: `config\review.yaml` → `polish: false`.

## Bước 67 — Mỗi chế độ hiện quy trình riêng `[CẦN KIỂM TRA TRÊN MÁY]`

1. QUAN TRỌNG: sau `git pull` phải **tắt hẳn cửa sổ `start.bat`** (bấm X) rồi mở lại — server cũ vẫn chạy code cũ dù đã
   pull. Trên trình duyệt bấm Ctrl+F5.
2. Mở một job review (hoặc tạo mới với ô 🎬): đầu trang ghi **🎬 Review phim / hoạt hình**; thanh tiến trình chỉ có:
   Phân tích footage → AI hiểu nội dung → AI tìm đoạn hay → Chờ duyệt đoạn hay → AI chọn tiêu đề · nhạc → AI viết bài
   lời đọc → Chờ bạn đọc cả bài → Dựng cảnh theo voice → CapCut → AI viết caption → Xong. KHÔNG có bước hook.
3. Job thường / đổi ngôn ngữ / chỉ thay tiếng / phụ đề tiếng Việt: đầu trang ghi đúng chế độ, các bước theo chế độ đó.

## Bước 66 — Review: tool viết lời TRƯỚC → bạn đọc cả bài → tool dựng cảnh theo voice `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5. Tạo job MỚI với ô **🎬 Review phim / hoạt hình**
   (job cũ: bấm **🌐 Viết lại thuyết minh**).
2. Duyệt các đoạn hay → job dừng ở **Chờ voice thuyết minh**. Mỗi video có khung **📜 Bài lời đọc**: cả bài viết liền
   một đoạn (kèm nghĩa tiếng Việt và dàn ý câu chuyện). File `dub_scripts.txt` cũng có mục "📜 BÀI LỜI ĐỌC".
3. Đọc CẢ BÀI một lượt trong Voice Studio theo nhịp tự nhiên, NGHỈ ~1 giây giữa các câu → tải lên ô **Một file cả bài**.
4. Chạy tiếp → nhật ký có dòng "Dựng từ voice: N câu → M cảnh, dài …s".
5. Mở draft trong CapCut: giọng chạy liền từ đầu tới cuối; câu nào kể đoạn phim nào thì hình đoạn đó chạy dưới câu đó,
   cắt cảnh nhanh ~2 giây; video dài đúng bằng file voice của bạn; không còn tiếng phim.
6. Muốn cảnh dài / ngắn hơn: `cut_s` trong `config\review.yaml` (vd 1.5 = nhanh hơn, 3 = chậm hơn).

## Bước 65 — Review: HÌNH CHẠY THEO GIỌNG (đọc nhanh / chậm đều khớp) `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5.
2. Job review đang chờ voice (hoặc tạo job mới với ô 🎬): mỗi câu giờ ghi "đọc theo nhịp của bạn · hình tự co / giãn
   khớp giọng" thay cho "chỗ 4.5s".
3. Đọc CẢ BÀI liền mạch theo nhịp tự nhiên (nghỉ ~1 giây giữa các câu để tool cắt được) → tải lên ô "Một file cả bài".
   Mỗi câu hiện "🟢 voice 2.0s — cảnh của câu này sẽ dài đúng 2.0s".
4. Bấm chạy tiếp → nhật ký có dòng "Hình chạy theo giọng: … câu co cảnh, … câu kéo dài cảnh".
5. Mở draft trong CapCut: giọng chạy liền từ đầu tới cuối, KHÔNG có khoảng im giữa các câu; mỗi câu kể đúng lúc cảnh của
   nó hiện; tổng thời lượng video ≈ tổng thời lượng giọng của bạn.
6. Video ngắn hơn 2:10 vì bạn đọc nhanh: bấm **🌐 Viết lại thuyết minh** — lần này AI viết theo tốc độ thật của bạn
   (đã lưu `review_voice_cps` trong `config\local.yaml`) nên kịch bản dài hơn, đủ 2:10–2:30.

## Bước 64 — Review: tắt hẳn tiếng phim, giọng review nói liền mạch `[CẦN KIỂM TRA TRÊN MÁY]`

1. Tắt `start.bat`, `git pull`, mở lại `start.bat`, Ctrl+F5. Tạo job MỚI với ô **🎬 Review phim / hoạt hình**
   (job cũ: bấm **🎬 Lập lại kế hoạch dựng** rồi **🌐 Viết lại thuyết minh**).
2. `dub_scripts.txt`: các câu nối liền nhau thành một câu chuyện, không chỗ nào để trống. Mẹo: đọc CẢ BÀI vào MỘT file
   (nghỉ ~1 giây giữa các câu) rồi tải lên ô "Một file cả bài" — tool tự cắt và xếp sát nhau.
3. Mở draft trong CapCut, bật loa nghe:
   - KHÔNG còn nghe tiếng phim (track video bị tắt tiếng);
   - từ giây đầu tới giây cuối chỉ có giọng review của bạn nói liên tục + nhạc nền nhỏ;
   - không có clip quay chậm / lặp lại.
4. Muốn nghe lại tiếng phim nhỏ bên dưới: `config\review.yaml` → `original_audio: mute: false`.

## Bước 63 — Trang chủ hiện đúng độ dài video review `[CẦN KIỂM TRA TRÊN MÁY]`

1. Đóng cửa sổ `start.bat` (bấm X hoặc Ctrl+C), rồi trong PowerShell ở thư mục tool:
   ```powershell
   git pull
   git log --oneline -1      # phải thấy dòng "Trang chủ: độ dài video review đọc từ config"
   ```
2. Nhấp đúp `start.bat` lại, trên trình duyệt bấm **Ctrl+F5**.
3. Ô 🎬 phải ghi "mỗi đoạn một video **2:10–2:30** có lời review". Đổi `min_video_s` / `max_video_s` trong
   `config\review.yaml` rồi mở lại `start.bat` → dòng chữ đổi theo.

## Bước 62 — Review phim: video 2:30 + tốc độ đọc riêng của giọng review `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Tạo job MỚI với ô **🎬 Review phim / hoạt hình** (phim nên dài ≥ 5 phút
   để mỗi video có đủ ~2:30).
2. Bảng duyệt chia video: mỗi đoạn AI chọn dài khoảng 2:20–7:00 phim gốc (dựng gọn lại còn 2:10–2:30).
3. Ở bước chờ voice: mở `dub_scripts.txt`, đọc thử vài câu bằng giọng review của bạn — câu vừa với "chỗ trống" ghi bên
   cạnh (AI viết theo 8.7 chữ/giây × 85%). Thu và tải lên → hầu hết câu 🟢 khớp hoặc 🟡 tăng tốc nhẹ, ít câu 🔴.
4. Draft trong CapCut dài 2:10–2:30. Nhật ký có dòng "Giọng thu của bạn đọc ~… ký tự/giây (ko); đã lưu … (giọng review)".
5. Giọng review đổi tốc độ / thêm tiếng Nhật, Anh: sửa `voice_cps` trong `config\review.yaml`
   (vd `voice_cps: {ko: 8.7, ja: 7.5, en: 16}`).

## Bước 61 — Review phim giống video mẫu (cảnh chuyển nhanh, bố cục tiêu đề trắng + xanh) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Tạo job MỚI với ô **🎬 Review phim / hoạt hình** (job cũ: bấm
   **🎬 Lập lại kế hoạch dựng** rồi **🌐 Viết lại thuyết minh**).
2. Mở draft trong CapCut, so với video mẫu:
   - nền tối, 2 dòng tiêu đề trên cùng (dòng 1 trắng, dòng 2 XANH LÁ, viền đen), khung phim gần vuông (9:10) ở giữa;
   - cảnh chuyển liên tục, mỗi cảnh khoảng 1–3 giây (CapCut: nhìn track video thấy rất nhiều đoạn ngắn);
   - một câu voice kéo liền qua 2–3 cảnh, không bị ngắt ở chỗ đổi cảnh;
   - phụ đề trắng viền đen, cụm ngắn, nằm ở khoảng 2/3 khung phim.
3. Nếu chữ tiêu đề quá to / nhỏ hoặc lệch so với mẫu: sửa `review_story` trong `config\layout.yaml` (`title_rows`,
   `title_width`, `subtitle_row`). Muốn cảnh chậm hơn / nhanh hơn: `avg_clip_s`, `max_clip_s` trong `config\review.yaml`.

## Bước 60 — Review phim kể thành MỘT CÂU CHUYỆN `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Tạo job mới với ô **🎬 Review phim / hoạt hình** (job cũ đã viết lời rồi
   thì bấm **🌐 Viết lại thuyết minh** ở trang job).
2. Khi tới bước **Chờ voice thuyết minh**, mở `dub_scripts.txt`: đầu mỗi video có dòng **📖 Câu chuyện:** (mở đầu – mâu
   thuẫn – cao trào – kết).
3. Đọc cột **Nghĩa** các câu: phải nghe như đang KỂ một câu chuyện nối liền ("Cả đời cậu bé chỉ mong… Nhưng không ngờ…"),
   KHÔNG phải kiểu "cậu bé đang chạy, con mèo đang nhìn". Nếu vẫn thấy tả cảnh nhiều, hạ `max_describe_share` trong
   `config\review.yaml` (vd 0.2) rồi bấm Viết lại thuyết minh.

## Bước 59 — Chế độ "🎬 Review phim / hoạt hình" `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`, tải lại trang chủ (Ctrl+F5).
2. Trang chủ: chọn một tập phim / hoạt hình (dài vài phút trở lên), tick **🎬 Review phim / hoạt hình**, chọn ngôn ngữ
   lời review ở ô **🌐 Đổi ngôn ngữ** (Hàn / Nhật / Anh; để "Giữ nguyên" thì lời review dùng tiếng gốc — chỉ khi phim nói
   Hàn / Nhật / Anh). Có thể tick thêm "Có hook voice" → Bắt đầu.
3. Job dừng ở **Chờ duyệt chia video**: bảng liệt kê các ĐOẠN HAY AI chọn (mỗi đoạn một video) + các đoạn bị bỏ kèm lý
   do. Chỉnh điểm cắt / bỏ bớt / thêm đoạn rồi bấm Xác nhận.
   Phim dài (vd 20 phút) có nhiều đoạn hay → bảng có NHIỀU video (mỗi đoạn hay một video). AI được xem ~24 khung hình rải
   đều cả phim nên đoạn hoạt hình ít thoại mà hình hay vẫn được chọn (`segment_frames` trong `config\review.yaml`).
4. Job dừng ở **Chờ voice thuyết minh**: kịch bản là LỜI REVIEW (kể lại + bình luận, có nghĩa tiếng Việt) cho từng video.
   Thu bằng Voice Studio (từng câu, hoặc cả bài một file nghỉ ~1 giây giữa các câu) rồi tải lên.
5. Mở các draft `…_video01`, `…_video02`… trong CapCut, kiểm tra:
   - mỗi video dài **1:00–1:30** (kể cả hook), các cảnh theo đúng thứ tự phim, mỗi cảnh ngắn (≤ 12 giây);
   - lời review gần như liên tục; tiếng phim vẫn nghe được nhưng NHỎ dưới voice (không tắt hẳn), chỗ không có voice
     tiếng phim to lên;
   - phụ đề chính = lời review; chữ vàng nhỏ tiếng Việt bên dưới để kiểm tra (tắt ở trang job trước khi xuất).
6. Muốn tắt hẳn tiếng phim / đổi độ dài video: sửa `config\review.yaml` (`original_audio.mute`, `min_video_s`,
   `max_video_s`).

## Bước 58 — Chọn NHIỀU file một lúc `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`, tải lại trang chủ (Ctrl+F5).
2. Bấm **📂 Chọn file…** → trong hộp thoại giữ **Ctrl** và bấm từng file (hoặc bấm file đầu, giữ **Shift** bấm file cuối,
   hoặc Ctrl+A) → Open.
3. Ô File footage hiện tất cả đường dẫn, mỗi file một dòng; dưới nút có dòng "Đã thêm N video — tool sẽ ghép thành một
   video". Bấm Chọn file lần nữa vẫn thêm tiếp vào dòng mới.

## Bước 57 — Sửa nút "📂 Chọn file…" không bấm được `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`, tải lại trang chủ (Ctrl+F5).
2. Bấm **📂 Chọn file…** → hộp thoại chọn file mở ra; chọn xong đường dẫn hiện trong ô.
3. Bấm lần nữa, chọn file khác → đường dẫn thứ hai hiện ở DÒNG MỚI (ghép nhiều video).

## Bước 56 — Chế độ "Phụ đề tiếng Việt" (xem hiểu video nước ngoài) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ: chọn một video nước ngoài (tiếng gì cũng được), tick **🇻🇳 Chỉ phụ đề tiếng Việt** → Bắt đầu.
3. Job chạy: Phân tích footage → Ghi dự án CapCut → Xong (không có bước hook / kế hoạch / caption). Nhật ký có
   "Dịch N câu thoại (…) sang tiếng Việt…".
4. Trang Xong → **⬇️ Tải file .srt**. Để file .srt cùng thư mục, đổi tên giống video gốc (vd `phim.mp4` + `phim.srt`), mở
   video bằng VLC / PotPlayer / Phim & TV → phụ đề tiếng Việt hiện đúng lúc, đủ dấu.
5. Hoặc mở draft `…_vietsub` trong CapCut: video gốc nguyên vẹn, tiếng gốc còn, phụ đề tiếng Việt chữ trắng viền đen
   ngay dưới video (video dọc: ở phần dưới màn hình) → xuất mp4 nếu muốn có chữ sẵn.
6. Video dài: dịch theo lô 60 câu (`config\dub.yaml → vi_sub_batch`), mỗi lô một lần hỏi AI.

## Bước 55 — Ghép nhiều video thành một câu chuyện ~2 phút (giữ tiếng gốc + nhạc nền) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Ô **File footage**: thêm nhiều tập phim / hoạt hình (mỗi dòng một file). KHÔNG tick ⚡ (trừ khi muốn cảnh gay cấn lên
   đầu) → Bắt đầu.
3. Mở draft trong CapCut, kiểm tra:
   - video dài khoảng 2 phút (100–140 giây);
   - cảnh lấy từ hầu hết các tập, xếp thành một mạch có ý nghĩa (chặng đường / quá trình / tình bạn...) — đọc
     "Ghi chú editor" trên trang job để xem AI chọn mạch gì;
   - tiếng gốc của từng cảnh vẫn còn, có thêm nhạc nền cảm xúc (nhỏ đi khi có thoại), hiệu ứng / chuyển cảnh mềm;
   - tiêu đề nói về ý nghĩa chung, không nói về một tập riêng.
4. Chỉnh độ dài: `config\hype.yaml` → `montage_target_s` (mặc định 120), `montage_tolerance_s`, `montage_max_clip_s`.

## Bước 54 — Chuyển cảnh liên tục (gay cấn lên đầu) + Ghép nhiều video `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. **Chuyển cảnh liên tục (1 video):** tick **⚡ Chuyển cảnh liên tục — cảnh gay cấn lên đầu** → tạo job. Mở draft:
   - mỗi cảnh khoảng 3–5 giây, chuyển cảnh liên tục từ đầu đến cuối;
   - mấy giây đầu là các cảnh gay cấn / đắt nhất; phần sau là các cảnh còn lại theo đúng thứ tự thời gian.
   Nhật ký bước kế hoạch có dòng "Tự sửa: xếp N cảnh gay cấn lên đầu…".
3. **Ghép nhiều video:** ở ô **File footage** bấm **📂 Chọn file…** nhiều lần (mỗi lần thêm một dòng) hoặc dán nhiều
   đường dẫn, mỗi dòng một file → Bắt đầu.
   - Nhật ký: "Ghép N video thành một nguồn chung…" rồi "Đã ghép xong: video 1 (…s), video 2 (…s)…". File ghép nằm ở
     `jobs\<job>\source\montage.mp4` (mở thử bằng trình phát video: các video nối liền, cùng khung).
   - Mở draft: cảnh được lấy từ hầu hết các video, mỗi video một chút, ghép thành một video mới có chủ đề chung
     (tiêu đề nói về chủ đề đó); cảnh gay cấn ở đầu.
   - Video ngang / dọc lẫn lộn: khung chung theo hướng đa số, phần thiếu thêm viền đen.
4. Ghép nhiều video không dùng được với "Chỉ thay tiếng" (tool báo lỗi), và không chia video.
5. Chỉnh độ dài mỗi cảnh: `config\hype.yaml` (`min_clip_s`, `max_clip_s`); tỉ lệ số video phải góp cảnh:
   `montage_min_share`.

## Bước 53 — Chỉ 2 dòng tiêu đề phía trên, nền trắng, chữ đen `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **🔁 Dựng lại draft** (dòng tiêu đề dưới cũ tự bỏ, không cần
   hỏi lại AI).
2. Mở draft trong CapCut: nền trắng; 2 dòng tiêu đề chữ đen phía trên khối video; phía dưới khối video không còn tiêu đề.
3. Xem phụ đề, nhãn chủ đề (nằm trong khối video) vẫn đọc rõ; video dọc kín màn (chế độ Chỉ thay tiếng): chữ tiêu đề đen
   viền trắng đè lên hình — xem có đọc được không.
4. Chỉnh: `config\layout.yaml → four_titles`: `background_color` (vd `"#000000FF"` = đen), `title_styles` (màu chữ),
   `bottom_titles: true` = có lại 2 dòng dưới.

## Bước 52 — Thuyết minh "AI xem video rồi viết mới" (không dịch) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ: chọn **🌐 Đổi ngôn ngữ video** → ô **✍️ Cách viết lời thuyết minh**:
   - "AI xem video rồi VIẾT MỚI nội dung hợp nước đó" (mặc định) — hoặc "Dịch sát lời gốc" như trước.
   Dùng được cho cả chế độ thường lẫn "Chỉ thay tiếng".
3. Tới bước chờ voice: đọc kịch bản (cột 🇻🇳 nghĩa tiếng Việt) — các câu là lời kể MỚI theo kiểu TikTok nước đó
   (mở bằng câu cuốn hút, bình luận / giải thích điều đang thấy), không phải bản dịch từng câu; vẫn đúng sự việc trên
   hình, không có tên / số liệu / lời hứa bịa ra. Cột "lời dẫn" ghi trên hình đang có gì.
4. Nhật ký bước dub có dòng "Đang hỏi đạo diễn AI (dub_rewrite)". Bước này gửi ~16 khung hình nên lâu hơn dịch chút.
5. Đổi mặc định: `config\dub.yaml` → `default_script_mode: translate`; số khung hình `rewrite.frames`.

## Bước 51 — Chỉ thay tiếng + Giữ nhạc nền gốc `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn `start.bat`. Cài Demucs một lần (xem docs/SETUP_WINDOWS.md, mục Demucs):
   ```powershell
   .\.venv\Scripts\python -m pip install -r requirements-bgm.txt
   .\.venv\Scripts\python -c "import demucs; print('Demucs OK')"
   ```
2. Mở lại `start.bat`. Trang chủ: chọn ngôn ngữ ở **🌐 Đổi ngôn ngữ video**, tick **🎙️ Chỉ thay tiếng** và
   **🎵 Giữ nhạc nền gốc** → Bắt đầu.
3. Tới bước dựng (sau khi tải voice), nhật ký có "Tách nhạc nền khỏi giọng nói… (Demucs)" rồi "Đã tách xong nhạc nền
   gốc" (lần đầu tải model ~80 MB; CPU mất vài phút). File tách lưu ở `jobs\<job>\analysis\audio\bgm_00.wav` — nghe
   thử: còn nhạc / tiếng nền, gần như không còn giọng nói.
4. Mở draft trong CapCut: có rãnh nhạc nền gốc (bgm_00.wav) chạy khớp hình, nhỏ đi khi voice thuyết minh nói; không có
   nhạc thư viện CapCut thêm vào; tiếng nói gốc không còn.
5. Chưa cài Demucs: job vẫn xong, nhật ký báo "Không giữ được nhạc nền gốc — dùng nhạc AI chọn thay thế".
6. Chỉnh: `config\dub.yaml → voice_only → keep_bgm` (`volume_db`, `duck_db`, `device`).

## Bước 50 — Giữ lại đoạn AI cho là vi phạm chính sách TikTok `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Mở một job có khung **🚫 Đoạn AI cho là vi phạm chính sách TikTok** (trang Xong, hoặc bước Xác nhận thể loại).
3. Tick ô **Giữ lại** ở đoạn muốn giữ → **💾 Lưu: giữ lại các đoạn đã tick** → xác nhận.
   - Job đã có kế hoạch dựng: tool tự lập lại kế hoạch (job Đổi ngôn ngữ: viết lại thuyết minh, voice cũ cất `*_cu`)
     rồi dựng lại draft. Mở draft: đoạn đó đã có mặt.
   - Đang ở bước Xác nhận thể loại: chỉ lưu lựa chọn, bấm Tiếp tục như bình thường.
4. Tiêu đề khung đổi thành "cắt X, giữ lại Y". Bỏ tick + Lưu = cắt lại như cũ.

## Bước 49 — Sửa lỗi bước write "Đoạn âm thanh vượt quá độ dài file video01_dubNN.wav" `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Mở job bị lỗi → **Chạy lại bước này** → job phải qua bước write tới Xong.
3. Mở draft trong CapCut: voice các câu được tăng tốc vẫn phát đủ câu, không bị cụt chữ cuối.

## Bước 48 — Chế độ "Chỉ thay tiếng" (giữ nguyên hình) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ: chọn **🌐 Đổi ngôn ngữ video** (Hàn / Nhật / Anh) + tick **🎙️ Chỉ thay tiếng — giữ NGUYÊN hình** → Bắt đầu.
   (Tick mà chưa chọn ngôn ngữ → tool báo "Chưa chọn ngôn ngữ".)
3. Job chạy qua phân tích → AI hiểu nội dung → kế hoạch (tiêu đề, nhạc, hiệu ứng) → viết thuyết minh → chờ voice.
   Không có bước hook, không có bảng chia video.
4. Thu voice, tải lên (từng câu hoặc một file cả bài). Mở draft trong CapCut, kiểm tra:
   - video dài đúng bằng video gốc, không bị cắt, không đổi thứ tự, không zoom / lật / tua nhanh;
   - khung video đúng tỉ lệ gốc (video ngang: khối ngang giữa màn, tiêu đề trên/dưới; video dọc: kín màn, tiêu đề và
     phụ đề đè lên hình — xem dòng dưới cùng có bị caption / tên tài khoản TikTok che không);
   - tiếng gốc tắt, chỉ còn voice mới + nhạc nền NHỎ + hiệu ứng / SFX.
5. Chỉnh: `config\dub.yaml` → `voice_only` (độ to nhạc `music_base_db`, `allow_filter`, `allow_emphasis`);
   vị trí chữ khi video dọc: `config\layout.yaml` → `overlay`.

## Bước 47 — Chống đè tiếng thuyết minh khi video gốc nói nhiều `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ đã có voice: bấm **🔁 Dựng lại draft**.
2. Mở draft trong CapCut, xem rãnh âm thanh voice: các đoạn voice KHÔNG chồng lên nhau; câu nào dài thì nói nhanh hơn
   chút (≤ 1.4x) hoặc lùi lại một chút rồi bắt kịp ở chỗ lặng. Nghe thử xem lời còn khớp hình không.
3. Trang job → khung thu voice: dòng "🎚️ Giọng bạn đọc ~X ký tự/giây" (tool đã nhớ để lần sau AI viết câu vừa giọng —
   lưu trong `config\local.yaml`).
4. Nếu có câu 🔴: bấm **✂️ Viết gọn N câu 🔴** → AI viết lại ngắn hơn đúng các câu đó (câu khác giữ nguyên), voice cũ
   cất thành `*_cu.wav`, trang báo thiếu đúng các file đó → thu lại, tải lên → tool dựng tiếp.
5. Job mới với video nói rất nhiều: nhật ký / kịch bản ngắn gọn hơn lời gốc (AI được dặn nén ý còn ~75%).
6. Chỉnh: `config\dub.yaml` → `hard_max_speed`, `max_delay_s`, `write_cps_factor`, `dense_ratio`, `dense_keep`,
   `use_measured_rate`.

## Bước 46 — Lỗi bước dub "Đạo diễn trả kết quả sai khuôn 3 lần": tự sửa + tùy chọn dùng bản gần nhất `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Mở job bị lỗi ở bước dub → **Chạy lại bước này**. Nhật ký giờ có các dòng "Tự sửa: gộp câu thuyết minh…" /
   "…vắt qua 2 clip → thu về…" — tool tự sửa thay vì bắt AI viết lại; câu ngắn mà còn khoảng lặng phía sau không bị
   báo lỗi "ký tự/giây" nữa.
3. Nếu AI vẫn còn lỗi sau 3 lần: trang lỗi có khung **🛟 Tùy chọn: dùng bản thuyết minh gần nhất** liệt kê lỗi còn lại →
   bấm **✅ Dùng bản này, bỏ qua lỗi còn lại** → job chạy tiếp tới bước thu voice (không hỏi lại AI).
4. Muốn luôn tự dùng bản gần nhất không cần bấm: `config\dub.yaml` → `accept_imperfect: true`.

## Bước 45 — Phụ đề tiếng Việt để kiểm tra khớp (chế độ Đổi ngôn ngữ) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job Đổi ngôn ngữ cũ: bấm **🔁 Dựng lại draft**.
2. Mở draft trong CapCut: ngay dưới phụ đề chính (tiếng Hàn / Nhật / Anh) có dòng chữ vàng nhỏ tiếng Việt = nghĩa câu
   đang nói, xuất hiện cùng lúc với câu đó. Xem: voice, phụ đề, nghĩa tiếng Việt có khớp với hình không; chữ Việt có
   bị đè / tràn khung không (font CapCut hiện đủ dấu tiếng Việt không).
3. Trước khi xuất đăng TikTok: trang job → **🇻🇳 Phụ đề tiếng Việt → 🚫 Tắt phụ đề tiếng Việt và dựng lại** → mở lại
   draft, dòng chữ vàng đã biến mất.
4. Chỉnh cỡ / màu / vị trí: `config\dub.yaml` → `vi_subtitles` (`enabled: false` = job mới mặc định tắt).

## Bước 44 — Voice thuyết minh khớp hình cho video nói liên tục (thu một file cả bài) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Tạo job **Đổi ngôn ngữ** với một video nói liên tục (vd hướng dẫn trang điểm). Tới bước chờ voice:
   - mỗi câu ghi **chỗ X s · tối đa Y s** (= thời gian cần đọc vừa);
   - `dub_scripts.txt` trong thư mục job có cùng thông tin + hướng dẫn thu một file.
3. Trong Voice Studio đọc CẢ kịch bản theo thứ tự vào MỘT file, **nghỉ khoảng 1 giây giữa các câu** (không nghỉ lâu
   giữa câu). Tải lên ở ô **Một file cả bài → ✂️ Tải lên và tự cắt**.
4. Kiểm tra: thư mục `jobs\<job>\voice\` có đủ `video01_dub01.wav`, `dub02.wav`… mỗi file đúng một câu (nghe thử vài
   file). Trên trang job mỗi câu có đèn: 🟢 khớp · 🟡 tool tự tăng tốc nhẹ · ⚪ ngắn · 🔴 quá dài.
5. Câu 🔴: thu lại riêng câu đó, đặt đúng tên (vd `video01_dub07.wav`), tải ở ô chọn nhiều file → bấm 🔁 Dựng lại draft.
6. Mở draft trong CapCut: lời thuyết minh khớp với động tác trên hình (câu "kẻ mắt" phát lúc đang kẻ mắt), không có
   2 câu đè lên nhau.
7. Nếu tool báo "chỉ có N chỗ nghỉ": thu lại và nghỉ lâu hơn giữa các câu (~1 giây).

## Bước 43 — Kiểu dựng mới "Trang điểm / làm đẹp" (`makeup`) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Tạo job với một footage trang điểm. Bước AI hiểu nội dung nên tự đề xuất "Trang điểm / làm đẹp" (bật
   "Xác nhận trước khi dựng" để xem / tự chọn kiểu này).
3. Mở draft trong CapCut, kiểm tra:
   - 1–3 giây đầu là look hoàn thiện, sau đó mới tới mặt mộc và các bước theo đúng thứ tự;
   - đoạn tán nền / đánh lặp chạy nhanh (1.5–2x), đoạn kẻ mắt / môi chạy tốc độ thường;
   - chữ nhấn tên bước nền hồng nằm phía trên, không che mặt; mũi tên HỒNG chỉ đúng vùng đang trang điểm
     (font CapCut có hiện ký tự → không);
   - cuối video: clip quay chậm khoe kết quả, có nhãn 完成 / 완성 / FINAL LOOK.
4. Muốn chỉnh liều lượng: sửa `styles\makeup.yaml` (phần `director_brief`, màu chữ, màu mũi tên `arrow`).

## Bước 42 — Sửa lỗi bước analyze "Could not open encoder before EOF" (trích khung hình) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Mở job bị lỗi → bấm **Chạy lại bước này** (bước analyze).
3. Job phải qua được bước "Trích khung hình". Nếu nhật ký có dòng "Bỏ qua N khung hình không trích được…" là bình
   thường (phần cuối file chỉ có tiếng, không có hình).
4. Nếu vẫn lỗi: chạy trong PowerShell và gửi lại kết quả cho Claude:
   ```powershell
   ffmpeg -version
   ffprobe -v error -show_entries stream=codec_name,pix_fmt,width,height,duration -of compact "ĐƯỜNG_DẪN_VIDEO"
   ```

## Bước 41 — Bỏ khung cố định 3:4 và bỏ che chữ in sẵn `[CẦN KIỂM TRA TRÊN MÁY]`

(Bước 38 và phần che chữ ở các bước trước không còn áp dụng.)

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **🔁 Dựng lại draft**.
2. Trang chủ: ô **Khung video** (4:3 / 1:1 / 16:9 / Tự động) giờ là khung video THẬT trên màn như trước Bước 38.
3. Mở draft trong CapCut: khung video đúng tỉ lệ đã chọn; không còn 2 dải nền đen (ảnh `frame_band_...png`) trên/dưới
   khung; tiêu đề, phụ đề, nhãn dời theo khung, không đè lên video.
4. Footage có chữ in sẵn: tool KHÔNG còn cắt tránh hay đặt dải che (nhật ký không còn dòng "che chữ in sẵn").
   Muốn bật lại: `config\text_cover.yaml` → `enabled: true`.

## Bước 40 — Sửa lỗi "Dự án mẫu thiếu khuôn cho loại 'video'" `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Mở job bị lỗi ở bước write → bấm **Chạy lại bước này**.
3. Nhật ký có dòng "Dự án mẫu '…' thiếu lớp video → mượn khuôn từ dự án mẫu có sẵn trong tool" và job chạy tiếp
   đến Xong. Mở draft trong CapCut: clip video hiện đúng, phát được.
4. Cách gốc rễ: trang chủ → ⚙️ **Dự án mẫu CapCut** → chọn dự án có đủ clip video, chữ, âm thanh (hoặc chọn
   "mẫu có sẵn trong tool").

## Bước 39 — Chọn nhạc nền khi tạo video (không chọn = AI chọn) `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Trang chủ → ô **🎵 Nhạc nền**:
   - để "✨ AI tự chọn theo nội dung" = như cũ;
   - hoặc chọn một bài trong danh sách (nhóm "Nhạc CapCut" / "Kho của bạn"), kèm độ dài, tâm trạng, nhãn Commercial;
   - hoặc tải lên file nhạc của bạn (.mp3/.wav/.m4a) — tự vào kho `assets\music\tu_chon\` và sổ nguồn.
3. Tạo job, nhật ký bước kế hoạch dựng có dòng "Nhạc nền theo lựa chọn của bạn: …". Mở draft: đúng bài đã chọn.
4. Trang Xong → **🎵 Đổi nhạc nền**: chọn bài khác → tool chỉ dựng lại draft (không hỏi lại AI, nhanh); chọn
   "AI tự chọn" → AI lập lại kế hoạch dựng.
5. Lưu ý: khách doanh nghiệp mà bạn tự chọn bài không có nhãn Commercial thì tool vẫn dùng bài bạn chọn.

## Bước 38 — Khung video cố định 3:4 (zoom chỉ trong khung), crop là chuyện riêng `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **🔁 Dựng lại draft**.
2. Mở draft trong CapCut, kiểm tra:
   - khung video giữa màn LUÔN 3:4 (1080×1440, cao gần hết màn 9:16) ở mọi kiểu dựng (cả thể thao);
   - lúc zoom to / lia / cắt cận theo người: hình phóng to BÊN TRONG khung, viền khung trên/dưới đứng yên.
     Tool đặt 2 dải nền đen (ảnh PNG `_tool_assets\frame_band_...png` trong thư mục draft CapCut) trên / dưới khung để
     che phần hình tràn ra — kiểm tra 2 dải này hiện đúng, CapCut mở được ảnh, và nằm DƯỚI chữ tiêu đề;
   - 4 dòng tiêu đề nằm trong 2 dải còn lại (240 px mỗi dải) — chữ không đè video, không chồng nhau. Dải hẹp nên dòng
     tiêu đề dưới cùng nằm sát vùng caption TikTok: xem trên điện thoại có bị che không.
3. Ô **Vùng crop từ video gốc** (trang chủ): 4:3 / 1:1 / 16:9 chọn phần lấy từ video gốc, sau đó phần đó được lấp đầy
   khung 3:4. Với footage ngang 16:9 cả 3 lựa chọn cho kết quả gần như nhau (đều lấy dải 3:4 cao bằng khung gốc,
   bám theo người); khác biệt rõ khi footage dọc.
4. Muốn đổi khung: `config\layout.yaml` → `frame_ratio` (xóa dòng = dùng lựa chọn ở trang chủ làm khung),
   `frame_lock: false` = không che phần tràn.

## Bước 37 — Nút ⏹️ Dừng job `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`.
2. Tạo một job, khi trang job đang chạy bấm **⏹️ Dừng** → xác nhận.
   - Đang hỏi đạo diễn AI: dừng gần như ngay (tiến trình `claude` bị tắt). Trong Task Manager không còn `claude` chạy cho job đó.
   - Đang phân tích video (nhận dạng thoại / dò cảnh): dừng ở lần báo tiến trình kế tiếp — có thể mất thêm một lúc.
   - Đang xếp hàng: bỏ khỏi hàng đợi ngay.
   Trong lúc chờ, trang hiện "Đang dừng…".
3. Job chuyển sang **⏹️ Đã dừng** (nhãn xám). Kết quả các bước đã xong vẫn giữ; bấm **▶️ Chạy tiếp từ bước này** để chạy lại
   từ bước đang dở. Hoặc 🗑️ Xóa job nếu không cần nữa.
4. Thử dừng khi đang chạy 2–3 video cùng lúc: chỉ video được bấm dừng, video khác chạy tiếp bình thường.

## Bước 36 — Chữ 4 dòng tiêu đề giảm từ cỡ 30 xuống 20 `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng hẳn và mở lại `start.bat`. Job cũ: bấm **🔁 Dựng lại draft**.
2. Mở draft trong CapCut, bấm vào một dòng tiêu đề → ô Cỡ chữ hiện **20**, tỉ lệ (scale) **100%** hoặc nhỏ hơn
   (dòng quá dài tự thu nhỏ cho vừa khung). Chữ không còn được phóng to thêm như trước.
3. Muốn đổi cỡ: `config\layout.yaml` → `title_size` (và `title_scale_max: 1.0` để giữ đúng cỡ đó).

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
