# HR Helpdesk AI

> Tóm tắt 1 câu: Nhân viên phải chờ HR trả lời các câu hỏi lặp lại về chính sách và thủ tục → HR Helpdesk AI dùng RAG, RBAC và function calling an toàn để trả lời có trích dẫn, tra cứu chỉ số cá nhân và tự động chuyển tiếp ticket cho HR.

## Vấn đề (Problem)

Trong doanh nghiệp, phòng HR thường bị quá tải bởi các câu hỏi lặp lại về nghỉ phép, lương thưởng, bảo hiểm, phúc lợi và quy trình nội bộ. Nhân viên phải chờ phản hồi cho các thắc mắc đơn giản, còn HR mất thời gian copy/paste câu trả lời thay vì xử lý các việc có giá trị hơn.

- Nhân viên cần câu trả lời nhanh, đúng chính sách và có nguồn kiểm chứng.
- HR admin cần giảm số câu hỏi lặp lại, đặc biệt khi có chính sách mới hoặc thay đổi đột xuất.
- Các truy vấn về dữ liệu cá nhân như ngày phép, bảo hiểm, khen thưởng phải được bảo vệ theo tài khoản đăng nhập.
- Các tình huống nhạy cảm hoặc vượt thẩm quyền AI cần được chuyển thành ticket cho HR thật.

Các kênh hiện tại như email, chat nội bộ hoặc file PDF rời rạc chưa đủ vì thông tin khó tìm, không cá nhân hóa theo quyền truy cập và không tự động phát hiện chủ đề đang được hỏi nhiều.

## Giải pháp (Solution)

HR Helpdesk AI là một web app self-service cho nhân viên và HR admin, gồm các năng lực chính:

- Hỏi đáp chính sách có trích dẫn: nhân viên hỏi về nghỉ phép, bảo hiểm, quy trình HR; hệ thống truy hồi tài liệu phù hợp và trả lời kèm citation.
- RBAC và guardrails: lọc tài liệu theo role/department trước khi trả lời, từ chối jailbreak, câu hỏi ngoài phạm vi và yêu cầu dữ liệu nhạy cảm.
- Tra cứu số liệu cá nhân: dùng function-calling style lookup để trả về số ngày phép còn lại, trạng thái bảo hiểm và trạng thái xét duyệt khen thưởng của chính user.
- Escalation ticket: tự động tạo ticket khi câu hỏi nhạy cảm, thiếu nguồn hoặc cần HR xử lý thủ công.
- Trending pins: ghi nhận lưu lượng câu hỏi, phát hiện chủ đề lặp lại và tạo thông báo ghim khi vượt threshold.
- Feedback: người dùng đánh giá câu trả lời hữu ích hay cần xem lại để HR cải thiện kho tri thức.

## Target User

- Primary: Nhân viên nội bộ, cán bộ, giảng viên cần hỏi nhanh về chính sách HR hoặc tra cứu thông tin HR cá nhân.
- Secondary: HR admin quản lý tài liệu chính sách, theo dõi trend câu hỏi, xử lý ticket và cải thiện chất lượng phản hồi.
- Additional: Department admin có quyền xem một số chính sách theo phòng ban nhưng không được truy cập dữ liệu cá nhân ngoài phạm vi.

## Tech Stack

| Layer | Technology |
|-------|------------|
| AI Agent | LangGraph workflow, Gemini generation model, Gemini embedding model |
| Backend | FastAPI, Python 3.11+, Pydantic |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS in `fontend/` |
| Retrieval | RAG lexical retrieval, Chroma-ready local vector storage |
| Data | In-memory MVP stores, local Chroma persist directory, planned SQLite/Postgres path |
| Security | JWT auth, role-based access control, retrieval filters, guardrails |
| DevOps | Docker, docker-compose, pytest, ruff |

## Quick Start

### 1. Clone repo

```bash
git clone https://github.com/a20-ai-thuc-chien/C2-App-091.git
cd C2-App-091
```

### 2. Setup environment

```bash
cp .env.example .env
```

Trên Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Sau đó cập nhật `.env` nếu muốn dùng Gemini thật:

- `GOOGLE_API_KEY`
- `GOOGLE_API_KEYS` nếu muốn xoay vòng nhiều key
- `MODEL_NAME=gemini-3.1-flash-lite`
- `EMBEDDING_MODEL_NAME=gemini-embedding-2`
- `JWT_SECRET`

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Trên Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Run backend development server

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Trên Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend URLs:

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- OpenAPI JSON: http://localhost:8000/openapi.json

### 5. Run React frontend

Frontend chính của dự án nằm trong thư mục `fontend/` và chạy bằng Vite.

```bash
cd fontend
npm install
npm run dev
```

Trên Windows PowerShell:

```powershell
Set-Location fontend
npm install
npm run dev
```

Mở frontend tại:

- React app: http://localhost:3000/app/

Khi chạy dev, frontend mặc định gọi backend tại `http://localhost:8000/api/v1`. Nếu cần đổi API URL, tạo file `fontend/.env` và đặt:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Lưu ý: backend vẫn có route `/app` phục vụ static fallback cũ, nhưng frontend chính để demo/nộp bài là React app trong `fontend/`.

### Demo accounts

| Role | Email | Password |
|------|-------|----------|
| Employee | `employee@example.com` | `employee123` |
| HR Admin | `admin@example.com` | `admin123` |

## Project Structure

```text
├── src/
│   ├── agents/              # LangGraph scaffold and agent state
│   ├── api/                 # FastAPI routes
│   ├── models/              # Pydantic schemas and response contracts
│   ├── rag/                 # Chunking, loaders, local retriever helpers
│   ├── services/            # Auth, documents, retrieval, guardrails, HRIS, tickets, trending, feedback
│   ├── static/              # Static fallback/demo HTML served by FastAPI
│   ├── config.py            # Environment settings
│   └── main.py              # FastAPI app entry point
├── fontend/                 # React/Vite frontend app, run with npm run dev
│   ├── src/                 # React pages, components, hooks, API client
│   ├── package.json         # npm scripts and dependencies
│   └── vite.config.ts       # Vite config, base /app/
├── tests/
│   ├── e2e/                 # Live demo verification
│   ├── test_agents/         # Agent/RAG/guardrail/function tests
│   └── test_api/            # API and contract tests
├── flow/                    # Product planning artifacts and API contract
├── cards/                   # Buildflow implementation cards C-001 to C-010
├── eval/results/            # Evaluation report and e2e metrics
├── mockups/                 # Approved UI mockup
├── presentation/            # Demo/pitch materials
├── scripts/                 # AI log helpers and e2e demo script
├── data/                    # Local persisted retrieval data
├── Dockerfile
├── docker-compose.yml
├── ARCHITECTURE.md
├── JOURNAL.md
├── WORKLOG.md
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/app` | Backend static fallback app |
| GET | `/docs` | Swagger API documentation |
| POST | `/api/v1/auth/login` | Login with demo credentials and receive JWT |
| GET | `/api/v1/me` | Return current user profile |
| GET | `/api/v1/me/hr-metrics` | Return current user's HR metrics |
| POST | `/api/v1/chat` | Chat with HR assistant; returns answer, citations, actions or escalation |
| POST | `/api/v1/documents` | HR admin uploads/registers a policy document |
| GET | `/api/v1/documents` | HR admin lists indexed documents |
| POST | `/api/v1/escalations` | Create a manual escalation ticket |
| GET | `/api/v1/admin/tickets` | HR admin lists tickets |
| PATCH | `/api/v1/admin/tickets/{ticket_id}` | HR admin updates ticket status/assignee |
| GET | `/api/v1/trending/pins` | Read current trend pins |
| POST | `/api/v1/admin/trending/run` | HR admin runs trending detection |
| POST | `/api/v1/feedback` | Submit answer feedback |
| GET | `/api/v1/status` | Baseline agent status |

The full contract is tracked in `flow/05-contract.md`.

## Testing

Run the main test suite:

```bash
pytest tests -q
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Run the live C-010 e2e verification after starting the app:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_demo_flow.py -q
```

The e2e script writes the final metrics report to `eval/results/report.md`.

Frontend checks:

```powershell
Set-Location fontend
npm run lint
npm run build
```

Nếu `npm run build` trên Windows báo `EPERM` khi ghi/xóa file trong `fontend/dist`, hãy đóng process đang giữ file hoặc xóa `fontend/dist` thủ công rồi chạy lại. Lệnh dev chính để demo vẫn là `npm run dev`.

Current verified demo metrics:

| Metric | Target | Result |
|--------|--------|--------|
| Seeded policy questions | 30 | 30 |
| Cited policy answers | >= 90% | 30/30, 100% |
| P95 chat latency | < 10s | 0.003s in local demo report |
| Safe HR metric lookups | 5 | 5 |
| Escalation tickets | 3 | 3 |
| Trend pin | 1 after 5 similar queries | `Nghỉ phép` |

## Configuration

Settings are loaded from `.env` with Pydantic settings.

Key variables:

| Variable | Purpose |
|----------|---------|
| `APP_NAME` | Application name |
| `APP_ENV` | Runtime environment |
| `CORS_ORIGINS` | Allowed frontend origins |
| `JWT_SECRET` | JWT signing secret |
| `GOOGLE_API_KEY` | Primary Gemini API key |
| `GOOGLE_API_KEYS` | Optional list of Gemini keys for rotation |
| `MODEL_NAME` | Gemini generation model |
| `EMBEDDING_MODEL_NAME` | Gemini embedding model |
| `CHROMA_PERSIST_DIR` | Local vector/chunk persistence directory |

Do not commit real API keys or production secrets.

## Deliverables Checklist

- [x] Source Code
- [x] README.md
- [x] Architecture Document (`ARCHITECTURE.md`)
- [x] API Contract (`flow/05-contract.md`)
- [x] AI Logs (`.ai-log/`)
- [x] Weekly Journal (`JOURNAL.md`)
- [x] Worklog (`WORKLOG.md`)
- [x] Evaluation Evidence (`eval/results/report.md`)
- [x] React Demo UI (`fontend/`, Vite dev server at `http://localhost:3000/app/`)
- [x] E2E Demo Verification (`tests/e2e/test_demo_flow.py`)
- [ ] Live URL / Deploy
- [ ] Video Demo
- [ ] Pitch Deck (`presentation/`)

## Team

| Member | Role | Student ID |
|--------|------|------------|
| Đang cập nhật | Product / Engineering | Đang cập nhật |

## Planning Artifacts

- `flow/00-idea.md`
- `flow/01-research.md`
- `flow/02-scope.md`
- `flow/03-prd.md`
- `flow/04-adr.md`
- `flow/05-contract.md`
- `cards/`

## License

MIT
