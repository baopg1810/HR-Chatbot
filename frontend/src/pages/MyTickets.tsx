import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Ticket } from '../types';
import { Search, Plus, CheckCircle2, Clock, FileText, AlertCircle, Send, Paperclip, Mic, ArrowLeft } from 'lucide-react';
import { cn } from '../lib/utils';


interface UserTicket extends Ticket {
  lastMessage: string;
}

const MOCK_TICKETS: UserTicket[] = [
  {
    id: '#TK-0042',
    title: 'Hỏi về chính sách nghỉ thai sản',
    description: 'Mình cần hiểu rõ các giấy tờ cần chuẩn bị để nộp yêu cầu nghỉ thai sản sắp tới...',
    status: 'In Progress',
    dateCreated: '26/10/2023',
    lastMessage: 'HR: Vui lòng bổ sung bản sao CMND.',
  },
  {
    id: '#TK-0041',
    title: 'Thiếu biểu mẫu thuế năm 2022',
    description: 'HR yêu cầu bổ sung giấy tờ xác minh. Vui lòng tải lên qua cổng bảo mật.',
    status: 'Action Needed',
    dateCreated: '24/10/2023',
    lastMessage: 'Vui lòng tải lên file bổ sung.',
  },
  {
    id: '#TK-0038',
    title: 'Yêu cầu thiết bị IT (màn hình)',
    description: 'Yêu cầu cấp màn hình ngoài đã được duyệt và bàn giao tại bàn 4B.',
    status: 'Resolved',
    dateCreated: '15/10/2023',
    lastMessage: 'HR: Yêu cầu đã hoàn tất.',
  }
];

const MOCK_TICKET_CHAT = [
  { sender: 'user', text: 'Chào HR, mình cần hỏi về thủ tục nghỉ thai sản ạ.', time: '10:30 AM' },
  { sender: 'hr', text: 'Chào bạn, bạn cần chuẩn bị giấy khám thai và điền form trên portal nhé.', time: '10:35 AM' },
  { sender: 'user', text: 'Mình đã nộp form. HR kiểm tra giúp nhé.', time: '10:42 AM' },
  { sender: 'hr', text: 'Bạn bổ sung thêm bản sao CMND công chứng nữa nhé.', time: '11:00 AM' },
];

export function MyTickets() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const navigate = useNavigate();

  const selectedTicket = MOCK_TICKETS.find(t => t.id === selectedTicketId);
  const statusLabel: Record<Ticket['status'], string> = {
    'In Progress': 'Đang xử lý',
    'Action Needed': 'Cần bổ sung',
    Resolved: 'Đã hoàn tất',
  };

  const getStatusColor = (status: Ticket['status']) => {
    switch (status) {
      case 'In Progress': return 'bg-indigo-50 text-indigo-700 border-indigo-100';
      case 'Action Needed': return 'bg-red-50 text-red-700 border-red-100';
      case 'Resolved': return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getStatusIconColor = (status: Ticket['status']) => {
    switch (status) {
      case 'In Progress': return 'bg-indigo-500';
      case 'Action Needed': return 'bg-red-500';
      case 'Resolved': return 'bg-gray-400';
    }
  }

  return (
    <div className="flex bg-white h-full overflow-hidden w-full relative">
      {/* Inbox List Pane */}
      <div className={cn(
        "w-full md:w-[400px] border-r border-gray-200 flex-col bg-gray-50/50 shrink-0 h-full absolute inset-0 z-10 md:relative transition-transform duration-300",
        selectedTicketId ? "-translate-x-full md:translate-x-0 md:flex flex" : "translate-x-0 flex"
      )}>
        <div className="p-4 md:p-6 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4 md:mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Yêu cầu của tôi</h1>
              <p className="text-gray-500 text-sm">Quản lý và theo dõi yêu cầu của bạn.</p>
            </div>
            <button 
              onClick={() => navigate('/submit-ticket')}
              className="w-10 h-10 rounded-full bg-brand-mint text-brand-blue flex items-center justify-center shadow-sm hover:bg-[#5cefc1] transition-colors"
            >
              <Plus size={20} />
            </button>
          </div>
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input 
              type="text" 
              placeholder="Tìm kiếm yêu cầu..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue text-[15px] transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {MOCK_TICKETS.map(ticket => {
            const isActionNeeded = ticket.status === 'Action Needed';
            const isSelected = ticket.id === selectedTicketId;
            
            return (
              <div 
                key={ticket.id} 
                onClick={() => setSelectedTicketId(ticket.id)}
                className={cn(
                  "bg-white p-4 rounded-xl border transition-all cursor-pointer relative overflow-hidden",
                  isSelected ? "border-brand-blue shadow-md ring-1 ring-brand-blue" : 
                  isActionNeeded ? "border-red-200 shadow-sm hover:shadow-md" : "border-gray-200 shadow-sm hover:shadow-md"
                )}
              >
                {isActionNeeded && (
                  <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-red-600"></div>
                )}
                
                <div className="flex justify-between items-start mb-2">
                  <span className="text-sm font-semibold text-brand-blue">{ticket.id}</span>
                  <span className={cn(
                    "text-[10px] px-2 py-0.5 rounded border font-medium flex items-center gap-1",
                    getStatusColor(ticket.status)
                  )}>
                    <span className={cn("w-1.5 h-1.5 rounded-full", getStatusIconColor(ticket.status))}></span>
                    {statusLabel[ticket.status]}
                  </span>
                </div>
                <h3 className="text-[15px] font-semibold text-gray-900 mb-1 leading-tight line-clamp-1">{ticket.title}</h3>
                <p className="text-sm text-gray-500 line-clamp-1 mb-2">{ticket.lastMessage}</p>
                <div className="text-right">
                  <span className="text-xs font-medium text-gray-400">{ticket.dateCreated}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Ticket Details & Chat Pane */}
      <div className={cn(
        "flex-1 flex col flex-col bg-[#f8f9fc] h-full absolute inset-0 md:relative z-20 transition-transform duration-300",
        selectedTicketId ? "translate-x-0" : "translate-x-full md:translate-x-0 hidden md:flex"
      )}>
        {selectedTicket ? (
          <>
            <div className="h-14 md:h-16 px-4 md:px-6 bg-white border-b border-gray-200 flex items-center gap-3 shrink-0 shadow-sm z-10">
              <button 
                onClick={() => setSelectedTicketId(null)}
                className="md:hidden p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-lg"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                <h2 className="font-semibold text-gray-900 leading-tight">Chi tiết ticket: {selectedTicket.id}</h2>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-10 space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm mb-6">
                 <h3 className="text-xl font-bold text-gray-900 mb-2">{selectedTicket.title}</h3>
                 <p className="text-[15px] text-gray-600 mb-4">{selectedTicket.description}</p>
                 <div className="flex items-center gap-4 text-xs font-medium text-gray-500">
                    <span className="flex items-center gap-1 bg-gray-50 px-3 py-1.5 rounded-lg"><Clock size={16} /> Mở ngày {selectedTicket.dateCreated}</span>
                 </div>
              </div>

              {MOCK_TICKET_CHAT.map((msg, index) => {
                const isUser = msg.sender === 'user';
                
                return (
                  <div key={index} className={cn("flex items-end gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
                     <div className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm", 
                        isUser ? "bg-[#3563E9]" : "bg-brand-blue"
                      )}>
                        {isUser ? "ME" : "HR"}
                      </div>
                    
                    <div className={cn(
                      "max-w-[75%] flex flex-col",
                      isUser ? "items-end" : "items-start"
                    )}>
                      <div className="flex items-center gap-2 mb-1 px-1">
                        <span className="text-xs font-medium text-gray-500">
                          {isUser ? 'Bạn' : 'Bộ phận HR'}
                        </span>
                        <span className="text-[10px] text-gray-400">{msg.time}</span>
                      </div>
                      
                      <div className={cn(
                        "p-4 rounded-2xl shadow-sm text-[15px] leading-relaxed",
                        isUser 
                          ? "bg-[#062474] text-white rounded-br-sm" 
                          : "bg-white border border-gray-100 text-gray-800 rounded-bl-sm"
                      )}>
                        {msg.text}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {selectedTicket.status !== 'Resolved' && (
              <div className="p-4 lg:p-6 bg-white border-t border-gray-200 shrink-0">
                 <div className="relative flex items-center">
                   <div className="absolute left-3 flex items-center gap-2">
                      <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                        <Paperclip size={20} />
                      </button>
                   </div>
                   <input
                     type="text"
                     value={replyText}
                     onChange={(e) => setReplyText(e.target.value)}
                     placeholder="Nhập phản hồi cho HR..."
                     className="w-full bg-gray-50 border border-gray-200 rounded-2xl py-3.5 pl-14 pr-14 outline-none focus:border-brand-blue focus:bg-white transition-all text-[15px]"
                   />
                   <div className="absolute right-2">
                     <button 
                       className="p-2.5 bg-brand-blue text-white rounded-xl hover:bg-[#051c5e] transition-colors disabled:opacity-50 shadow-sm"
                       disabled={!replyText.trim()}
                     >
                       <Send size={18} />
                     </button>
                   </div>
                 </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
            <div className="w-16 h-16 bg-white rounded-full border border-gray-100 shadow-sm flex items-center justify-center mb-4">
               <FileText size={32} className="text-gray-300" />
            </div>
            <p className="font-medium text-gray-500">Chọn một yêu cầu để xem chi tiết và trò chuyện cùng HR.</p>
          </div>
        )}
      </div>
    </div>
  );
}
