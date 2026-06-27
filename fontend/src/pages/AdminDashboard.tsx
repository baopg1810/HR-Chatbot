import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, BookOpen, CheckCircle2, Clock, FileDown, Ticket, TrendingUp } from 'lucide-react';
import { DocumentRecord, listAdminTickets, listDocuments, listTrendPins, TicketRecord, TrendPin } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

type DashboardActivity = {
  id: string;
  action: string;
  subject: string;
  time: string;
  tone: 'blue' | 'green' | 'amber';
};

type WorkloadItem = {
  label: string;
  count: number;
  percent: number;
  color: string;
};

const STATUS_LABELS: Record<TicketRecord['status'], string> = {
  open: 'Cần xử lý',
  in_progress: 'Đang xử lý',
  resolved: 'Đã hoàn thành',
};

const PRIORITY_LABELS: Record<TicketRecord['priority'], string> = {
  low: 'Thấp',
  normal: 'Bình thường',
  high: 'Cao',
};

export function AdminDashboard() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<TicketRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [pins, setPins] = useState<TrendPin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    async function loadDashboard() {
      setIsLoading(true);
      setError('');
      try {
        const [nextTickets, nextDocuments, nextPins] = await Promise.all([
          listAdminTickets(user.token),
          listDocuments(user.token).catch(() => []),
          listTrendPins(user.token).catch(() => []),
        ]);
        if (cancelled) return;
        setTickets(nextTickets);
        setDocuments(nextDocuments);
        setPins(nextPins);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Không thể tải dữ liệu tổng quan.');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const stats = useMemo(() => {
    const now = Date.now();
    const weekStart = now - 7 * 24 * 60 * 60 * 1000;
    const activeTickets = tickets.filter((ticket) => ticket.status !== 'resolved');
    const urgentTickets = tickets.filter((ticket) => ticket.priority === 'high' && ticket.status !== 'resolved');
    const resolvedThisWeek = tickets.filter(
      (ticket) => ticket.status === 'resolved' && new Date(ticket.updated_at).getTime() >= weekStart,
    );
    const resolvedDurations = tickets
      .filter((ticket) => ticket.status === 'resolved')
      .map((ticket) => new Date(ticket.updated_at).getTime() - new Date(ticket.created_at).getTime())
      .filter((duration) => Number.isFinite(duration) && duration >= 0);
    const averageResolutionHours = resolvedDurations.length
      ? resolvedDurations.reduce((sum, duration) => sum + duration, 0) / resolvedDurations.length / 36e5
      : 0;

    return {
      totalTickets: tickets.length,
      activeTickets: activeTickets.length,
      urgentTickets: urgentTickets.length,
      resolvedThisWeek: resolvedThisWeek.length,
      averageResolutionHours,
      indexedDocuments: documents.filter((document) => document.status === 'indexed').length,
      trendPins: pins.length,
    };
  }, [documents, pins, tickets]);

  const workload = useMemo<WorkloadItem[]>(() => {
    const activeTickets = tickets.filter((ticket) => ticket.status !== 'resolved');
    const total = Math.max(activeTickets.length, 1);
    const groups: WorkloadItem[] = [
      {
        label: 'Cần xử lý',
        count: activeTickets.filter((ticket) => ticket.status === 'open').length,
        percent: 0,
        color: 'bg-amber-500',
      },
      {
        label: 'Đang xử lý',
        count: activeTickets.filter((ticket) => ticket.status === 'in_progress').length,
        percent: 0,
        color: 'bg-brand-blue dark:bg-discord-accent',
      },
      {
        label: 'Ưu tiên cao',
        count: activeTickets.filter((ticket) => ticket.priority === 'high').length,
        percent: 0,
        color: 'bg-red-500',
      },
    ];
    return groups.map((item) => ({
      ...item,
      percent: activeTickets.length ? Math.round((item.count / total) * 100) : 0,
    }));
  }, [tickets]);

  const activities = useMemo<DashboardActivity[]>(() => {
    const ticketActivities = tickets.slice(0, 5).map((ticket) => ({
      id: `ticket-${ticket.id}`,
      action: STATUS_LABELS[ticket.status],
      subject: `${ticket.id} - ${ticket.summary}`,
      time: formatRelativeTime(ticket.updated_at),
      tone: ticket.status === 'resolved' ? 'green' as const : ticket.priority === 'high' ? 'amber' as const : 'blue' as const,
    }));
    const documentActivities = documents.slice(0, 3).map((document) => ({
      id: `document-${document.id}`,
      action: 'Tài liệu',
      subject: `${document.title} (${document.status})`,
      time: formatRelativeTime(document.created_at),
      tone: 'blue' as const,
    }));
    const pinActivities = pins.slice(0, 3).map((pin) => ({
      id: `pin-${pin.id}`,
      action: 'TrendPin',
      subject: `${pin.title} (${pin.source_query_count} câu hỏi)`,
      time: formatRelativeTime(pin.created_at),
      tone: 'amber' as const,
    }));

    return [...ticketActivities, ...documentActivities, ...pinActivities]
      .sort((a, b) => relativeSortValue(b.time) - relativeSortValue(a.time))
      .slice(0, 6);
  }, [documents, pins, tickets]);

  const handleExport = () => {
    const report = {
      generated_at: new Date().toISOString(),
      stats,
      tickets,
      documents,
      trend_pins: pins,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `hr-dashboard-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 md:mb-8 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-discord-text tracking-tight mb-2">Tổng quan HR</h1>
          <p className="text-gray-500 dark:text-discord-text-muted text-sm md:text-[15px]">Theo dõi ticket, tài liệu và chủ đề đang được hỏi từ dữ liệu thật của hệ thống.</p>
        </div>
        <button
          onClick={handleExport}
          disabled={isLoading}
          className="bg-white dark:bg-discord-card border w-fit border-gray-200 dark:border-discord-bg shadow-sm text-gray-700 dark:text-discord-text px-4 py-2 rounded-xl text-sm font-medium hover:bg-gray-50 dark:hover:bg-discord-card-hover transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          <FileDown size={16} /> Xuất báo cáo
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard icon={<Ticket size={20} />} label="Tổng yêu cầu" value={stats.totalTickets} helper={`${stats.activeTickets} ticket đang mở`} tone="blue" loading={isLoading} />
        <MetricCard icon={<Activity size={20} />} label="Cần phản hồi gấp" value={stats.urgentTickets} helper="Ticket ưu tiên cao chưa hoàn thành" tone="red" loading={isLoading} />
        <MetricCard icon={<Clock size={20} />} label="Thời gian xử lý TB" value={`${stats.averageResolutionHours.toFixed(1)}h`} helper="Tính trên ticket đã hoàn thành" tone="indigo" loading={isLoading} />
        <MetricCard icon={<CheckCircle2 size={20} />} label="Đã giải quyết tuần này" value={stats.resolvedThisWeek} helper={`${stats.indexedDocuments} tài liệu đã index`} tone="green" loading={isLoading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 transition-colors">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-discord-text mb-6">Trạng thái khối lượng công việc</h3>
          {isLoading ? (
            <SkeletonRows />
          ) : workload.every((item) => item.count === 0) ? (
            <EmptyState text="Chưa có ticket đang xử lý." />
          ) : (
            <div className="space-y-5">
              {workload.map((item) => (
                <div key={item.label}>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-gray-700 dark:text-discord-text">{item.label}</span>
                    <span className="text-gray-500 dark:text-discord-text-muted">{item.count} ticket</span>
                  </div>
                  <div className="w-full bg-gray-100 dark:bg-discord-card rounded-full h-2">
                    <div className={`${item.color} h-2 rounded-full`} style={{ width: `${Math.max(item.percent, item.count > 0 ? 8 : 0)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 transition-colors">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-discord-text">Hoạt động gần đây</h3>
            <span className="text-sm font-medium text-brand-blue dark:text-discord-accent">{stats.trendPins} TrendPin</span>
          </div>
          {isLoading ? (
            <SkeletonRows />
          ) : activities.length === 0 ? (
            <EmptyState text="Chưa có hoạt động nào." />
          ) : (
            <div className="space-y-4">
              {activities.map((activity) => (
                <div key={activity.id} className="flex items-start gap-4 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-discord-card transition-colors">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${activityToneClass(activity.tone)}`}>
                    {activity.action === 'Tài liệu' ? <BookOpen size={14} /> : activity.action === 'TrendPin' ? <TrendingUp size={14} /> : <Ticket size={14} />}
                  </div>
                  <div>
                    <p className="text-[14px] font-medium text-gray-900 dark:text-discord-text">{activity.action}: <span className="font-normal text-gray-600 dark:text-discord-text-muted">{activity.subject}</span></p>
                    <span className="text-xs text-gray-400 dark:text-discord-text-muted">{activity.time}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  helper,
  tone,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  helper: string;
  tone: 'blue' | 'red' | 'indigo' | 'green';
  loading: boolean;
}) {
  return (
    <div className="bg-white dark:bg-discord-sidebar p-6 rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] transition-colors">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${metricToneClass(tone)}`}>{icon}</div>
      </div>
      <p className="text-sm font-medium text-gray-500 dark:text-discord-text-muted mb-1">{label}</p>
      {loading ? <div className="h-8 w-20 rounded bg-gray-100 dark:bg-discord-card animate-pulse" /> : <p className="text-2xl font-bold text-gray-900 dark:text-discord-text">{value}</p>}
      <p className="mt-2 text-xs font-medium text-gray-400 dark:text-discord-text-muted">{helper}</p>
    </div>
  );
}

function SkeletonRows() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((item) => (
        <div key={item} className="h-12 rounded-xl bg-gray-100 dark:bg-discord-card animate-pulse" />
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed border-gray-200 dark:border-discord-bg p-6 text-sm font-medium text-gray-400 dark:text-discord-text-muted text-center">{text}</div>;
}

function metricToneClass(tone: 'blue' | 'red' | 'indigo' | 'green') {
  const classes = {
    blue: 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400',
    red: 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400',
    indigo: 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
    green: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  };
  return classes[tone];
}

function activityToneClass(tone: DashboardActivity['tone']) {
  const classes = {
    blue: 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400',
    green: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    amber: 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400',
  };
  return classes[tone];
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return 'Không rõ thời gian';
  const diffMs = Date.now() - timestamp;
  const minutes = Math.max(0, Math.floor(diffMs / 60000));
  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} ngày trước`;
  return new Date(value).toLocaleDateString('vi-VN');
}

function relativeSortValue(relativeTime: string) {
  if (relativeTime === 'Vừa xong') return Date.now();
  const match = relativeTime.match(/^(\d+)\s+(phút|giờ|ngày)/);
  if (!match) return 0;
  const amount = Number(match[1]);
  const unit = match[2];
  const multipliers = { phút: 60000, giờ: 36e5, ngày: 86400000 };
  return Date.now() - amount * multipliers[unit as keyof typeof multipliers];
}
