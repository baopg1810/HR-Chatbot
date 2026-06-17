# Weekly Journal - HR Helpdesk AI

## Week 1 - From Idea To Demo-Ready MVP

**Time period:** 01/06/2026 - 17/06/2026  
**Project:** HR Helpdesk AI  
**Status:** MVP demo-ready, e2e verified locally

### 1. Features Shipped

Trong tuần này, dự án đã đi từ ý tưởng sản phẩm tới một bản MVP có thể chạy demo end-to-end.

Các phần chính đã hoàn thành:

- Product flow và planning artifacts:
  - Hoàn thiện ý tưởng, research, scope, PRD, ADR và API contract trong thư mục `flow/`.
  - Tạo build cards từ `C-001` đến `C-010` để chia nhỏ quá trình triển khai.
- Backend FastAPI:
  - Tạo app FastAPI với `/health`, `/docs`, `/openapi.json`.
  - Tạo API prefix `/api/v1`.
  - Serve static fallback tại `/app`.
- Authentication:
  - Tạo demo login bằng JWT.
  - Tạo user mẫu `employee@example.com` và `admin@example.com`.
  - Bảo vệ các endpoint cần đăng nhập.
- HR policy Q&A:
  - Upload/register tài liệu HR.
  - Chunking tài liệu.
  - Retrieval/RAG-lite để trả lời kèm citations.
- Security/RBAC:
  - Lọc citation theo role và department.
  - Guardrails cho jailbreak, outside-scope và sensitive request.
  - Không trả lời khi không có nguồn phù hợp.
- HR self-service:
  - Tra cứu ngày phép còn lại, trạng thái bảo hiểm, trạng thái xét duyệt khen thưởng.
  - Đảm bảo employee chỉ xem dữ liệu của chính mình.
- Escalation:
  - Tạo ticket tự động cho câu hỏi nhạy cảm hoặc vượt phạm vi.
  - HR admin có thể list và cập nhật ticket.
- Trending:
  - Ghi log query.
  - Phát hiện nhiều câu hỏi cùng chủ đề.
  - Tạo trend pin khi vượt threshold.
- Feedback:
  - Người dùng đánh giá câu trả lời `up/down`.
  - Feedback gắn với `message_id`.
- Frontend:
  - Tạo UI mockup.
  - Tạo frontend React/Vite trong thư mục `fontend/`, chạy bằng `npm run dev`.
  - Frontend gọi backend FastAPI qua `http://localhost:8000/api/v1` trong môi trường dev.
  - Việt hóa các chuỗi hiển thị trên giao diện.
- Testing/evaluation:
  - Tạo API tests, agent tests, contract tests và e2e test.
  - Cập nhật `eval/results/report.md`.
  - Kết quả gần nhất: `49 passed`.

### 2. AI Tools Used And How They Helped

Các công cụ AI được dùng chủ yếu trong tuần:

| Tool | Cách sử dụng | Tác động |
|------|--------------|----------|
| Codex | Phân tích codebase, tạo plan theo card, viết backend/frontend/tests/docs | Tăng tốc triển khai MVP theo từng module nhỏ, có kiểm thử sau mỗi bước |
| Buildflow workflow | Chia dự án thành các stage và cards `C-001` đến `C-010` | Giữ phạm vi rõ ràng, tránh làm lan man hoặc bỏ sót deliverable |
| AI logging hooks | Ghi lại prompt và tương tác AI vào `.ai-log/` | Hỗ trợ minh bạch quá trình dùng AI khi nộp bài |

AI hữu ích nhất ở ba điểm:

1. Chuyển yêu cầu sản phẩm thành API contract và card triển khai cụ thể.
2. Viết code theo cấu trúc hiện có, không cần thiết kế lại từ đầu.
3. Tạo test/e2e verification để chứng minh MVP chạy được thay vì chỉ mô tả.

### 3. Hardest Problem Of The Week

Vấn đề khó nhất là cân bằng giữa một MVP chạy offline/local ổn định và yêu cầu sản phẩm có RAG, LLM, RBAC, HRIS lookup, trending.

Nếu gọi LLM thật ở mọi bước thì demo dễ bị phụ thuộc API key, network, quota và latency. Để giảm rủi ro, nhóm chọn cách:

- Dùng RAG-lite lexical retrieval cho MVP để có kết quả deterministic.
- Vẫn giữ cấu hình Gemini model và embedding model trong `.env`.
- Thiết kế contract sao cho sau này có thể thay retrieval/LLM thật mà không phá API.
- Viết e2e test kiểm tra metric sản phẩm thay vì chỉ unit test.

Một vấn đề khác là bảo mật dữ liệu HR. Hệ thống phải trả lời nhanh nhưng không được lộ dữ liệu ngoài quyền. Vì vậy RBAC được đặt ở tầng retrieval trước khi tạo câu trả lời, không chỉ lọc text sau khi answer đã được sinh.

### 4. What We Learned

- Contract-first giúp làm nhanh hơn: khi `flow/05-contract.md` rõ, backend, frontend và tests đi cùng một hướng.
- Guardrails không nên chỉ là prompt instruction; cần có logic kiểm tra trước khi retrieval/generation.
- Với dữ liệu nhạy cảm như HR, fallback đúng không phải là "trả lời chung chung", mà là từ chối rõ ràng hoặc tạo ticket.
- E2E metrics rất quan trọng khi demo AI product: 30 câu policy, citation rate, latency, metric lookup, escalation và trending pin giúp chứng minh sản phẩm chạy thật.
- React/Vite frontend phù hợp hơn cho demo thật vì có routing, component, state và UX rõ hơn static HTML.

### 5. What We Would Do Differently

Nếu làm lại từ đầu, nhóm sẽ:

- Thiết kế persistent storage sớm hơn để tránh phụ thuộc in-memory store.
- Tách rõ data seed/demo data với runtime data.
- Tạo UI admin feedback chi tiết hơn thay vì chỉ có endpoint feedback.
- Viết script chạy demo một lệnh từ đầu để giảm thao tác thủ công khi kiểm thử.

### 6. Plan For Next Week

Các bước tiếp theo:

1. Thay in-memory stores bằng SQLite hoặc Postgres.
2. Kết nối Chroma/pgvector thật cho retrieval.
3. Tích hợp Gemini answer synthesis và trend summary có guardrails.
4. Hoàn thiện deploy bằng Docker hoặc một nền tảng như Render/Fly/Railway.
5. Làm video demo ngắn theo flow: login, upload document, hỏi policy, metric lookup, sensitive escalation, trend pin.
6. Hoàn thiện pitch deck trong `presentation/`.

### 7. Evidence

- Backend local: `http://localhost:8000`
- React frontend local: `http://localhost:3000/app/`
- API docs: `http://localhost:8000/docs`
- Architecture: `ARCHITECTURE.md`
- PRD: `flow/03-prd.md`
- API contract: `flow/05-contract.md`
- E2E report: `eval/results/report.md`
- AI logs: `.ai-log/archive/`
