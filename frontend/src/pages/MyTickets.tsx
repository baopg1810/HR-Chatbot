import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, FileText, Plus, Search, Ticket as TicketIcon } from 'lucide-react';
import { cn } from '../lib/utils';
import { listMyTickets, TicketRecord } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

const statusLabel: Record<TicketRecord['status'], string> = {
  open: 'Cần xử lý',
  in_progress: 'Đang xử lý',
  resolved: 'Đã hoàn thành',
  rejected: 'Từ chối xử lý',
};

const priorityLabel: Record<TicketRecord['priority'], string> = {
  low: 'Thấp',
  normal: 'Bình thường',
  high: 'Cao',
};

export function MyTickets() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<TicketRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    async function loadTickets() {
      setIsLoading(true);
      setError('');
      try {
        const nextTickets = await listMyTickets(user.token);
        if (cancelled) return;
        setTickets(nextTickets);
        if (!selectedTicketId && nextTickets[0]) {
          setSelectedTicketId(nextTickets[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          setTickets([]);
          setError(err instanceof Error ? err.message : 'Không thể tải ticket của bạn.');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadTickets();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const filteredTickets = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return tickets;
    return tickets.filter((ticket) =>
      ticket.id.toLowerCase().includes(query)
      || ticket.summary.toLowerCase().includes(query)
      || ticket.reason.toLowerCase().includes(query)
    );
  }, [searchQuery, tickets]);

  const selectedTicket = tickets.find((ticket) => ticket.id === selectedTicketId) || filteredTickets[0];

  return (
    <div className="flex bg-white dark:bg-discord-bg h-full overflow-hidden w-full relative transition-colors">
      <div className={cn(
        'w-full md:w-[400px] border-r border-gray-200 dark:border-discord-bg flex-col bg-gray-50/50 dark:bg-discord-sidebar shrink-0 h-full absolute inset-0 z-10 md:relative transition-all duration-300',
        selectedTicketId ? '-translate-x-full md:translate-x-0 md:flex flex' : 'translate-x-0 flex',
      )}>
        <div className="p-4 md:p-6 border-b border-gray-200 dark:border-discord-bg">
          <div className="flex items-center justify-between mb-4 md:mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-discord-text tracking-tight">Yêu cầu của tôi</h1>
              <p className="text-gray-500 dark:text-discord-text-muted text-sm">Theo dõi các ticket bạn đã gửi cho HR.</p>
            </div>
            <button
              onClick={() => navigate('/submit-ticket')}
              className="w-10 h-10 rounded-full bg-brand-mint dark:bg-discord-accent text-brand-blue dark:text-white flex items-center justify-center shadow-sm hover:bg-[#5cefc1] dark:hover:bg-[#4752C4] transition-colors"
              title="Tạo yêu cầu mới"
            >
              <Plus size={20} />
            </button>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-discord-text-muted" size={18} />
            <input
              type="text"
              placeholder="Tìm kiếm yêu cầu..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent text-[15px] text-gray-800 dark:text-discord-text transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {error && <div className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm font-medium text-red-700">{error}</div>}
          {isLoading ? (
            [0, 1, 2].map((item) => <div key={item} className="h-28 rounded-xl bg-gray-100 dark:bg-discord-card animate-pulse" />)
          ) : filteredTickets.length > 0 ? (
            filteredTickets.map((ticket) => {
              const isSelected = ticket.id === selectedTicketId;
              return (
                <div
                  key={ticket.id}
                  onClick={() => setSelectedTicketId(ticket.id)}
                  className={cn(
                    'bg-white dark:bg-discord-card p-4 rounded-xl border transition-all cursor-pointer relative overflow-hidden',
                    isSelected
                      ? 'border-brand-blue dark:border-discord-accent shadow-md ring-1 ring-brand-blue dark:ring-discord-accent'
                      : 'border-gray-200 dark:border-discord-bg shadow-sm hover:shadow-md dark:hover:border-discord-text-muted/20',
                  )}
                >
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <span className="text-sm font-semibold text-brand-blue dark:text-discord-accent">{ticket.id}</span>
                    <span className={cn('text-[10px] px-2 py-0.5 rounded border font-medium flex items-center gap-1', getStatusColor(ticket.status))}>
                      <span className={cn('w-1.5 h-1.5 rounded-full', getStatusIconColor(ticket.status))} />
                      {statusLabel[ticket.status]}
                    </span>
                  </div>
                  <h3 className="text-[15px] font-semibold text-gray-900 dark:text-discord-text mb-1 leading-tight line-clamp-1">{ticket.summary}</h3>
                  <p className="text-sm text-gray-500 dark:text-discord-text-muted line-clamp-1 mb-2">{ticket.reason}</p>
                  <div className="text-right">
                    <span className="text-xs font-medium text-gray-400 dark:text-discord-text-muted">{formatDate(ticket.updated_at)}</span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 gap-3">
              <TicketIcon size={44} className="opacity-30" />
              <p className="text-sm font-medium">Bạn chưa có ticket nào.</p>
            </div>
          )}
        </div>
      </div>

      <div className={cn(
        'flex-1 flex flex-col bg-[#f8f9fc] dark:bg-discord-bg h-full absolute inset-0 md:relative z-20 transition-all duration-300',
        selectedTicketId ? 'translate-x-0' : 'translate-x-full md:translate-x-0 hidden md:flex',
      )}>
        {selectedTicket ? (
          <>
            <div className="h-14 md:h-16 px-4 md:px-6 bg-white dark:bg-discord-sidebar border-b border-gray-200 dark:border-discord-bg flex items-center gap-3 shrink-0 shadow-sm z-10 transition-colors">
              <button
                onClick={() => setSelectedTicketId(null)}
                className="md:hidden p-2 -ml-2 text-gray-500 dark:text-discord-text-muted hover:bg-gray-100 dark:hover:bg-discord-card rounded-lg"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                <h2 className="font-semibold text-gray-900 dark:text-discord-text leading-tight">Chi tiết ticket: {selectedTicket.id}</h2>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-10 space-y-6">
              <div className="bg-white dark:bg-discord-sidebar p-6 rounded-2xl border border-gray-100 dark:border-discord-bg shadow-sm mb-6 transition-colors">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className={cn('text-[11px] px-2.5 py-1 rounded-md border font-bold', getStatusColor(selectedTicket.status))}>{statusLabel[selectedTicket.status]}</span>
                  <span className="text-[11px] px-2.5 py-1 rounded-md border border-gray-200 text-gray-500 font-bold">Ưu tiên: {priorityLabel[selectedTicket.priority]}</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-discord-text mb-2">{selectedTicket.summary}</h3>
                <p className="text-[15px] text-gray-600 dark:text-discord-text-muted whitespace-pre-wrap mb-4">{selectedTicket.reason}</p>
                <div className="flex flex-wrap items-center gap-3 text-xs font-medium text-gray-500 dark:text-discord-text-muted">
                  <span className="flex items-center gap-1 bg-gray-50 dark:bg-discord-card px-3 py-1.5 rounded-lg"><Clock size={16} /> Mở ngày {formatDate(selectedTicket.created_at)}</span>
                  <span className="flex items-center gap-1 bg-gray-50 dark:bg-discord-card px-3 py-1.5 rounded-lg"><Clock size={16} /> Cập nhật {formatDateTime(selectedTicket.updated_at)}</span>
                </div>
              </div>

              <div className="rounded-2xl border border-gray-100 dark:border-discord-bg bg-white dark:bg-discord-sidebar p-6">
                <h3 className="text-sm font-bold text-gray-900 dark:text-discord-text mb-2">Luồng xử lý</h3>
                <p className="text-sm text-gray-500 dark:text-discord-text-muted">
                  Ticket đang ở trạng thái "{statusLabel[selectedTicket.status]}".
                  {selectedTicket.assignee_id ? ` Người xử lý hiện tại: ${selectedTicket.assignee_id}.` : ' HR chưa gán người xử lý.'}
                </p>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500 dark:text-discord-text-muted">
            <div className="w-16 h-16 bg-white dark:bg-discord-sidebar rounded-full border border-gray-100 dark:border-discord-bg shadow-sm flex items-center justify-center mb-4">
              <FileText size={32} className="text-gray-300 dark:text-discord-text-muted" />
            </div>
            <p className="font-medium text-gray-500 dark:text-discord-text-muted">Chọn một yêu cầu để xem chi tiết.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function getStatusColor(status: TicketRecord['status']) {
  switch (status) {
    case 'in_progress': return 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-100 dark:border-indigo-500/20';
    case 'open': return 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-100 dark:border-amber-500/20';
    case 'resolved': return 'bg-gray-100 dark:bg-discord-card text-gray-700 dark:text-discord-text-muted border-gray-200 dark:border-discord-bg';
    case 'rejected': return 'bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-red-100 dark:border-red-500/20';
  }
}

function getStatusIconColor(status: TicketRecord['status']) {
  switch (status) {
    case 'in_progress': return 'bg-indigo-500';
    case 'open': return 'bg-amber-500';
    case 'resolved': return 'bg-gray-400';
    case 'rejected': return 'bg-red-500';
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('vi-VN');
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('vi-VN');
}
