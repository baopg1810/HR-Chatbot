# HR Helpdesk AI

HR Helpdesk AI là ứng dụng helpdesk nội bộ cho phòng nhân sự. Sản phẩm dùng AI để trả lời câu hỏi về chính sách HR từ tài liệu đã upload, hiển thị nguồn trích dẫn, kiểm soát quyền truy cập theo vai trò/phòng ban, hỗ trợ tra cứu chỉ số HR cá nhân, tạo ticket khi cần HR xử lý và phát hiện các chủ đề đang được hỏi nhiều.

## Tổng quan

Ứng dụng phù hợp cho công ty có nhiều tài liệu HR như sổ tay nhân viên, chính sách nghỉ phép, bảo hiểm, hợp đồng, lương thưởng, onboarding/offboarding hoặc quy định nội bộ. Thay vì để nhân viên tự tìm trong nhiều file hoặc hỏi HR lặp lại cùng một câu, HR Helpdesk AI cung cấp giao diện chat có RAG, guardrails và luồng escalation rõ ràng.

Các chức năng chính:

- Chat hỏi đáp chính sách HR dựa trên tài liệu nội bộ đã được lập chỉ mục.
- Trả lời có citations để người dùng kiểm chứng nguồn.
- Lọc tài liệu theo `role` và `department` trước khi sinh câu trả lời.
- Tra cứu chỉ số HR cá nhân như ngày phép còn lại, trạng thái bảo hiểm và xét duyệt khen thưởng.
- Guardrails đầu vào/đầu ra/tool để chặn jailbreak, câu hỏi ngoài phạm vi và yêu cầu dữ liệu riêng tư của người khác.
- Luồng tạo ticket có nháp do AI điền sẵn, hỏi bổ sung khi thiếu thông tin và yêu cầu người dùng xác nhận trước khi gửi.
- HR admin upload/xóa tài liệu, quản lý ticket, chạy trending detection và pin chủ đề nổi bật.
- Lưu lịch sử chat/session, feedback và query log để phục vụ cải thiện chất lượng.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, SQLAlchemy async, Alembic, Pydantic |
| Agent orchestration | LangGraph state graph |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Database | SQLite cho local/test, Postgres cho production pilot |
| Retrieval | Chroma persistent vector store, hybrid semantic + lexical scoring |
| AI | Gemini generation, embeddings, streaming và tool choice |
| Rerank | Cohere rerank |
| Guardrails | Rule-based safeguards + optional Groq/OpenAI safeguard provider + topic classifier |
| Observability | Python logging, optional Langfuse |
| Deploy | Docker, Docker Compose, Uvicorn |

## Yêu cầu môi trường

- Python 3.11+
- Node.js 18+ và npm
- Git
- Docker và Docker Compose nếu chạy bằng container
- Gemini API key nếu muốn dùng model thật: `GOOGLE_API_KEY` hoặc `GOOGLE_API_KEYS`
- Cohere API key cho rerank: `COHERE_API_KEY`
- Groq/OpenAI key nếu muốn dùng safeguard provider ngoài rule-based fallback: `GROQ_API_KEY`/`GROQ_API_KEYS` hoặc `OPENAI_API_KEY` khi dùng `SAFEGUARD_PROVIDER=openai`

## Cài đặt local

Chạy các lệnh sau ở thư mục gốc của project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nếu repo đã có sẵn `.venv`, bạn có thể bỏ qua bước tạo virtualenv và chỉ chạy lệnh install dependencies.

Sau khi copy `.env.example`, đặt database local rõ ràng nếu file `.env` đang để trống:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

Các biến môi trường quan trọng nằm trong `.env`:

| Biến | Ý nghĩa |
| --- | --- |
| `APP_ENV` | `development` cho local, `production` cho deploy, `test` cho test isolation |
| `DATABASE_URL` | Local nên đặt `sqlite+aiosqlite:///./data/app.db`; production dùng Postgres |
| `CHROMA_PERSIST_DIR` | Thư mục lưu Chroma vector store, mặc định `./data/chroma` |
| `GOOGLE_API_KEY` / `GOOGLE_API_KEYS` | Gemini API key cho generation, embeddings, tool choice và topic classifier |
| `MODEL_NAME` | Model Gemini dùng để sinh câu trả lời |
| `EMBEDDING_MODEL_NAME` | Model embedding |
| `COHERE_API_KEY` | API key cho rerank |
| `ONLINE_LLM_TESTS` | `1` mặc định: pytest gọi provider thật; đặt `0` khi cần debug offline deterministic fallback |
| `SAFEGUARD_PROVIDER` | `groq` mặc định hoặc `openai` |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | API key cho safeguard provider tương ứng |
| `JWT_SECRET_KEY` | Secret ký JWT; local có thể dùng default, production phải đổi |
| `CORS_ORIGINS` | Origin frontend được phép gọi API, mặc định `http://localhost:3000` |
| `CHAT_RATE_LIMIT_COUNT` / `CHAT_RATE_LIMIT_WINDOW_SECONDS` | Giới hạn tốc độ chat theo cửa sổ thời gian |

## Chạy project

### 1. Chạy backend

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Khi chạy ở `APP_ENV=development`, backend tự tạo bảng local và seed demo users nếu chưa có.

Backend URLs:

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Liveness: http://localhost:8000/health/live
- Readiness: http://localhost:8000/health/ready
- Static/bundled app: http://localhost:8000/app

### 2. Chạy frontend

Mở terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- React dev app: http://localhost:3000

Frontend mặc định gọi API tại `http://localhost:8000/api/v1` khi chạy dev. Nếu cần đổi API URL, tạo file `frontend/.env` và thêm:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Chuẩn bị dữ liệu lần đầu

Khi chạy sản phẩm lần đầu, kho tri thức chưa có tài liệu nên chatbot có thể trả lời rằng chưa tìm thấy nguồn HR phù hợp. Trước khi demo hoặc kiểm thử luồng hỏi đáp, hãy upload file sổ tay nhân viên có sẵn trong repo:

- File cần upload: [So_tay_nhan_vien.md](So_tay_nhan_vien.md)
- Tài khoản thực hiện: HR Admin `admin@example.com` / `admin123`
- Vị trí trong UI: đăng nhập HR Admin, mở menu **Kho tri thức**, chọn **Upload file chính sách**.
- Tên hiển thị gợi ý: `Sổ tay nhân viên`.
- Sau khi chọn file, bấm **Lập chỉ mục file upload** và đợi thông báo lập chỉ mục thành công.

Ứng dụng hỗ trợ upload tài liệu chính sách dạng `.docx`, `.md`, `.txt`. Sau khi tài liệu đã được index, đăng nhập bằng tài khoản Employee để hỏi các câu về thử việc, nghỉ phép, phúc lợi, kỷ luật, nội quy hoặc quy tắc ứng xử và kiểm tra citations trong câu trả lời.

## Tài khoản demo

Local development tự seed hai tài khoản sau:

| Role | Email | Password |
| --- | --- | --- |
| Employee | `employee@example.com` | `employee123` |
| HR Admin | `admin@example.com` | `admin123` |

Gợi ý demo nhanh:

1. Đăng nhập bằng tài khoản HR Admin.
2. Vào **Kho tri thức** và upload [So_tay_nhan_vien.md](So_tay_nhan_vien.md).
3. Đăng nhập bằng tài khoản Employee.
4. Hỏi: `Nhân viên thử việc trong bao lâu?` hoặc `Chính sách nghỉ phép được quy định như thế nào?`
5. Kiểm tra câu trả lời có citations.
6. Hỏi `Tôi còn bao nhiêu ngày nghỉ phép?` để kiểm tra luồng HR metrics cá nhân.
7. Yêu cầu `Tạo ticket giúp tôi về việc chậm lương tháng 6` để xem luồng nháp ticket và xác nhận gửi.
8. Đăng nhập HR Admin để xem/cập nhật ticket và chạy trending detection.

## API chính

Tất cả endpoint nghiệp vụ nằm dưới `/api/v1`.

| Nhóm | Endpoint chính |
| --- | --- |
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `GET /me`, `POST /auth/users` |
| Chat | `POST /chat`, `POST /chat/stream`, `GET /chat/sessions`, `GET /chat/sessions/{session_id}/messages`, `POST /chat/sessions/{session_id}/state/clear` |
| Documents | `POST /documents`, `POST /documents/upload`, `GET /documents`, `DELETE /documents/{document_id}` |
| Tickets | `POST /escalations`, `GET /tickets`, `GET /admin/tickets`, `PATCH /admin/tickets/{ticket_id}` |
| Trending | `GET /trending/pins`, `POST /admin/trending/run`, `GET /admin/trending/candidates`, `POST /admin/trending/candidates/{candidate_id}/pin` |
| Feedback | `POST /feedback` |
| HR metrics | `GET /me/hr-metrics` |

## Tests và checks

Backend:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check backend/app tests
```

Pytest mặc định bật `ONLINE_LLM_TESTS=1`, nên cần có key thật trong `.env`: `GOOGLE_API_KEY` hoặc `GOOGLE_API_KEYS`, `COHERE_API_KEY`, và guardrail key tương ứng với `SAFEGUARD_PROVIDER`. Chỉ đặt `ONLINE_LLM_TESTS=0` khi muốn debug offline deterministic fallback.

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Chạy bằng Docker Compose

Docker Compose build backend image, build React frontend vào image đó, chạy kèm Postgres và persist runtime data qua `data/`:

```bash
docker compose up --build
```

Sau khi build, backend phục vụ API tại `http://localhost:8000` và bundled React app tại `http://localhost:8000/app`.

## Production Pilot

Production startup không tự tạo bảng và không seed demo accounts. Trước khi chạy production cần migration database và tạo admin đầu tiên.

```bash
alembic upgrade head
PYTHONPATH=backend python scripts/bootstrap_admin.py \
  --email hr-admin@example.com \
  --password 'replace-with-a-strong-password' \
  --full-name 'HR Admin'
```

Các biến môi trường bắt buộc/khuyến nghị cho production:

- `APP_ENV=production`
- `DATABASE_URL=postgresql+psycopg://...`
- `JWT_SECRET_KEY` dài ít nhất 32 ký tự và không dùng default
- `JWT_ALGORITHM=HS256`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `GOOGLE_API_KEY` hoặc `GOOGLE_API_KEYS`
- `COHERE_API_KEY`
- `SAFEGUARD_PROVIDER=groq` kèm `GROQ_API_KEY`/`GROQ_API_KEYS`, hoặc `SAFEGUARD_PROVIDER=openai` kèm `OPENAI_API_KEY`
- `CORS_ORIGINS=https://your-frontend-domain`
- `CHROMA_PERSIST_DIR=/app/data/chroma`

## Troubleshooting

- **Không vào được frontend dev:** kiểm tra `npm run dev` có chạy ở port `3000` không.
- **Frontend không gọi được backend:** kiểm tra backend ở port `8000`, `CORS_ORIGINS=http://localhost:3000`, và `VITE_API_BASE_URL`.
- **Login demo thất bại:** đảm bảo backend đang chạy với `APP_ENV=development`; xóa database local trong `data/app.db` nếu muốn seed lại từ đầu.
- **Chat không có citations:** upload và index tài liệu trước, sau đó hỏi bằng user có quyền đọc tài liệu đó.
- **Readiness báo `model_provider: missing`:** thêm `GOOGLE_API_KEY` hoặc `GOOGLE_API_KEYS` vào `.env`.
- **Rerank lỗi thiếu key:** thêm `COHERE_API_KEY`; khi debug offline có thể đặt `ONLINE_LLM_TESTS=0`.
- **Guardrail provider lỗi:** kiểm tra `SAFEGUARD_PROVIDER` và key tương ứng; production có thể fail closed nếu provider lỗi.
- **Port 8000 hoặc 3000 bị chiếm:** đổi port trong lệnh `uvicorn` hoặc script Vite, rồi cập nhật API URL/CORS tương ứng.
- **Lỗi Chroma/vector store:** kiểm tra `CHROMA_PERSIST_DIR=./data/chroma` và quyền ghi vào thư mục `data/`.

## Cấu trúc project

```text
backend/app/
  agents/         LangGraph graph, nodes, tool choice, ticket draft agent
  api/            FastAPI routers và dependencies
  core/           config, security, logging, online test helpers
  database/       SQLAlchemy session/base
  guardrails/     rule/provider safeguards, topic classifier, schemas
  models/         SQLAlchemy models
  rag/            loaders, chunking, lexical retrieval helpers
  repository/     database access helpers
  schemas/        API/auth/document schemas
  services/       auth, documents, retrieval, LLM, tickets, feedback, trending
frontend/         React/Vite frontend
alembic/          Database migrations
tests/            API, agent, RAG và integration tests
scripts/          Seed, bootstrap, migration và local helper scripts
docs/             Architecture diagram và project guide
eval/             Golden dataset và benchmark results
presentation/     Demo/pitch materials
```
