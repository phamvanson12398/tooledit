# Hướng dẫn kiểm tra trên máy Windows

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
