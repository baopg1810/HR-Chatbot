import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Upload } from 'lucide-react';
import { createEscalation } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

const reasonByTopic: Record<string, string> = {
  leave: 'user_requested',
  benefits: 'user_requested',
  equipment: 'outside_scope',
  documents: 'user_requested',
  other: 'user_requested',
};

export function SubmitTicket() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [topic, setTopic] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!user || !topic || !title || !description) return;
    setIsSubmitting(true);
    setMessage('');
    try {
      const ticket = await createEscalation(user.token, {
        message: `${title}\n\n${description}`,
        reason: reasonByTopic[topic] || 'user_requested',
        priority: topic === 'equipment' ? 'normal' : 'low',
      });
      setMessage(`Đã tạo ticket ${ticket.id}. HR sẽ xử lý tiếp.`);
      setTitle('');
      setDescription('');
      setTopic('');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể tạo ticket.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm font-medium text-gray-500 dark:text-discord-text-muted hover:text-gray-900 dark:hover:text-discord-text mb-6 transition-colors w-fit"
      >
        <ArrowLeft size={16} />
        Quay lại
      </button>

      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-discord-text tracking-tight mb-2">Tạo yêu cầu mới</h1>
        <p className="text-gray-500 dark:text-discord-text-muted text-sm md:text-[15px] mb-6 md:mb-8">Gửi thắc mắc hoặc yêu cầu hỗ trợ đến bộ phận HR.</p>
      </div>

      {message && (
        <div className="mb-6 rounded-xl border border-[#a6f4df] dark:border-discord-accent/30 bg-[#e0fbf4] dark:bg-discord-accent/10 px-4 py-3 text-sm font-medium text-[#048261] dark:text-discord-accent">
          {message}
        </div>
      )}

      <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-5 md:p-8 transition-colors">
        <form className="space-y-6" onSubmit={(event) => event.preventDefault()}>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Chủ đề <span className="text-red-500">*</span></label>
            <select
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full p-3 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent text-[15px] transition-all text-gray-700 dark:text-discord-text"
              required
            >
              <option value="" disabled>-- Chọn chủ đề --</option>
              <option value="leave">Nghỉ phép & Thai sản</option>
              <option value="benefits">Lương & Phúc lợi</option>
              <option value="equipment">Thiết bị & IT Support</option>
              <option value="documents">Giấy tờ & Thủ tục hành chính</option>
              <option value="other">Khác</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Tiêu đề yêu cầu <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Tóm tắt ngắn gọn vấn đề của bạn..."
              className="w-full p-3 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent text-[15px] transition-all text-gray-800 dark:text-discord-text placeholder:text-gray-400 dark:placeholder:text-discord-text-muted"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Mô tả chi tiết <span className="text-red-500">*</span></label>
            <textarea
              rows={5}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Cung cấp thông tin để HR hỗ trợ bạn tốt hơn..."
              className="w-full p-4 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent text-[15px] transition-all resize-none text-gray-800 dark:text-discord-text placeholder:text-gray-400 dark:placeholder:text-discord-text-muted"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Đính kèm tệp tin</label>
            <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 dark:border-discord-bg border-dashed rounded-xl bg-gray-50 dark:bg-discord-card">
              <div className="space-y-1 text-center">
                <Upload className="mx-auto h-12 w-12 text-gray-400 dark:text-discord-text-muted" />
                <p className="text-sm text-gray-500 dark:text-discord-text-muted">Đính kèm sẽ được bổ sung trong phiên bản tiếp theo.</p>
              </div>
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 mt-8 border-t border-gray-100 dark:border-discord-bg">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-600 dark:text-discord-text-muted hover:bg-gray-100 dark:hover:bg-discord-card transition-colors"
            >
              Hủy
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-brand-blue dark:bg-discord-accent text-white hover:bg-[#051c5e] dark:hover:bg-[#4752C4] transition-colors shadow-sm disabled:opacity-50"
              disabled={!topic || !title || !description || isSubmitting}
            >
              <Send size={16} />
              {isSubmitting ? 'Đang gửi...' : 'Gửi yêu cầu'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
