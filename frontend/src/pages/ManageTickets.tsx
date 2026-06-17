import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Filter, Search, Send, Sparkles, Ticket } from 'lucide-react';
import { cn } from '../lib/utils';
import { listAdminTickets, listTrendPins, runTrending, TicketRecord, TrendPin, updateTicket } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

const statusLabel: Record<TicketRecord['status'], string> = {
  open: 'Cần xử lý',
  in_progress: 'Đang xử lý',
  resolved: 'Đã hoàn thành',
};

export function ManageTickets() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<TicketRecord[]>([]);
  const [pins, setPins] = useState<TrendPin[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'inbox' | 'clusters'>('inbox');
  const [searchQuery, setSearchQuery] = useState('');
  const [message, setMessage] = useState('');
  const selectedTicket = tickets.find((ticket) => ticket.id === selectedTicketId) || tickets[0];

  useEffect(() => {
    refresh();
  }, [user]);

  useEffect(() => {
    if (!selectedTicketId && tickets[0]) setSelectedTicketId(tickets[0].id);
  }, [tickets, selectedTicketId]);

  const refresh = async () => {
    if (!user) return;
    try {
      const [nextTickets, nextPins] = await Promise.all([
        listAdminTickets(user.token),
        listTrendPins(user.token).catch(() => []),
      ]);
      setTickets(nextTickets);
      setPins(nextPins);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể tải ticket.');
    }
  };

  const handleStatusUpdate = async (ticketId: string, status: TicketRecord['status']) => {
    if (!user) return;
    try {
      await updateTicket(user.token, ticketId, { status, assignee_id: user.id });
      setMessage('Đã cập nhật ticket.');
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể cập nhật ticket.');
    }
  };

  const handleRunTrending = async () => {
    if (!user) return;
    try {
      await runTrending(user.token, 2, 60);
      setMessage('Đã chạy trending.');
      await refresh();
      setActiveTab('clusters');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể chạy trending.');
    }
  };

  const filteredTickets = tickets.filter((ticket) => {
    const query = searchQuery.toLowerCase();
    return ticket.id.toLowerCase().includes(query) || ticket.summary.toLowerCase().includes(query) || ticket.requester_id.toLowerCase().includes(query);
  });

  const getStatusColor = (status: TicketRecord['status']) => {
    switch (status) {
      case 'in_progress': return 'bg-indigo-50 text-indigo-700 border-indigo-100';
      case 'open': return 'bg-red-50 text-red-700 border-red-100';
      case 'resolved': return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getStatusIconColor = (status: TicketRecord['status']) => {
    switch (status) {
      case 'in_progress': return 'bg-indigo-500';
      case 'open': return 'bg-red-500';
      case 'resolved': return 'bg-gray-400';
    }
  };

  return (
    <div className="flex bg-white h-full overflow-hidden w-full relative">
      <div className="w-full md:w-[380px] border-r border-gray-200 flex flex-col bg-gray-50/50 shrink-0 h-full">
        <div className="p-4 md:p-5 border-b border-gray-200 bg-white">
          <h1 className="text-xl font-bold text-gray-900 mb-4">Quản lý yêu cầu HR</h1>

          <div className="flex bg-gray-100 p-1 rounded-xl mb-4">
            <button
              onClick={() => setActiveTab('inbox')}
              className={cn('flex-1 text-sm font-medium py-1.5 rounded-lg transition-colors', activeTab === 'inbox' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700')}
            >
              Hộp thư
            </button>
            <button
              onClick={() => setActiveTab('clusters')}
              className={cn('flex-1 text-sm font-medium py-1.5 rounded-lg transition-colors flex justify-center items-center gap-1.5', activeTab === 'clusters' ? 'bg-white shadow-sm text-brand-blue' : 'text-gray-500 hover:text-gray-700')}
            >
              <Sparkles size={14} /> Trending
            </button>
          </div>

          {activeTab === 'inbox' ? (
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm ticket..."
                className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue text-sm transition-all"
              />
            </div>
          ) : (
            <button onClick={handleRunTrending} className="w-full flex items-center justify-center gap-2 rounded-lg bg-brand-blue px-3 py-2 text-sm font-medium text-white">
              <Filter size={16} /> Chạy trending
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {activeTab === 'inbox' ? (
            filteredTickets.length > 0 ? (
              filteredTickets.map((ticketItem) => {
                const isSelected = ticketItem.id === selectedTicket?.id;
                return (
                  <div
                    key={ticketItem.id}
                    onClick={() => setSelectedTicketId(ticketItem.id)}
                    className={cn('p-4 border-b border-gray-100 cursor-pointer transition-colors relative', isSelected ? 'bg-white shadow-[inset_4px_0_0_0_#062474]' : 'hover:bg-gray-100/50')}
                  >
                    <div className="flex items-start gap-3 w-full">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold shrink-0 mt-0.5 bg-brand-blue">
                        HR
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium block truncate text-gray-900">{ticketItem.requester_id}</span>
                          <span className="text-xs text-gray-400 whitespace-nowrap ml-2">{new Date(ticketItem.updated_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-sm font-medium text-gray-900 mb-0.5 truncate">{ticketItem.summary}</p>
                        <div className="flex gap-2 mt-2">
                          <span className={cn('text-[10px] px-2 py-0.5 rounded border font-medium flex items-center gap-1', getStatusColor(ticketItem.status))}>
                            <span className={cn('w-1.5 h-1.5 rounded-full', getStatusIconColor(ticketItem.status))} />
                            {statusLabel[ticketItem.status]}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center p-6 text-gray-500 mt-10">
                <p className="text-sm">Chưa có ticket nào.</p>
              </div>
            )
          ) : (
            <div className="p-4 space-y-4">
              {pins.map((pin) => (
                <div key={pin.id} className="bg-white border text-left border-gray-200 hover:border-brand-blue rounded-xl p-4 shadow-sm transition-all">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-[#e8f2ff] text-brand-blue font-bold px-2 py-0.5 rounded text-xs">{pin.source_query_count} câu hỏi</span>
                    <span className="text-[10px] uppercase font-bold text-red-500 flex items-center gap-1"><AlertCircle size={12} /> Trending</span>
                  </div>
                  <h3 className="font-semibold text-gray-900 text-sm mb-2 leading-tight">{pin.title}</h3>
                  <p className="text-xs text-gray-500 mb-3">{pin.summary}</p>
                </div>
              ))}
              {pins.length === 0 && <p className="text-sm text-gray-500">Chưa có chủ đề trending.</p>}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-[#f8f9fc] h-full">
        {selectedTicket && activeTab === 'inbox' ? (
          <>
            <div className="h-14 md:h-16 px-4 md:px-6 bg-white border-b border-gray-200 flex items-center justify-between shrink-0 shadow-sm z-10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0 bg-brand-blue">
                  <Ticket size={16} />
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900 leading-tight line-clamp-1">{selectedTicket.id}</h2>
                  <p className="text-xs text-gray-500">{selectedTicket.reason}</p>
                </div>
              </div>
              <span className={cn('text-xs px-2.5 py-1 rounded-full border font-medium flex items-center gap-1.5', getStatusColor(selectedTicket.status))}>
                <span className={cn('w-1.5 h-1.5 rounded-full', getStatusIconColor(selectedTicket.status))} />
                {statusLabel[selectedTicket.status]}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 space-y-6">
              {message && (
                <div className="rounded-xl border border-[#a6f4df] bg-[#e0fbf4] px-4 py-3 text-sm font-medium text-[#048261]">
                  {message}
                </div>
              )}
              <div className="bg-white p-4 md:p-5 rounded-2xl border border-gray-100 shadow-sm mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">{selectedTicket.summary}</h3>
                <p className="text-[15px] text-gray-600 mb-3">Người gửi: {selectedTicket.requester_id}</p>
                <div className="flex flex-wrap items-center gap-3 text-xs font-medium text-gray-500">
                  <span className="flex items-center gap-1 bg-gray-50 p-2 rounded-lg"><Clock size={14} /> Mở ngày {new Date(selectedTicket.created_at).toLocaleString()}</span>
                  <span className="flex items-center gap-1 bg-gray-50 p-2 rounded-lg">Độ ưu tiên: {selectedTicket.priority}</span>
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={() => handleStatusUpdate(selectedTicket.id, 'in_progress')} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white">
                  Đang xử lý
                </button>
                <button onClick={() => handleStatusUpdate(selectedTicket.id, 'resolved')} className="rounded-xl bg-[#046c4e] px-4 py-2 text-sm font-medium text-white">
                  <CheckCircle2 size={16} className="inline mr-1" /> Hoàn thành
                </button>
              </div>
            </div>

            <div className="p-4 bg-white border-t border-gray-200 shrink-0">
              <div className="relative flex items-center bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 text-sm text-gray-500">
                Phản hồi hội thoại ticket sẽ được bổ sung sau. Trang này hiện kết nối CRUD ticket backend.
                <Send size={16} className="ml-auto" />
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
            <p>Chọn một ticket để xử lý.</p>
          </div>
        )}
      </div>
    </div>
  );
}
