import React, { useEffect, useRef, useState } from 'react';
import { Bot, RotateCcw, Send, Ticket, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Message } from '../types';
import { cn } from '../lib/utils';
import { streamChatRequest } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

export function Chat() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: 'Xin chào. Tôi là AI hỗ trợ nhân sự. Bạn có thể hỏi về chính sách nghỉ phép, bảo hiểm, phúc lợi hoặc tạo ticket cho HR.',
      timestamp: new Date().toISOString(),
    },
  ]);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
                      .map((action) => ({ name: action.label, url: action.type })),
                  }
                : message,
            ),
          );
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
      handleSend();
    }
  };

  const suggestions = [
    'Tôi còn bao nhiêu ngày phép?',
    'Quy định nghỉ phép cần báo trước bao lâu?',
    'Trạng thái bảo hiểm của tôi là gì?',
  ];

  return (
    <div className="flex flex-col h-full bg-[#f8f9fc] relative">
      <div className="absolute top-4 right-4 z-10 md:top-6 md:right-8">
        <button
          onClick={() => {
            setSessionId(null);
            setMessages(messages.slice(0, 1));
          }}
          className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500 hover:bg-gray-50 shadow-sm transition-colors"
          title="Làm mới cuộc trò chuyện"
        >
          <RotateCcw size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-[15%] pt-16 md:pt-12 pb-6">
        <div className="space-y-6 md:space-y-8">
          {messages.map((msg, index) => {
            const isUser = msg.sender === 'user';
            const nextIsSame = messages[index + 1]?.sender === msg.sender;

            return (
              <div key={msg.id} className={cn('flex items-start gap-4 w-full', isUser ? 'flex-row-reverse' : 'flex-row')}>
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1',
                    isUser ? 'bg-[#3563E9] text-white' : 'bg-brand-mint text-brand-blue',
                    nextIsSame && 'opacity-0',
                  )}
                >
                  {isUser ? <User size={18} /> : <Bot size={18} />}
                </div>

                <div className={cn('max-w-[78%] rounded-2xl relative', isUser ? 'bg-[#062474] text-white shadow-md p-4' : 'flex flex-col gap-3')}>
                  {!isUser && <div className="absolute left-[-26px] top-6 w-0.5 h-[calc(100%+16px)] bg-brand-mint" />}

                  {isUser ? (
                    <div className="leading-relaxed text-[15px] whitespace-pre-wrap">{msg.text}</div>
                  ) : (
                    <div className="bg-white border border-gray-100 shadow-sm rounded-2xl p-5 text-gray-800 leading-relaxed whitespace-pre-wrap text-[15px]">
                      {msg.text}
                    </div>
                  )}

                  {msg.attachments?.map((attachment, i) => (
                    <div key={`${attachment.name}-${i}`} className="bg-white border border-[#a6f4df] ring-1 ring-brand-mint shadow-sm rounded-xl p-5 relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-1.5 h-full bg-[#048261]" />
                      <div className="flex items-start gap-4 mb-4 px-2">
                        <div className="w-10 h-10 rounded-full bg-[#e0fbf4] text-[#048261] flex items-center justify-center shrink-0 mt-1">
                          <Ticket size={20} />
                        </div>
                        <div>
                          <h4 className="text-[15px] font-bold text-gray-900 leading-tight">{attachment.name}</h4>
                          <p className="text-sm text-gray-600">Hệ thống đã thực hiện hành động liên quan đến yêu cầu của bạn.</p>
                        </div>
                      </div>
                      {attachment.url === 'escalation_created' && (
                        <div className="flex justify-end border-t border-gray-100 pt-3">
                          <button
                            onClick={() => navigate(user?.role === 'admin' ? '/admin/tickets' : '/tickets')}
                            className="px-4 py-2 text-sm font-medium bg-brand-blue text-white rounded-lg hover:bg-[#051c5e] transition-colors shadow-sm flex items-center gap-1.5"
                          >
                            Xem ticket <Send size={14} />
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
            <div className="text-sm text-gray-500 pl-12">AI đang trả lời...</div>
          )}
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      <div className="shrink-0 w-full border-t border-gray-100 bg-[#f8f9fc] pt-4 pb-4 md:pb-6 px-4 md:px-8 lg:px-[15%] z-20">
        <div className="flex gap-2 mb-3 md:mb-4 overflow-x-auto pb-2 [scrollbar-width:none]">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInput(suggestion)}
              className="whitespace-nowrap px-4 py-1.5 rounded-full bg-[#e0fbf4] border border-[#a6f4df] text-[#048261] text-sm font-medium hover:bg-[#c9f9ec] transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nhập câu hỏi HR..."
            className="w-full bg-white border border-gray-200 rounded-2xl py-4 pl-4 pr-16 outline-none focus:border-brand-blue shadow-sm text-[15px]"
          />
          <button
            onClick={handleSend}
            className="absolute right-3 p-2.5 bg-[#046c4e] text-white rounded-xl hover:bg-[#03543d] transition-colors disabled:opacity-50 shadow-sm"
            disabled={!input.trim() || isLoading}
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-3 font-medium">AI có thể trả lời chưa đầy đủ. Hãy kiểm tra lại thông tin quan trọng.</p>
      </div>
    </div>
  );
}
