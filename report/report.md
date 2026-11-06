# Báo Cáo Bài Tập Lớn Môn Mạng Máy Tính

## Thông tin sinh viên
* **Họ và tên:** Nguyễn Anh Vũ
* **Mã sinh viên:** 24020695
---

## Báo cáo chi tiết quá trình làm bài

Dưới đây là phần tóm tắt những gì em đã thêm và sửa trong từng file:

### 1. Phần 1 & Phần 2: Bản cơ bản (`RTP-base`)

#### File `receiver.py` (Bên nhận):
Nhìn vào code mẫu ban đầu thầy cho, em thấy còn thiếu các logic để xử lý giao thức tin cậy, nên em đã bổ sung các phần sau:
* **Sửa chỗ kiểm tra Checksum:** Ở code mẫu, khi checksum bị sai thì chương trình chỉ in ra chữ `checksums not match` rồi vẫn chạy tiếp in dữ liệu. Em đã sửa lại thành lệnh `continue` để nếu gói tin bị lỗi bit do mạng làm hỏng thì vứt bỏ luôn, không nhận và không gửi ACK.
* **Xử lý gói bắt tay START (type = 0):** Khi bên gửi bắt đầu kết nối, em cho `expected_seq = 1` và gửi lại gói ACK số 1 để bên gửi biết đường truyền dữ liệu.
* **Xử lý gói DATA (type = 2):**
  * Em tạo biến `expected_seq` để nhớ xem mình đang chờ gói số mấy (bắt đầu từ 1) và một từ điển `buffer = {}` để lưu tạm các gói đến lộn xộn.
  * Nếu gói đến có `seq_num` nằm ngoài cửa sổ tiếp nhận thì em bỏ qua.
  * Nếu gói cũ (`seq_num < expected_seq`): chứng tỏ gói này em nhận rồi nhưng bên gửi chưa nhận được ACK nên gửi lại, em gửi lại ACK `expected_seq` để nhắc bên gửi.
  * Nếu gói đến sớm (`seq_num > expected_seq`): em cất tạm dữ liệu vào `buffer[seq_num]` và vẫn gửi lại ACK `expected_seq`.
  * Nếu đúng gói đang đợi (`seq_num == expected_seq`): em ghi dữ liệu ra `sys.stdout.buffer`, tăng `expected_seq` lên 1, sau đó kiểm tra xem trong `buffer` có sẵn các gói tiếp theo không thì lôi ra in nốt, rồi gửi Cumulative ACK báo số thứ tự tiếp theo cần nhận.
* **Xử lý gói kết thúc END (type = 1):** Khi bên gửi báo hết dữ liệu và em đã nhận đủ các gói trước đó, em gửi lại một gói ACK xác nhận rồi dùng lệnh `break` để đóng socket và thoát chương trình.

#### File `sender.py` (Bên gửi):
* **Cắt nhỏ dữ liệu:** Em dùng `sys.stdin.buffer.read()` để đọc toàn bộ dữ liệu vào, sau đó cắt thành từng mẩu nhỏ tối đa 1456 bytes để cộng thêm 16 bytes Header thì gói tin không bị vượt quá giới hạn 1500 bytes của mạng.
* **Gửi gói START:** Em gửi gói START có `seq_num = 0` và dùng vòng lặp đợi cho đến khi nhận được ACK số 1 từ bên nhận thì mới bắt đầu gửi các gói dữ liệu.
* **Cửa sổ trượt Go-Back-N:**
  * Em dùng 2 biến con trỏ là `base = 1` và `next_seq = 1`.
  * Đầu tiên, em gửi trước một loạt gói để lấp đầy cửa sổ `window_size`.
  * Em đặt bộ đếm giờ `s.settimeout()` tối đa 500ms:
    * Mỗi khi nhận được ACK mới có `ack_seq > base`, em trượt cửa sổ lên bằng cách gán `base = ack_seq`, reset lại thời gian và gửi tiếp các gói mới vào cửa sổ.
    * Nếu hết 500ms mà không nhận được ACK mới (bị mất gói hoặc mất ACK), chương trình nhảy vào `except socket.timeout:`, em cho vòng lặp gửi lại toàn bộ các gói đang nằm trong cửa sổ từ `base` đến `next_seq - 1`.
* **Gửi gói END:** Sau khi toàn bộ các gói dữ liệu đã được ACK xong, em gửi gói END báo hết file và chờ tối đa 500ms, nếu nhận được ACK hoặc hết giờ thì đóng socket thoát chương trình.

---

### 2. Phần 3: Bản tối ưu (`RTP-opt`)

Ở bản cơ bản `RTP-base`, nếu chẳng may bị mất 1 gói ở giữa thì bên gửi phải gửi lại toàn bộ các gói sau đó dù bên nhận đã nhận được rồi, rất lãng phí mạng. Vì vậy ở phần này em sửa lại theo cơ chế Selective Repeat:

#### File `receiver.py` (Bên nhận):
* Em không gửi ACK tích lũy nữa. Cứ nhận được gói dữ liệu số mấy thì em gửi trả lại đúng số thứ tự của gói đó: `send_ack(s, address, pkt_header.seq_num)`. Các gói đến trước vẫn được lưu tạm vào `buffer` chờ gói thiếu đến đủ mới in ra màn hình.

#### File `sender.py` (Bên gửi):
* Em tạo thêm một tập hợp `acked = set()` để ghi nhớ xem những gói nào đã nhận được ACK.
* Khi nhận được ACK của gói nào thì em thêm vào `acked`. Nếu gói ở đáy cửa sổ (`base`) đã nằm trong `acked` rồi thì em trượt `base` lên đến gói chưa được ACK đầu tiên.
* **Điểm tối ưu quan trọng nhất:** Khi bị timeout 500ms, thay vì gửi lại cả cửa sổ như bản base, em chỉ duyệt gửi lại những gói nào trong cửa sổ mà chưa có trong `acked` (`if seq not in acked:`).

---

## Kết quả chạy kiểm thử
Em đã chạy kiểm tra cả 2 bản `RTP-base` và `RTP-opt` với script test và proxy giả lập 4 lỗi mạng của thầy (`0123: delay, reorder, drop, jam`). Kết quả so sánh file gửi và file nhận bằng script `compare.sh` đều báo trùng khớp 100%:
`SUCCESS: Message received matches message sent!`