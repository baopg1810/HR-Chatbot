# HR Helpdesk AI

HR Helpdesk AI là một ứng dụng helpdesk nội bộ cho phòng nhân sự. Sản phẩm dùng AI để trả lời câu hỏi về chính sách HR từ tài liệu nội bộ, hiển thị nguồn trích dẫn, kiểm soát quyền truy cập theo vai trò/phòng ban, tạo ticket khi cần HR xử lý và phát hiện các câu hỏi đang được hỏi nhiều.

## Tổng quan

Ứng dụng phù hợp cho các công ty có nhiều tài liệu HR như chính sách nghỉ phép, bảo hiểm, hợp đồng, lương thưởng, onboarding hoặc quy định nội bộ. Thay vì để nhân viên tự tìm trong nhiều file hoặc hỏi HR lặp lại cùng một câu hỏi, HR Helpdesk AI cung cấp một giao diện chat có RAG và quy trình escalation rõ ràng.

Các chức năng chính:

- Trả lời câu hỏi HR dựa trên tài liệu đã upload.
- Hiển thị citations để người dùng kiểm chứng nguồn trả lời.
- Lọc tài liệu theo `role` và `department` trước khi sinh câu trả lời.
- Cho nhân viên xem các chỉ số HR của chính mình qua adapter an toàn.
- Chặn câu hỏi jailbreak, ngoài phạm vi hoặc yêu cầu dữ liệu riêng tư của người khác.
- Tạo ticket khi câu hỏi nhạy cảm, thiếu thông tin hoặc cần HR xử lý.
- Cho HR admin upload/xóa tài liệu, quản lý ticket và chạy trending detection.
- Thu thập feedback để đánh giá chất lượng câu trả lời.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, SQLAlchemy async, Alembic, Pydantic |
| Frontend | React 18, Vite, TypeScript |
| Database | SQLite cho local dev/test, Postgres cho production pilot |
| Retrieval | Chroma persistent vector store + lexical scoring |
| AI | Gemini generation và embedding models; local deterministic fallback cho dev/test |
| Rerank | Cohere rerank |
| Security | JWT access/refresh tokens, DB-backed user lookup, RBAC helpers |
| Deploy | Docker, Docker Compose, Uvicorn |

## Yêu cầu môi trường

- Python 3.11+
- Node.js 18+ và npm
- Git
- Docker và Docker Compose nếu chạy production/pilot bằng container
- Gemini API key nếu muốn dùng model thật: `GOOGLE_API_KEY` hoặc `GOOGLE_API_KEYS`
- Cohere API key nếu muốn bật rerank thật: `COHERE_API_KEY`

## Cài đặt local

Chạy các lệnh sau ở thư mục gốc của project.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nếu repo đã có sẵn `.venv`, bạn có thể bỏ qua bước tạo virtualenv và chỉ chạy lệnh install dependencies.

Các biến môi trường quan trọng nằm trong `.env`:

| Biến | Ý nghĩa |
| --- | --- |
| `APP_ENV` | `development` cho local, `production` cho deploy |
| `DATABASE_URL` | Mặc định local: `sqlite+aiosqlite:///./data/app.db` |
| `CHROMA_PERSIST_DIR` | Thư mục lưu Chroma vector store, mặc định `./data/chroma` |
| `GOOGLE_API_KEY` / `GOOGLE_API_KEYS` | Gemini API key cho generation và embedding |
| `MODEL_NAME` | Model Gemini dùng để sinh câu trả lời |
| `EMBEDDING_MODEL_NAME` | Model embedding |
| `COHERE_API_KEY` | API key cho rerank, có thể để trống khi dev/test |
| `JWT_SECRET_KEY` | Secret ký JWT; local có thể dùng default, production phải đổi |
| `CORS_ORIGINS` | Origin frontend được phép gọi API, mặc định `http://localhost:3000` |

## Chạy project

### 1. Chạy backend

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Khi chạy ở `APP_ENV=development`, backend sẽ tự tạo bảng local và seed demo users nếu chưa có.

Backend URLs:

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/health/ready
- Static fallback app: http://localhost:8000/app

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

## Tài khoản demo

Local development tự seed hai tài khoản sau:

| Role | Email | Password |
| --- | --- | --- |
| Employee | `employee@example.com` | `employee123` |
| HR Admin | `admin@example.com` | `admin123` |

Gợi ý demo nhanh:

1. Đăng nhập bằng tài khoản HR Admin.
2. Upload tài liệu chính sách HR hoặc dùng flow thêm tài liệu mẫu trong UI.
3. Đăng nhập bằng tài khoản Employee.
4. Hỏi: `Chính sách nghỉ phép năm nay như thế nào?`
5. Kiểm tra câu trả lời có citations.
6. Hỏi một câu nhạy cảm hoặc ngoài phạm vi để thấy luồng xác nhận tạo ticket.
7. Đăng nhập HR Admin để xem/cập nhật ticket và chạy trending detection.

## Tests và checks

Backend:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check backend/app tests
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Chạy bằng Docker Compose

Docker Compose build backend, frontend và chạy kèm Postgres:

```bash
docker compose up --build
```

Các dữ liệu runtime được persist qua volume và thư mục `data/`.

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
- `CORS_ORIGINS=https://your-frontend-domain`
- `CHROMA_PERSIST_DIR=/app/data/chroma`

## Troubleshooting

- **Không vào được frontend:** kiểm tra `npm run dev` có chạy ở port `3000` không.
- **Frontend không gọi được backend:** kiểm tra backend ở port `8000`, `CORS_ORIGINS=http://localhost:3000`, và `VITE_API_BASE_URL`.
- **Login demo thất bại:** đảm bảo backend đang chạy với `APP_ENV=development`; xóa database local trong `data/app.db` nếu muốn seed lại từ đầu.
- **Readiness báo `model_provider: missing`:** thêm `GOOGLE_API_KEY` hoặc `GOOGLE_API_KEYS` vào `.env`. Ở local/dev, một số test vẫn có fallback deterministic.
- **Port 8000 hoặc 3000 bị chiếm:** đổi port trong lệnh `uvicorn` hoặc script Vite, rồi cập nhật lại API URL/CORS tương ứng.
- **Lỗi Chroma/vector store:** kiểm tra `CHROMA_PERSIST_DIR=./data/chroma` và quyền ghi vào thư mục `data/`.

## Cấu trúc project

```text
backend/app/
  api/            FastAPI routers và dependencies
  core/           config, security, logging helpers
  database/       SQLAlchemy session/base
  models/         SQLAlchemy models
  rag/            chunking, loaders, lexical retrieval helpers
  services/       auth, documents, retrieval, LLM, tickets, feedback, trending
frontend/         React/Vite frontend
alembic/          Database migrations
tests/            API, RAG, và integration tests
scripts/          Operational và bootstrap scripts
eval/results/     Evaluation reports
presentation/     Pitch deck và demo materials
```
