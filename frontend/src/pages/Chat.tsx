import React, { useEffect, useRef, useState } from 'react';
import { Bot, Clock, MessageSquare, Plus, Send, Ticket, X } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Message } from '../types';
import { cn } from '../lib/utils';
import {
  ChatSessionRecord,
  clearChatSessionState,
  createEscalation,
  getChatSessionMessages,
  listChatSessions,
  streamChatRequest,
} from '../lib/api';
import { useAuth } from '../hooks/useAuth';

const welcomeMessage = 'Xin chào. Tôi là AI hỗ trợ nhân sự. Bạn có thể hỏi về chính sách nghỉ phép, bảo hiểm, phúc lợi hoặc tạo ticket cho HR.';

function newWelcomeMessage(): Message {
  return {
    id: 'welcome',
    sender: 'ai',
    text: welcomeMessage,
    timestamp: new Date().toISOString(),
  };
}

type MarkdownBlock =
  | { type: 'paragraph'; content: string }
  | { type: 'unordered-list'; items: string[] }
  | { type: 'ordered-list'; items: string[] };

type ChatAttachment = NonNullable<Message['attachments']>[number];
type TicketCategory = 'leave' | 'benefits' | 'equipment' | 'documents' | 'other';

interface TicketDraftFormValues {
  title: string;
  category: TicketCategory;
  description: string;
  reason: string;
  priority: string;
  suggestedFields: string[];
  sessionId?: string | null;
}

const ticketCategories: { value: TicketCategory; label: string }[] = [
  { value: 'leave', label: 'Nghỉ phép & Thai sản' },
  { value: 'benefits', label: 'Lương & Phúc lợi' },
  { value: 'equipment', label: 'Thiết bị & IT Support' },
  { value: 'documents', label: 'Giấy tờ & Thủ tục hành chính' },
  { value: 'other', label: 'Khác' },
];

export function Chat() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([newWelcomeMessage()]);

  const hasTicketDraft = messages.some((message) =>
    message.attachments?.some((attachment) => attachment.url === 'ticket_draft_confirmation'),
  );

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([newWelcomeMessage()]);
  };

  const handleSelectSessionById = async (sid: string) => {
    if (!user) return;
    setIsLoading(true);
    try {
      const history = await getChatSessionMessages(user.token, sid);
      setSessionId(sid);
      setMessages(
        history.length > 0
          ? history.map((message) => ({
              id: message.id,
              sender: message.sender,
              text: message.text,
              timestamp: message.timestamp || new Date().toISOString(),
              citations: message.citations,
              attachments: message.actions
                ?.filter((action) => !['none', 'hr_metric_lookup'].includes(action.type))
                .map((action) => ({ name: action.label, url: action.type, data: action.data })),
            }))
          : [newWelcomeMessage()],
      );
    } catch (err) {
      console.error('Error loading chat session:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const state = location.state as any;
    if (state?.newChat) {
      handleNewChat();
      window.history.replaceState({}, document.title);
    } else if (state?.sessionId) {
      void handleSelectSessionById(state.sessionId);
      window.history.replaceState({}, document.title);
    }
  }, [location]);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('current_chat_session_id', sessionId);
    } else {
      localStorage.removeItem('current_chat_session_id');
    }
    window.dispatchEvent(new Event('chat-session-active-changed'));
  }, [sessionId]);

  const handleSend = async () => {
    if (!input.trim() || !user) return;
    const question = input.trim();
    setInput('');
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), sender: 'user', text: question, timestamp: new Date().toISOString() },
    ]);
    setIsLoading(true);
    let assistantMessageId: string | null = null;
    let streamedText = '';
    try {
      await streamChatRequest(user.token, question, sessionId, {
        onStart: (data) => {
          assistantMessageId = data.message_id;
          setSessionId(data.session_id);
          setMessages((prev) => [
            ...prev,
            {
              id: data.message_id,
              sender: 'ai',
              text: '',
              timestamp: new Date().toISOString(),
            },
          ]);
        },
        onToken: (text) => {
          streamedText += text;
          if (!assistantMessageId) return;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMessageId ? { ...message, text: streamedText } : message,
            ),
          );
        },
        onDone: (response) => {
          assistantMessageId = response.message_id;
          streamedText = response.answer;
          setSessionId(response.session_id);
          setMessages((prev) =>
            prev.map((message) =>
              message.id === response.message_id
                ? {
                    ...message,
                    text: response.answer,
                    citations: response.citations,
                    attachments: response.actions
                      .filter((action) => !['none', 'hr_metric_lookup'].includes(action.type))
                      .map((action) => ({ name: action.label, url: action.type, data: action.data })),
                  }
                : message,
            ),
          );
          window.dispatchEvent(new Event('chat-session-updated'));
        },
      });
    } catch (err) {
      const errorText = err instanceof Error ? err.message : 'Không thể gửi câu hỏi.';
      setMessages((prev) => {
        if (assistantMessageId) {
          return prev.map((message) =>
            message.id === assistantMessageId ? { ...message, text: errorText } : message,
          );
        }
        return [
          ...prev,
          {
            id: crypto.randomUUID(),
            sender: 'ai',
            text: errorText,
            timestamp: new Date().toISOString(),
          },
        ];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleConfirmEscalation = async (
    messageId: string,
    attachmentIndex: number,
    payload: Record<string, unknown> | null | undefined,
  ) => {
    if (!user || !payload) return;
    setIsLoading(true);
    try {
      const ticket = await createEscalation(user.token, {
        message: String(payload.message || ''),
        reason: typeof payload.reason === 'string' ? payload.reason : 'user_requested',
        priority: typeof payload.priority === 'string' ? payload.priority : 'normal',
        session_id: typeof payload.session_id === 'string' ? payload.session_id : sessionId,
      });

      setMessages((prev) =>
        prev.map((message) =>
          message.id === messageId
            ? {
                ...message,
                attachments: message.attachments?.map((attachment, index) =>
                  index === attachmentIndex
                    ? {
                        name: `Đã tạo ticket ${ticket.id}`,
                        url: 'escalation_created',
                        data: { ticket_id: ticket.id, status: ticket.status },
                      }
                    : attachment,
                ),
              }
            : message,
        ),
      );
    } catch (err) {
      const errorText = err instanceof Error ? err.message : 'Không thể tạo ticket.';
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'ai',
          text: errorText,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmTicketDraft = async (
    messageId: string,
    attachmentIndex: number,
    draft: TicketDraftFormValues,
  ) => {
    if (!user) return;
    setIsLoading(true);
    try {
      const ticket = await createEscalation(user.token, {
        message: formatTicketDraftMessage(draft),
        reason: draft.reason || 'user_requested',
        priority: draft.priority || 'normal',
        session_id: draft.sessionId || sessionId,
      });

      setMessages((prev) =>
        prev.map((message) =>
          message.id === messageId
            ? {
                ...message,
                attachments: message.attachments?.map((attachment, index) =>
                  index === attachmentIndex
                    ? {
                        name: `Đã tạo ticket ${ticket.id}`,
                        url: 'escalation_created',
                        data: { ticket_id: ticket.id, status: ticket.status },
                      }
                    : attachment,
                ),
              }
            : message,
        ),
      );
    } catch (err) {
      const errorText = err instanceof Error ? err.message : 'Không thể tạo ticket.';
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'ai',
          text: errorText,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismissEscalation = async (messageId: string, attachmentIndex: number) => {
    const attachment = messages.find((message) => message.id === messageId)?.attachments?.[attachmentIndex];
    const isTicketDraft = attachment?.url === 'ticket_draft_confirmation';
    const payloadSessionId =
      typeof attachment?.data?.session_id === 'string' ? attachment.data.session_id : sessionId;
    if (user && isTicketDraft && payloadSessionId) {
      try {
        await clearChatSessionState(user.token, payloadSessionId);
      } catch (err) {
        console.error('Error clearing ticket draft state:', err);
      }
    }
    if (isTicketDraft) {
      setMessages((prev) => [
        ...removeTicketDraftAttachments(prev),
        {
          id: crypto.randomUUID(),
          sender: 'ai',
          text: 'Ticket nháp đã được hủy. Mình sẽ không gửi yêu cầu này cho HR.',
          timestamp: new Date().toISOString(),
        },
      ]);
      return;
    }
    setMessages((prev) =>
      prev.map((message) =>
        message.id === messageId
          ? {
              ...message,
              attachments: message.attachments?.filter((_, index) => index !== attachmentIndex),
            }
          : message,
      ),
    );
  };

  const suggestions = [
    'Thời gian thử việc tại công ty quy định thế nào?',
    'Chế độ thưởng các ngày lễ Tết và thâm niên thế nào?',
  ];

  const isLastMessageAiLoading = messages.length > 0 && messages[messages.length - 1].sender === 'ai' && !messages[messages.length - 1].text;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-discord-bg relative overflow-hidden transition-colors">
      {/* Nút Clock lịch sử đã được chuyển vào Sidebar chính */}

      <div className="flex-1 overflow-y-auto px-3 md:px-8 lg:px-[15%] pt-20 md:pt-16 pb-4 md:pb-6">
        <div className="space-y-5 md:space-y-8 max-w-4xl mx-auto">
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';

            return (
              <div key={msg.id} className={cn('flex items-start gap-4 w-full', isUser ? 'flex-row-reverse' : 'flex-row')}>
                {!isUser && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 bg-brand-mint text-[#048261] dark:bg-discord-accent dark:text-white">
                    <Bot size={18} />
                  </div>
                )}

                <div
                  className={cn(
                    'max-w-[88%] relative flex flex-col gap-3',
                    msg.attachments?.some((attachment) => attachment.url === 'ticket_draft_confirmation')
                      ? 'md:max-w-[88%]'
                      : 'md:max-w-[75%]',
                  )}
                >
                  {isUser ? (
                    <div className="bg-[#f0f4f9] dark:bg-discord-accent text-gray-800 dark:text-white px-4 md:px-5 py-3 md:py-3.5 rounded-[20px] md:rounded-[24px] rounded-tr-sm leading-relaxed text-[15px] whitespace-pre-wrap">
                      {msg.text}
                    </div>
                  ) : (
                    msg.text.trim() ? (
                      <MarkdownMessage text={msg.text} />
                    ) : (
                      <div className="flex items-center py-2">
                        <div className="w-4 h-4 bg-white border border-gray-300 dark:border-transparent dark:bg-white rounded-full animate-scale-circle shadow-sm shrink-0" />
                      </div>
                    )
                  )}

                  {msg.attachments?.map((attachment, i) =>
                    attachment.url === 'ticket_draft_confirmation' ? (
                      <TicketDraftCard
                        key={`${attachment.name}-${i}`}
                        attachment={attachment}
                        isLoading={isLoading}
                        onCancel={() => handleDismissEscalation(msg.id, i)}
                        onSubmit={(draft) => void handleConfirmTicketDraft(msg.id, i, draft)}
                      />
                    ) : (
                      <div key={`${attachment.name}-${i}`} className="bg-white dark:bg-discord-sidebar border border-[#a6f4df] dark:border-discord-accent/30 ring-1 ring-brand-mint dark:ring-discord-accent/20 shadow-sm rounded-xl p-5 relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-1.5 h-full bg-[#048261] dark:bg-discord-accent" />
                        <div className="flex items-start gap-4 mb-4 px-2">
                          <div className="w-10 h-10 rounded-full bg-[#e0fbf4] dark:bg-discord-accent/20 text-[#048261] dark:text-discord-accent flex items-center justify-center shrink-0 mt-1">
                            <Ticket size={20} />
                          </div>
                          <div>
                            <h4 className="text-[15px] font-bold text-gray-900 dark:text-discord-text leading-tight">
                              {attachment.url === 'escalation_confirmation_required'
                                ? 'Cần xác nhận gửi ticket cho HR'
                                : attachment.name}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-discord-text-muted">Hệ thống đã thực hiện hành động liên quan đến yêu cầu của bạn.</p>
                            {attachment.url === 'escalation_confirmation_required' && (
                              <p className="text-sm text-gray-600 dark:text-discord-text-muted mt-2">
                                Bạn có muốn gửi ticket cho HR để được hỗ trợ tiếp không?
                              </p>
                            )}
                          </div>
                        </div>
                        {attachment.url === 'escalation_created' && (
                          <div className="flex justify-end border-t border-gray-100 dark:border-discord-bg pt-3">
                            <button
                              onClick={() => navigate(user?.role === 'admin' ? '/admin/tickets' : '/tickets')}
                              className="px-4 py-2 text-sm font-medium bg-brand-blue dark:bg-discord-accent text-white rounded-lg hover:bg-[#051c5e] dark:hover:bg-[#4752C4] transition-colors shadow-sm flex items-center gap-1.5"
                            >
                              Xem ticket <Send size={14} />
                            </button>
                          </div>
                        )}
                        {attachment.url === 'escalation_confirmation_required' && (
                          <div className="flex justify-end gap-2 border-t border-gray-100 dark:border-discord-bg pt-3">
                            <button
                              onClick={() => handleDismissEscalation(msg.id, i)}
                              className="px-4 py-2 text-sm font-medium bg-white dark:bg-discord-card text-gray-600 dark:text-discord-text border border-gray-200 dark:border-discord-bg rounded-lg hover:bg-gray-50 dark:hover:bg-discord-card-hover transition-colors"
                            >
                              Không gửi
                            </button>
                            <button
                              onClick={() => handleConfirmEscalation(msg.id, i, attachment.data)}
                              className="px-4 py-2 text-sm font-medium bg-brand-blue dark:bg-discord-accent text-white rounded-lg hover:bg-[#051c5e] dark:hover:bg-[#4752C4] transition-colors shadow-sm flex items-center gap-1.5 disabled:opacity-60"
                              disabled={isLoading}
                            >
                              Gửi ticket <Send size={14} />
                            </button>
                          </div>
                        )}
                      </div>
                    ),
                  )}
                </div>
              </div>
            );
          })}

          {isLoading && !isLastMessageAiLoading && (
            <div className="flex items-start gap-4 w-full">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 bg-brand-mint text-[#048261] dark:bg-discord-accent dark:text-white">
                <Bot size={18} />
              </div>
              <div className="flex items-center py-2">
                <div className="w-4 h-4 bg-white border border-gray-300 dark:border-transparent dark:bg-white rounded-full animate-scale-circle shadow-sm shrink-0" />
              </div>
            </div>
          )}
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      <div
        className={cn(
          'shrink-0 w-full bg-gradient-to-t from-white dark:from-discord-bg via-white dark:via-discord-bg to-transparent px-3 md:px-8 z-20 relative',
          hasTicketDraft ? 'pb-4 pt-3' : 'pb-4 md:pb-6 pt-4 md:pt-10',
        )}
      >
        <div className="max-w-3xl mx-auto w-full">
          <div className="flex flex-wrap gap-2 mb-4">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => setInput(suggestion)}
                className="whitespace-nowrap px-4 py-2 rounded-full bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg text-gray-600 dark:text-discord-text-muted shadow-sm text-sm font-medium hover:bg-gray-50 dark:hover:bg-discord-card-hover transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
          <div className="relative flex items-center shadow-lg rounded-full bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg focus-within:ring-2 focus-within:ring-gray-100 dark:focus-within:ring-discord-accent/20 transition-shadow">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Hỏi AI bất cứ điều gì..."
              className="w-full bg-transparent py-4 pl-6 pr-16 outline-none text-[15px] text-gray-800 dark:text-discord-text placeholder:text-gray-400 dark:placeholder:text-discord-text-muted"
            />
            <button
              onClick={handleSend}
              className="absolute right-2.5 p-2 bg-[#f0f4f9] dark:bg-discord-sidebar text-gray-700 dark:text-discord-text rounded-full hover:bg-gray-200 dark:hover:bg-discord-bg transition-colors disabled:opacity-50"
              disabled={!input.trim() || isLoading}
            >
              <Send size={18} />
            </button>
          </div>
          {!hasTicketDraft && (
          <p className="text-center text-[11px] text-gray-400 dark:text-discord-text-muted mt-3 font-medium">AI có thể trả lời chưa đầy đủ. Hãy kiểm tra lại thông tin quan trọng.</p>
          )}
        </div>
      </div>

      {/* Sidebar Lịch sử cũ đã bị xóa và tích hợp vào Sidebar chính */}
    </div>
  );
}

function TicketDraftCard({
  attachment,
  isLoading,
  onCancel,
  onSubmit,
}: {
  attachment: ChatAttachment;
  isLoading: boolean;
  onCancel: () => void;
  onSubmit: (draft: TicketDraftFormValues) => void;
}) {
  const initialDraft = getTicketDraftValues(attachment.data);
  const [title, setTitle] = useState(initialDraft.title);
  const [category, setCategory] = useState<TicketCategory>(initialDraft.category);
  const [description, setDescription] = useState(initialDraft.description);
  const canSubmit = title.trim().length > 0 && description.trim().length > 0 && !isLoading;

  return (
    <form
      className="w-full bg-white dark:bg-discord-sidebar border border-gray-200 dark:border-discord-bg shadow-sm rounded-lg relative overflow-hidden"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSubmit) return;
        onSubmit({
          title,
          category,
          description,
          reason: initialDraft.reason,
          priority: initialDraft.priority,
          suggestedFields: initialDraft.suggestedFields,
          sessionId: initialDraft.sessionId,
        });
      }}
    >
      <div className="absolute top-0 left-0 w-1 h-full bg-brand-blue dark:bg-discord-accent" />
      <div className="flex items-center gap-2.5 border-b border-gray-200 dark:border-discord-bg px-4 py-2.5 pl-5">
        <div className="w-6 h-6 rounded-full bg-[#e0fbf4] dark:bg-discord-accent/20 text-[#048261] dark:text-discord-accent flex items-center justify-center shrink-0">
          <Ticket size={15} />
        </div>
        <h4 className="text-sm font-semibold text-gray-900 dark:text-discord-text leading-tight">
          Xác nhận yêu cầu hỗ trợ (AI đã điền sẵn)
        </h4>
      </div>

      <div className="px-4 py-3 pl-5 space-y-2.5">
        <div className="grid gap-2.5 md:grid-cols-[1fr_260px]">
        <label className="block">
          <span className="block text-xs font-semibold text-gray-700 dark:text-discord-text-muted mb-1.5">Tiêu đề</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full h-10 rounded-lg border border-gray-300 dark:border-discord-bg bg-gray-50 dark:bg-discord-card px-3 text-sm text-gray-900 dark:text-discord-text outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent"
          />
        </label>

        <label className="block">
          <span className="block text-xs font-semibold text-gray-700 dark:text-discord-text-muted mb-1.5">Danh mục</span>
          <select
            value={category}
            onChange={(event) => setCategory(toTicketCategory(event.target.value))}
            className="w-full h-10 rounded-lg border border-gray-300 dark:border-discord-bg bg-gray-50 dark:bg-discord-card px-3 text-sm text-gray-900 dark:text-discord-text outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent"
          >
            {ticketCategories.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        </div>

        <label className="block">
          <span className="block text-xs font-semibold text-gray-700 dark:text-discord-text-muted mb-1.5">Mô tả chi tiết</span>
          <textarea
            rows={2}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-discord-bg bg-gray-50 dark:bg-discord-card px-3 py-2 text-sm leading-relaxed text-gray-900 dark:text-discord-text outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent resize-none min-h-[60px]"
          />
        </label>

        {initialDraft.suggestedFields.length > 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 dark:border-discord-bg bg-white dark:bg-discord-card px-3 py-2.5">
            <span className="block text-xs font-semibold text-gray-700 dark:text-discord-text-muted mb-1.5">
              Gợi ý nên bổ sung
            </span>
            <div className="flex flex-wrap gap-1.5">
              {initialDraft.suggestedFields.map((suggestion) => (
                <span
                  key={suggestion}
                  className="rounded-full border border-gray-200 dark:border-discord-bg bg-gray-50 dark:bg-discord-sidebar px-2.5 py-1 text-xs font-medium text-gray-700 dark:text-discord-text"
                >
                  {suggestion}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-2.5 bg-gray-50 dark:bg-discord-card/50 border-t border-gray-100 dark:border-discord-bg px-4 py-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3.5 py-2 text-sm font-medium text-gray-600 dark:text-discord-text hover:bg-white dark:hover:bg-discord-card rounded-lg transition-colors"
        >
          Hủy
        </button>
        <button
          type="submit"
          disabled={!canSubmit}
          className="px-4 py-2 text-sm font-semibold bg-brand-blue dark:bg-discord-accent text-white rounded-lg hover:bg-[#051c5e] dark:hover:bg-[#4752C4] transition-colors shadow-sm flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          Gửi yêu cầu <Send size={14} />
        </button>
      </div>
    </form>
  );
}

function getTicketDraftValues(data: Record<string, unknown> | null | undefined): TicketDraftFormValues {
  const payload = data || {};
  return {
    title: getString(payload.title),
    category: toTicketCategory(getString(payload.category)),
    description: getString(payload.description),
    reason: getString(payload.reason) || 'user_requested',
    priority: getString(payload.priority) || 'normal',
    suggestedFields: getStringArray(payload.suggested_fields),
    sessionId: getString(payload.session_id) || null,
  };
}

function removeTicketDraftAttachments(messages: Message[]): Message[] {
  return messages.map((message) => {
    if (!message.attachments?.some((attachment) => attachment.url === 'ticket_draft_confirmation')) {
      return message;
    }
    return {
      ...message,
      attachments: message.attachments.filter((attachment) => attachment.url !== 'ticket_draft_confirmation'),
    };
  });
}

function formatTicketDraftMessage(draft: TicketDraftFormValues): string {
  return [
    `Tiêu đề: ${draft.title.trim()}`,
    `Danh mục: ${ticketCategoryLabel(draft.category)}`,
    '',
    'Mô tả:',
    draft.description.trim(),
  ].join('\n');
}

function ticketCategoryLabel(category: TicketCategory): string {
  return ticketCategories.find((item) => item.value === category)?.label || 'Khác';
}

function toTicketCategory(value: string): TicketCategory {
  return ticketCategories.some((item) => item.value === value) ? (value as TicketCategory) : 'other';
}

function getString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function getStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function MarkdownMessage({ text }: { text: string }) {
  const blocks = parseMarkdownBlocks(text);

  return (
    <div className="text-gray-800 dark:text-discord-text leading-relaxed text-[15px] pt-1 space-y-3">
      {blocks.map((block, index) => {
        if (block.type === 'unordered-list') {
          return (
            <ul key={`ul-${index}`} className="list-disc pl-5 space-y-1">
              {block.items.map((item, itemIndex) => (
                <li key={`ul-${index}-${itemIndex}`}>{renderInlineMarkdown(item, `ul-${index}-${itemIndex}`)}</li>
              ))}
            </ul>
          );
        }

        if (block.type === 'ordered-list') {
          return (
            <ol key={`ol-${index}`} className="list-decimal pl-5 space-y-1">
              {block.items.map((item, itemIndex) => (
                <li key={`ol-${index}-${itemIndex}`}>{renderInlineMarkdown(item, `ol-${index}-${itemIndex}`)}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={`p-${index}`} className="whitespace-pre-wrap">
            {renderInlineMarkdown(block.content, `p-${index}`)}
          </p>
        );
      })}
    </div>
  );
}

function parseMarkdownBlocks(text: string): MarkdownBlock[] {
  const lines = text.split(/\r?\n/);
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const unorderedMatch = line.match(/^\s*[-*+]\s+(.+)$/);
    if (unorderedMatch) {
      const items: string[] = [];
      while (index < lines.length) {
        const match = lines[index].match(/^\s*[-*+]\s+(.+)$/);
        if (!match) break;
        items.push(match[1].trim());
        index += 1;
      }
      blocks.push({ type: 'unordered-list', items });
      continue;
    }

    const orderedMatch = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (orderedMatch) {
      const items: string[] = [];
      while (index < lines.length) {
        const match = lines[index].match(/^\s*\d+[.)]\s+(.+)$/);
        if (!match) break;
        items.push(match[1].trim());
        index += 1;
      }
      blocks.push({ type: 'ordered-list', items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      index < lines.length
      && lines[index].trim()
      && !/^\s*[-*+]\s+/.test(lines[index])
      && !/^\s*\d+[.)]\s+/.test(lines[index])
    ) {
      paragraphLines.push(lines[index].trimEnd());
      index += 1;
    }
    blocks.push({ type: 'paragraph', content: paragraphLines.join('\n') });
  }

  return blocks.length > 0 ? blocks : [{ type: 'paragraph', content: '' }];
}

function renderInlineMarkdown(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const boldPattern = /\*\*([\s\S]+?)\*\*/g;
  let lastIndex = 0;
  let matchIndex = 0;

  for (const match of text.matchAll(boldPattern)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      nodes.push(...renderTextWithBreaks(text.slice(lastIndex, start), `${keyPrefix}-text-${matchIndex}`));
    }
    nodes.push(
      <strong key={`${keyPrefix}-strong-${matchIndex}`} className="font-semibold text-gray-900 dark:text-discord-text">
        {renderTextWithBreaks(match[1], `${keyPrefix}-strong-text-${matchIndex}`)}
      </strong>,
    );
    lastIndex = start + match[0].length;
    matchIndex += 1;
  }

  if (lastIndex < text.length) {
    nodes.push(...renderTextWithBreaks(text.slice(lastIndex), `${keyPrefix}-text-tail`));
  }

  return nodes;
}

function renderTextWithBreaks(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split('\n').flatMap((part, index, parts) => (
    index === parts.length - 1
      ? [part]
      : [part, <br key={`${keyPrefix}-br-${index}`} />]
  ));
}
