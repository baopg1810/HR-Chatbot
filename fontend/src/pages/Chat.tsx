import React, { useEffect, useRef, useState } from 'react';
import { Bot, Clock, MessageSquare, Plus, Send, Ticket, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Message } from '../types';
import { cn } from '../lib/utils';
import {
  ChatSessionRecord,
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

export function Chat() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [historySessions, setHistorySessions] = useState<ChatSessionRecord[]>([]);
  const [messages, setMessages] = useState<Message[]>([newWelcomeMessage()]);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const refreshHistorySessions = async () => {
    if (!user) {
      setHistorySessions([]);
      return;
    }
    try {
      setHistorySessions(await listChatSessions(user.token));
    } catch (err) {
      console.error('Error fetching chat sessions:', err);
    }
  };

  useEffect(() => {
    void refreshHistorySessions();
  }, [user?.token]);

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([newWelcomeMessage()]);
    setIsSidebarOpen(false);
  };

  const handleSelectSession = async (session: ChatSessionRecord) => {
    if (!user) return;
    setIsLoading(true);
    try {
      const history = await getChatSessionMessages(user.token, session.id);
      setSessionId(session.id);
      setMessages(
        history.length > 0
          ? history.map((message) => ({
              id: message.id,
              sender: message.sender,
              text: message.text,
              timestamp: message.timestamp || new Date().toISOString(),
              citations: message.citations,
            }))
          : [newWelcomeMessage()],
      );
      setIsSidebarOpen(false);
    } catch (err) {
      console.error('Error loading chat session:', err);
    } finally {
      setIsLoading(false);
    }
  };

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
                      .filter((action) => action.type !== 'none')
                      .map((action) => ({ name: action.label, url: action.type, data: action.data })),
                  }
                : message,
            ),
          );
          void refreshHistorySessions();
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

  const handleDismissEscalation = (messageId: string, attachmentIndex: number) => {
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
    'Tôi còn bao nhiêu ngày phép?',
    'Quy định nghỉ phép cần báo trước bao lâu?',
    'Trạng thái bảo hiểm của tôi là gì?',
  ];

  return (
    <div className="flex flex-col h-full bg-white dark:bg-discord-bg relative overflow-hidden transition-colors">
      <div className="absolute top-4 right-4 z-10 md:top-6 md:right-8 flex items-center gap-3">
        <button
          onClick={handleNewChat}
          className="w-10 h-10 md:w-11 md:h-11 rounded-full bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg flex items-center justify-center text-gray-500 dark:text-discord-text-muted hover:bg-gray-50 dark:hover:bg-discord-card-hover shadow-sm transition-colors"
          title="Phiên trò chuyện mới"
        >
          <Plus size={20} />
        </button>
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="w-10 h-10 md:w-11 md:h-11 rounded-full bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg flex items-center justify-center text-gray-500 dark:text-discord-text-muted hover:bg-gray-50 dark:hover:bg-discord-card-hover shadow-sm transition-colors"
          title="Lịch sử trò chuyện"
        >
          <Clock size={20} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-[15%] pt-20 md:pt-16 pb-6">
        <div className="space-y-6 md:space-y-8 max-w-4xl mx-auto">
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';

            return (
              <div key={msg.id} className={cn('flex items-start gap-4 w-full', isUser ? 'flex-row-reverse' : 'flex-row')}>
                {!isUser && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 bg-brand-mint text-[#048261] dark:bg-discord-accent dark:text-white">
                    <Bot size={18} />
                  </div>
                )}

                <div className="max-w-[85%] md:max-w-[75%] relative flex flex-col gap-3">
                  {isUser ? (
                    <div className="bg-[#f0f4f9] dark:bg-discord-accent text-gray-800 dark:text-white px-5 py-3.5 rounded-[24px] rounded-tr-sm leading-relaxed text-[15px] whitespace-pre-wrap">
                      {msg.text}
                    </div>
                  ) : (
                    <div className="text-gray-800 dark:text-discord-text leading-relaxed whitespace-pre-wrap text-[15px] pt-1">
                      {msg.text}
                    </div>
                  )}

                  {msg.attachments?.map((attachment, i) => (
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
                  ))}
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="text-sm text-gray-500 dark:text-discord-text-muted pl-12">AI đang trả lời...</div>
          )}
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      <div className="shrink-0 w-full bg-gradient-to-t from-white dark:from-discord-bg via-white dark:via-discord-bg to-transparent pb-6 pt-10 px-4 md:px-8 z-20 relative">
        <div className="max-w-3xl mx-auto w-full">
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2 [scrollbar-width:none]">
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
          <p className="text-center text-[11px] text-gray-400 dark:text-discord-text-muted mt-3 font-medium">AI có thể trả lời chưa đầy đủ. Hãy kiểm tra lại thông tin quan trọng.</p>
        </div>
      </div>

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 dark:bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <div
        className={cn(
          'fixed inset-y-0 right-0 w-[280px] md:w-80 bg-white dark:bg-discord-sidebar shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col',
          isSidebarOpen ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <div className="flex items-center justify-between p-5 border-b border-gray-100 dark:border-discord-bg">
          <h2 className="text-lg font-bold text-gray-900 dark:text-discord-text flex items-center gap-2">
            <Clock size={20} className="text-brand-blue dark:text-discord-accent" />
            Lịch sử trò chuyện
          </h2>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-discord-card text-gray-500 dark:text-discord-text-muted transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        <div className="p-4 border-b border-gray-100 dark:border-discord-bg">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 rounded-xl border border-gray-200 dark:border-discord-bg px-4 py-2.5 text-sm font-semibold text-gray-700 dark:text-discord-text hover:bg-gray-50 dark:hover:bg-discord-card transition-colors"
          >
            <Plus size={16} />
            Đoạn chat mới
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-1">
            {historySessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleSelectSession(session)}
                className={cn(
                  'w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-discord-card transition-colors text-left group',
                  sessionId === session.id && 'bg-[#e0fbf4] dark:bg-discord-card-hover',
                )}
              >
                <div className="w-8 h-8 rounded-full bg-[#f8f9fc] dark:bg-discord-card flex items-center justify-center text-gray-400 dark:text-discord-text-muted group-hover:text-brand-blue dark:group-hover:text-discord-accent transition-colors shrink-0">
                  <MessageSquare size={16} />
                </div>
                <div className="min-w-0 flex-1">
                  <span className="block text-[14px] font-medium text-gray-700 dark:text-discord-text group-hover:text-gray-900 dark:group-hover:text-white truncate">
                    {session.title || 'Cuộc trò chuyện'}
                  </span>
                  <span className="block text-[11px] text-gray-400 dark:text-discord-text-muted mt-0.5">
                    {session.updated_at ? new Date(session.updated_at).toLocaleDateString('vi-VN') : ''}
                  </span>
                </div>
              </button>
            ))}
            {historySessions.length === 0 && (
              <div className="text-sm text-gray-400 dark:text-discord-text-muted text-center py-8">
                Chưa có lịch sử trò chuyện
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
