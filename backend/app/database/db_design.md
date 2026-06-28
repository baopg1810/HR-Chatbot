# Database Design - HR Policy Chatbot

## 1. users

Lưu thông tin nhân viên để xác thực JWT và cá nhân hóa câu trả lời.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | ID của user |
| employee_code | VARCHAR UNIQUE | Mã nhân viên |
| email | VARCHAR UNIQUE | Email đăng nhập |
| password_hash | VARCHAR | Mật khẩu đã hash |
| full_name | VARCHAR | Họ tên |
| department | VARCHAR | Phòng ban |
| position | VARCHAR | Chức vụ |
| employment_type | VARCHAR | Loại hợp đồng (Full-time, Intern, ...) |
| role | VARCHAR | employee / hr / admin |
| is_active | BOOLEAN | Trạng thái tài khoản |
| created_at | TIMESTAMP | Thời gian tạo |
| updated_at | TIMESTAMP | Thời gian cập nhật |

---

## 2. documents

Lưu thông tin tài liệu chính sách.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | ID tài liệu |
| title | VARCHAR | Tên tài liệu |
| file_name | VARCHAR | Tên file |
| file_url | TEXT | Đường dẫn file |
| document_type | VARCHAR | leave / benefit / remote / contract |
| version | VARCHAR | Phiên bản |
| status | VARCHAR | active / archived |
| created_at | TIMESTAMP | Ngày tạo |
| updated_at | TIMESTAMP | Ngày cập nhật |

---

## 4. chat_sessions

Mỗi cuộc hội thoại của user.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | Session ID |
| user_id | UUID (FK -> users.id) | Chủ session |
| title | VARCHAR | Tiêu đề hội thoại |
| created_at | TIMESTAMP | Ngày tạo |
| updated_at | TIMESTAMP | Ngày cập nhật |

---

## 5. chat_messages

Lưu từng message trong cuộc hội thoại.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | Message ID |
| session_id | UUID (FK -> chat_sessions.id) | Session |
| user_id | UUID (FK -> users.id) | Người gửi |
| role | VARCHAR | user / assistant |
| content | TEXT | Nội dung |
| created_at | TIMESTAMP | Thời gian tạo |
---

## 6. query_logs

Lưu log câu hỏi để phân tích.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | ID log |
| user_id | UUID (FK -> users.id) | Người hỏi |
| session_id | UUID (FK -> chat_sessions.id) | Session |
| question | TEXT | Câu hỏi gốc |
| normalized_question | TEXT | Câu hỏi chuẩn hóa |
| intent | VARCHAR | Ý định |
| topic | VARCHAR | Chủ đề |
| department | VARCHAR | Phòng ban |
| created_at | TIMESTAMP | Thời gian |

### Ví dụ

```
question: Tôi được nghỉ phép bao nhiêu ngày?
normalized_question: nghỉ phép năm
intent: ask_policy
topic: leave_policy
```

---

## 7. trend_questions

Lưu các chủ đề hoặc câu hỏi đang trend.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | ID |
| topic | VARCHAR | Chủ đề |
| normalized_question | TEXT | Câu hỏi chuẩn hóa |
| question_count | INTEGER | Tổng số lượt hỏi |
| unique_user_count | INTEGER | Số user khác nhau |
| time_window | VARCHAR | daily / weekly / monthly |
| start_time | TIMESTAMP | Bắt đầu thống kê |
| end_time | TIMESTAMP | Kết thúc thống kê |
| is_pinned | BOOLEAN | Có ghim hay không |
| created_at | TIMESTAMP | Ngày tạo |

Ví dụ:

```
topic: remote_work
normalized_question: chính sách làm việc remote
question_count: 45
unique_user_count: 28
```

---


## 8. tickets

Tạo ticket khi chatbot không giải quyết được.

| Column | Type | Description |
|----------|----------|----------------------------|
| id | UUID (PK) | Ticket ID |
| user_id | UUID (FK -> users.id) | Người tạo |
| session_id | UUID (FK -> chat_sessions.id) | Session liên quan |
| question | TEXT | Nội dung cần hỗ trợ |
| status | VARCHAR | open / in_progress / resolved / closed |
| priority | VARCHAR | low / medium / high |
| assigned_to | UUID (FK -> users.id) | HR phụ trách |
| created_at | TIMESTAMP | Ngày tạo |
| updated_at | TIMESTAMP | Ngày cập nhật |

---