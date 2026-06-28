import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Ban, Calendar, Check, CheckCircle2, Clock, Filter, Flag, MessageSquare, Search, Sparkles, Ticket, User } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '../lib/utils';
import {
  approveTrendCandidate,
  listAdminTickets,
  listTrendCandidates,
  listTrendPins,
  runTrending,
  TicketRecord,
  TrendCandidate,
  TrendPin,
  updateTicket,
} from '../lib/api';
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

export function ManageTickets() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<TicketRecord[]>([]);
  const [candidates, setCandidates] = useState<TrendCandidate[]>([]);
  const [pins, setPins] = useState<TrendPin[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'inbox' | 'clusters'>('inbox');
  const [searchQuery, setSearchQuery] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const selectedTicket = tickets.find((ticket) => ticket.id === selectedTicketId) || tickets[0];

  useEffect(() => {
    refresh();
  }, [user]);

  useEffect(() => {
    if (!selectedTicketId && tickets[0]) {
      setSelectedTicketId(tickets[0].id);
    }
    if (selectedTicketId && tickets.length > 0 && !tickets.some((ticket) => ticket.id === selectedTicketId)) {
      setSelectedTicketId(tickets[0].id);
    }
  }, [tickets, selectedTicketId]);

  const refresh = async () => {
    if (!user) return;
    setIsLoading(true);
    setError('');
    try {
      const [nextTickets, nextCandidates, nextPins] = await Promise.all([
        listAdminTickets(user.token),
        listTrendCandidates(user.token),
        listTrendPins(user.token),
      ]);
      setTickets(nextTickets);
      setCandidates(nextCandidates);
      setPins(nextPins);
    } catch (err) {
      setTickets([]);
      setCandidates([]);
      setPins([]);
      setError(err instanceof Error ? err.message : 'Không thể tải danh sách ticket.');
    } finally {
      setIsLoading(false);
    }
  };

  const showMessage = (text: string) => {
    setMessage(text);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleStatusUpdate = async (ticketId: string, status: TicketRecord['status']) => {
    if (!user) return;
    try {
      await updateTicket(user.token, ticketId, { status, assignee_id: user.id });
      showMessage('Đã cập nhật trạng thái ticket thành công.');
      await refresh();
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Không thể cập nhật ticket.');
    }
  };

  const handleRunTrending = async () => {
    if (!user) return;
    try {
      const result = await runTrending(user.token, 2, 60) as { created_candidates?: TrendCandidate[] };
      const createdCount = result.created_candidates?.length || 0;
      showMessage(createdCount > 0 ? `Đã tạo ${createdCount} trend candidate chờ duyệt.` : 'Không có trend candidate mới.');
      await refresh();
      setActiveTab('clusters');
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Không thể chạy trending.');
    }
  };

  const handleApproveCandidate = async (candidateId: string) => {
    if (!user) return;
    try {
      await approveTrendCandidate(user.token, candidateId);
      showMessage('Đã duyệt và ghim TrendPin.');
      await refresh();
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Không thể duyệt TrendPin.');
    }
  };

  const filteredTickets = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return tickets;
    return tickets.filter((ticket) =>
      ticket.id.toLowerCase().includes(query)
      || ticket.summary.toLowerCase().includes(query)
      || ticket.requester_id.toLowerCase().includes(query)
      || ticket.reason.toLowerCase().includes(query)
    );
  }, [searchQuery, tickets]);

  return (
    <div className="flex bg-gray-50 dark:bg-discord-bg h-full overflow-hidden w-full relative font-sans text-brand-text dark:text-discord-text transition-colors duration-300">
      <AnimatePresence>
        {message && (
          <motion.div
            initial={{ opacity: 0, y: -20, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: -20, x: '-50%' }}
            className="absolute top-4 left-1/2 z-50 rounded-xl border border-brand-mint/50 bg-brand-mint-light/90 backdrop-blur-sm px-6 py-3 text-sm font-semibold text-[#048261] shadow-lg flex items-center gap-2"
          >
            <CheckCircle2 size={18} />
            {message}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="w-full md:w-[400px] border-r border-gray-200 dark:border-discord-bg flex flex-col bg-white dark:bg-discord-sidebar shrink-0 h-full z-10 shadow-[2px_0_10px_rgba(0,0,0,0.02)] transition-colors">
        <div className="p-5 border-b border-gray-100 dark:border-discord-bg">
          <h1 className="text-2xl font-extrabold text-gray-900 dark:text-discord-text mb-5 tracking-tight">Quản lý yêu cầu</h1>

          <div className="flex bg-gray-100/80 p-1.5 rounded-xl mb-5 relative">
            <button
              onClick={() => setActiveTab('inbox')}
              className={cn('flex-1 text-sm font-semibold py-2 rounded-lg transition-all relative z-10', activeTab === 'inbox' ? 'text-brand-blue' : 'text-gray-500 hover:text-gray-800')}
            >
              Hộp thư xử lý
            </button>
            <button
              onClick={() => setActiveTab('clusters')}
              className={cn('flex-1 text-sm font-semibold py-2 rounded-lg transition-all relative z-10 flex justify-center items-center gap-2', activeTab === 'clusters' ? 'text-brand-blue' : 'text-gray-500 hover:text-gray-800')}
            >
              <Sparkles size={16} /> Phân tích xu hướng
            </button>
            <motion.div
              className="absolute top-1.5 bottom-1.5 w-[calc(50%-6px)] bg-white dark:bg-discord-card rounded-lg shadow-sm"
              animate={{ left: activeTab === 'inbox' ? '6px' : 'calc(50% + 0px)' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            />
          </div>

          {activeTab === 'inbox' ? (
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-discord-text-muted" size={18} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm kiếm ticket..."
                className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-discord-bg border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-2 focus:ring-brand-blue/20 dark:focus:ring-discord-accent/20 focus:bg-white dark:focus:bg-discord-card text-sm font-medium transition-all"
              />
            </div>
          ) : (
            <button onClick={handleRunTrending} className="w-full flex items-center justify-center gap-2 rounded-xl bg-brand-blue hover:bg-[#041952] px-4 py-2.5 text-sm font-bold text-white transition-all shadow-sm">
              <Filter size={16} /> Chạy phân tích
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto bg-gray-50/30 dark:bg-discord-sidebar/50">
          {error && <div className="m-4 rounded-xl border border-red-100 bg-red-50 p-3 text-sm font-medium text-red-700">{error}</div>}
          {activeTab === 'inbox' ? (
            isLoading ? (
              <LoadingList />
            ) : filteredTickets.length > 0 ? (
              <div className="p-3 space-y-2">
                <AnimatePresence>
                  {filteredTickets.map((ticketItem) => {
                    const isSelected = ticketItem.id === selectedTicket?.id;
                    return (
                      <motion.div
                        layout
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        key={ticketItem.id}
                        onClick={() => setSelectedTicketId(ticketItem.id)}
                        className={cn(
                          'p-4 rounded-xl cursor-pointer transition-all relative border',
                          isSelected
                            ? 'bg-white dark:bg-discord-card border-brand-blue/30 dark:border-discord-accent/50 shadow-[0_4px_20px_-4px_rgba(6,36,116,0.1)] dark:shadow-none ring-1 ring-brand-blue/10 dark:ring-discord-accent/30'
                            : 'bg-white dark:bg-transparent border-transparent hover:border-gray-200 dark:hover:border-discord-bg hover:shadow-sm dark:hover:bg-discord-card/50',
                        )}
                      >
                        {isSelected && <motion.div layoutId="active-indicator" className="absolute left-0 top-3 bottom-3 w-1 bg-brand-blue dark:bg-discord-accent rounded-r-md" />}
                        <div className="flex justify-between items-start mb-2 gap-2">
                          <span className={cn('text-[11px] px-2.5 py-1 rounded-md border font-bold flex items-center gap-1.5 shrink-0', getStatusColor(ticketItem.status))}>
                            <span className={cn('w-1.5 h-1.5 rounded-full', getStatusIndicator(ticketItem.status))} />
                            {statusLabel[ticketItem.status]}
                          </span>
                          <span className="text-[11px] font-semibold text-gray-400 whitespace-nowrap">{formatDate(ticketItem.updated_at)}</span>
                        </div>
                        <h4 className="font-bold text-gray-900 dark:text-discord-text text-sm mb-1.5 line-clamp-1">{ticketItem.summary}</h4>
                        <div className="flex items-center justify-between mt-3">
                          <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-discord-text-muted">
                            <div className="w-6 h-6 rounded-full bg-brand-blue/10 text-brand-blue flex items-center justify-center font-bold">{ticketItem.requester_id.substring(0, 2).toUpperCase()}</div>
                            <span className="truncate max-w-[120px]">{ticketItem.requester_id}</span>
                          </div>
                          {ticketItem.priority === 'high' && <span className="flex items-center gap-1 text-[10px] font-bold text-red-600 bg-red-50 px-2 py-1 rounded-md">Khẩn cấp</span>}
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            ) : (
              <EmptyList icon={<Ticket size={48} />} text="Chưa có ticket nào." />
            )
          ) : (
            <TrendPanel candidates={candidates} pins={pins} onApprove={handleApproveCandidate} loading={isLoading} />
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-[#f8f9fc] dark:bg-discord-bg h-full overflow-hidden transition-colors">
        {selectedTicket && activeTab === 'inbox' ? (
          <>
            <div className="bg-white/80 dark:bg-discord-sidebar/80 backdrop-blur-md border-b border-gray-200 dark:border-discord-bg px-6 py-4 flex flex-wrap items-center justify-between shrink-0 shadow-sm z-20 gap-4 sticky top-0 transition-colors">
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm shrink-0 bg-brand-blue shadow-md shadow-brand-blue/20">
                  <Ticket size={20} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-gray-400">{selectedTicket.id}</span>
                    <span className={cn('px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', getStatusColor(selectedTicket.status))}>{statusLabel[selectedTicket.status]}</span>
                  </div>
                  <h2 className="font-extrabold text-gray-900 dark:text-discord-text text-lg leading-tight truncate">{selectedTicket.summary}</h2>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {selectedTicket.status === 'open' && (
                  <button onClick={() => handleStatusUpdate(selectedTicket.id, 'in_progress')} className="rounded-xl bg-blue-600 dark:bg-discord-accent text-white hover:bg-blue-700 dark:hover:bg-[#4752C4] px-5 py-2.5 text-sm font-bold transition-all flex items-center gap-2">
                    <CheckCircle2 size={18} /> Tiếp nhận xử lý
                  </button>
                )}
                {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'rejected' && (
                  <button onClick={() => handleStatusUpdate(selectedTicket.id, 'rejected')} className="rounded-xl bg-red-600 text-white hover:bg-red-700 px-5 py-2.5 text-sm font-bold transition-all flex items-center gap-2">
                    <Ban size={18} /> Từ chối xử lý
                  </button>
                )}
                {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'rejected' && (
                  <button onClick={() => handleStatusUpdate(selectedTicket.id, 'resolved')} className="rounded-xl bg-[#048261] text-white hover:bg-[#036e52] px-5 py-2.5 text-sm font-bold transition-all flex items-center gap-2">
                    <Check size={18} /> Đánh dấu hoàn thành
                  </button>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 relative">
              <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-sm overflow-hidden shrink-0">
                <div className="bg-gray-50/80 dark:bg-discord-sidebar/50 px-6 py-4 border-b border-gray-100 dark:border-discord-bg grid grid-cols-2 md:grid-cols-4 gap-4">
                  <TicketMeta label="Người yêu cầu" value={selectedTicket.requester_id} icon={<User size={14} className="text-gray-400" />} />
                  <TicketMeta label="Ngày tạo" value={formatDate(selectedTicket.created_at)} icon={<Calendar size={14} className="text-gray-400" />} />
                  <TicketMeta label="Mức độ ưu tiên" value={priorityLabel[selectedTicket.priority]} icon={<Flag size={14} className={selectedTicket.priority === 'high' ? 'text-red-500' : 'text-gray-400'} />} />
                  <TicketMeta label="Mã nhân viên" value={`#NV-${selectedTicket.requester_id.substring(0, 4).toUpperCase()}`} />
                </div>
                <div className="p-6">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-discord-text mb-3 flex items-center gap-2">
                    <MessageSquare size={16} className="text-brand-blue dark:text-discord-accent" /> Nội dung chi tiết
                  </h3>
                  <div className="bg-brand-gray/50 dark:bg-discord-card rounded-xl p-5 text-[15px] text-gray-800 dark:text-discord-text leading-relaxed whitespace-pre-wrap border border-gray-100/50 dark:border-discord-bg">
                    {selectedTicket.reason}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-center my-2">
                <div className="h-px bg-gray-200 dark:bg-discord-bg flex-1" />
                <span className="px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Lịch sử xử lý</span>
                <div className="h-px bg-gray-200 dark:bg-discord-bg flex-1" />
              </div>

              <div className="rounded-2xl border border-gray-100 dark:border-discord-bg bg-white dark:bg-discord-sidebar p-5 text-sm text-gray-600 dark:text-discord-text-muted">
                Ticket được tạo lúc {formatDateTime(selectedTicket.created_at)} và cập nhật gần nhất lúc {formatDateTime(selectedTicket.updated_at)}.
                {selectedTicket.assignee_id ? ` Người xử lý hiện tại: ${selectedTicket.assignee_id}.` : ' Chưa có người xử lý được gán.'}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center bg-gray-50/50 dark:bg-discord-bg">
            <div className="w-24 h-24 bg-white dark:bg-discord-sidebar rounded-full flex items-center justify-center shadow-sm border border-gray-100 dark:border-discord-bg mb-6">
              <Ticket size={40} className="text-brand-blue/30 dark:text-discord-accent/30" />
            </div>
            <h2 className="text-xl font-extrabold text-gray-900 dark:text-discord-text mb-2">Chưa chọn ticket nào</h2>
            <p className="text-gray-500 dark:text-discord-text-muted font-medium text-sm">Vui lòng chọn một ticket từ danh sách bên trái để bắt đầu xử lý.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function TrendPanel({
  candidates,
  pins,
  onApprove,
  loading,
}: {
  candidates: TrendCandidate[];
  pins: TrendPin[];
  onApprove: (candidateId: string) => void;
  loading: boolean;
}) {
  if (loading) return <LoadingList />;
  if (pins.length === 0 && candidates.length === 0) {
    return <EmptyList icon={<Sparkles size={48} />} text="Chưa có chủ đề nổi bật nào." />;
  }
  return (
    <div className="p-4 space-y-4">
      {candidates.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs font-bold uppercase tracking-wide text-gray-400">Candidate chờ duyệt</div>
          {candidates.map((candidate) => (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} key={candidate.id} className="bg-white border border-amber-200 rounded-2xl p-5 shadow-sm">
              <div className="flex justify-between items-center mb-3">
                <span className="bg-amber-50 text-amber-700 font-extrabold px-3 py-1 rounded-lg text-xs flex items-center gap-1.5">
                  <MessageSquare size={14} /> {candidate.source_query_count} yêu cầu
                </span>
                <span className="text-[11px] uppercase font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded-md">Draft</span>
              </div>
              <h3 className="font-bold text-gray-900 text-[15px] mb-2 leading-snug">{candidate.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-4">{candidate.summary}</p>
              <button onClick={() => onApprove(candidate.id)} className="w-full rounded-xl bg-[#048261] hover:bg-[#036e52] px-4 py-2.5 text-sm font-bold text-white transition-all shadow-sm">
                Duyệt ghim TrendPin
              </button>
            </motion.div>
          ))}
        </div>
      )}
      {pins.map((pin) => (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} key={pin.id} className="bg-white border border-gray-200 hover:border-brand-blue/50 rounded-2xl p-5 shadow-sm transition-all group">
          <div className="flex justify-between items-center mb-3">
            <span className="bg-brand-blue/10 text-brand-blue font-extrabold px-3 py-1 rounded-lg text-xs flex items-center gap-1.5">
              <MessageSquare size={14} /> {pin.source_query_count} yêu cầu
            </span>
            <span className="text-[11px] uppercase font-bold text-red-500 flex items-center gap-1.5 bg-red-50 px-2 py-1 rounded-md">
              <AlertCircle size={12} /> Hot
            </span>
          </div>
          <h3 className="font-bold text-gray-900 text-[15px] mb-2 leading-snug group-hover:text-brand-blue transition-colors">{pin.title}</h3>
          <p className="text-sm text-gray-500 line-clamp-2 leading-relaxed">{pin.summary}</p>
        </motion.div>
      ))}
    </div>
  );
}

function TicketMeta({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div>
      <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1 block">{label}</span>
      <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-discord-text">
        {icon}
        {value}
      </div>
    </div>
  );
}

function LoadingList() {
  return (
    <div className="p-4 space-y-3">
      {[0, 1, 2].map((item) => (
        <div key={item} className="h-24 rounded-xl bg-gray-100 dark:bg-discord-card animate-pulse" />
      ))}
    </div>
  );
}

function EmptyList({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-4 p-6">
      <div className="opacity-20">{icon}</div>
      <p className="text-sm font-medium">{text}</p>
    </div>
  );
}

function getStatusColor(status: TicketRecord['status']) {
  switch (status) {
    case 'in_progress': return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'open': return 'bg-amber-50 text-amber-700 border-amber-200';
    case 'resolved': return 'bg-green-50 text-green-700 border-green-200';
    case 'rejected': return 'bg-red-50 text-red-700 border-red-200';
  }
}

function getStatusIndicator(status: TicketRecord['status']) {
  switch (status) {
    case 'in_progress': return 'bg-blue-500';
    case 'open': return 'bg-amber-500';
    case 'resolved': return 'bg-green-500';
    case 'rejected': return 'bg-red-500';
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('vi-VN');
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('vi-VN');
}
