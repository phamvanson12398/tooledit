# Hướng dẫn kiểm tra trên máy Windows

## Bước 14 — Nhạc nền to hơn 30% `[CẦN KIỂM TRA TRÊN MÁY]`

1. `git pull`, đóng và mở lại `start.bat`. Vào job cũ bấm **🔁 Dựng lại draft** (không tốn lượt AI), hoặc tạo job mới.
2. Mở draft trong CapCut, nghe: nhạc nền to hơn trước ~30%, vẫn tự nhỏ lại khi có người nói.
3. Muốn to/nhỏ nữa: sửa `music_gain` trong `config/audio.yaml` (1.3 = +30%, 1.5 = +50%, 1.0 = như cũ), rồi Dựng lại draft.

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
