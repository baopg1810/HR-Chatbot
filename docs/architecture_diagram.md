# Sơ đồ kiến trúc

## Tổng quan hệ thống

```mermaid
graph TB
    User([Nhân viên / HR Admin]) --> UI[Frontend React + Vite]
    UI -->|REST + SSE| API[Backend FastAPI<br/>/api/v1]

    API --> Auth[Xác thực + RBAC<br/>JWT access/refresh tokens]
    API --> Chat[Chat API<br/>sync + streaming]
    API --> Docs[Document API<br/>upload/list/delete]
    API --> Tickets[Ticket API<br/>employee + admin]
    API --> Trends[Trending API]
    API --> Feedback[Feedback API]

    Chat --> Agent[LangGraph agent]
    Agent --> Guardrails[Guardrails đầu vào / chủ đề / tool / đầu ra]
    Agent --> ToolChoice[Chọn tool]
    ToolChoice --> HRIS[Adapter chỉ số HR cá nhân]
    ToolChoice --> RAG[Tìm kiếm chính sách]
    ToolChoice --> TicketDraft[Ticket draft agent]
    ToolChoice --> General[Trả lời HR chung]

    Docs --> Ingest[Load + chunk + embed]
    Ingest --> Chroma[(Chroma<br/>policy chunks)]
    Ingest --> SQL[(SQLite local<br/>Postgres production)]

    RAG --> Chroma
    RAG --> Cohere[Cohere rerank]
    Agent --> Gemini[Gemini<br/>generation, embeddings, tool choice]
    Guardrails --> Safeguard[Rules + Groq/OpenAI safeguard tùy chọn]

    Auth --> SQL
    Chat --> SQL
    Tickets --> SQL
    Trends --> SQL
    Feedback --> SQL
```

## Luồng chat agent

```mermaid
flowchart TD
    Start([Tin nhắn người dùng]) --> InputGuard[input_safeguard]
    InputGuard --> InputBlocked{Bị chặn?}
    InputBlocked -->|Có| OutputGuard[output_safeguard]
    InputBlocked -->|Không| TopicScope[topic_scope]

    TopicScope --> TopicBlocked{Ngoài phạm vi / mơ hồ / nhạy cảm?}
    TopicBlocked -->|Có| OutputGuard
    TopicBlocked -->|Không| Intent[classify_intent]

    Intent --> Route{Tool được chọn}
    Route -->|get_hr_metrics| HRMetrics[hr_metrics]
    Route -->|search_policy| Retrieve[retrieve_policy]
    Route -->|request_ticket_escalation| TicketIntent[handle_ticket_intent]
    Route -->|answer_general| General[general_answer]

    Retrieve --> HasSource{Có citations đọc được?}
    HasSource -->|Có| CitedAnswer[answer_with_sources]
    HasSource -->|Không| NoSource[handle_no_source]

    HRMetrics --> OutputGuard
    CitedAnswer --> OutputGuard
    NoSource --> OutputGuard
    TicketIntent --> OutputGuard
    General --> OutputGuard
    OutputGuard --> Finalize[finalize_response]
    Finalize --> End([ChatResponse])
```

## Ingest và retrieval RAG

```mermaid
flowchart LR
    Upload[Admin upload .docx/.md/.txt] --> Loader[load_policy_document]
    Loader --> Chunker[chunk_document theo section]
    Chunker --> Embed[Gemini embeddings<br/>hoặc local fallback trong non-strict dev/test]
    Embed --> VectorStore[(Chroma collection<br/>hr_policy_chunks)]
    Embed --> Metadata[(SQL document metadata)]

    Query[Câu hỏi HR của người dùng] --> QueryEmbed[Embed query]
    QueryEmbed --> Semantic[Chroma semantic search]
    Query --> Lexical[Keyword / lexical scoring]
    Semantic --> Merge[Gộp candidates]
    Lexical --> Merge
    Merge --> ACL[Filter theo visibility_roles + department_ids]
    ACL --> Gate[Score/confidence gate]
    Gate --> Rerank[Cohere rerank]
    Rerank --> Citations[Citations trả về agent]
```

## Luồng ticket

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant UI as Frontend
    participant API as FastAPI
    participant A as LangGraph agent
    participant DB as SQL database

    U->>UI: Yêu cầu tạo ticket HR
    UI->>API: POST /api/v1/chat/stream
    API->>A: Invoke chat graph kèm session state
    A->>A: Soạn field ticket hoặc hỏi thông tin còn thiếu
    A-->>API: ChatResponse kèm ticket_draft_confirmation
    API->>DB: Lưu chat/session workflow state
    API-->>UI: SSE tokens + final response
    UI-->>U: Hiển thị card ticket đã điền sẵn
    U->>UI: Xác nhận gửi
    UI->>API: POST /api/v1/escalations
    API->>DB: Tạo ticket
    API-->>UI: Ticket record
```

## Chi tiết thành phần

| Thành phần | Công nghệ | Mục đích |
| --- | --- | --- |
| Frontend | React 18, Vite, TypeScript | Chat, knowledge base, tickets, admin dashboard theo vai trò |
| Backend API | FastAPI | REST/SSE API và phục vụ frontend bundled/static |
| Agent | LangGraph | Điều phối chat có trạng thái và routing |
| LLM | Gemini | Generation, embeddings, streaming, tool choice |
| Rerank | Cohere | Rerank retrieval candidates trước khi trả citations |
| Guardrails | Rules + provider Groq/OpenAI tùy chọn | Safety checks cho input/topic/tool/output |
| Database | SQLite/Postgres | Users, tokens, sessions, tickets, feedback, query logs, document metadata |
| Vector Store | Chroma | Lưu persistent policy chunk embeddings cho RAG |
| Triển khai | Docker, Docker Compose | Backend image có bundled frontend và Postgres |
