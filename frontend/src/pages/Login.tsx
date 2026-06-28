import React, { useState } from 'react';
import { Bot, ArrowRight, Lock, Mail } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function Login() {
  const [email, setEmail] = useState('employee@example.com');
  const [password, setPassword] = useState('employee123');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate('/chat');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Đăng nhập thất bại');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#f8f9fa] dark:bg-discord-card flex items-center justify-center p-4 transition-colors">
      <div className="w-full max-w-md bg-white dark:bg-discord-sidebar rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.3)] p-10 border border-gray-100 dark:border-discord-bg transition-colors">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-full bg-indigo-100 dark:bg-discord-accent/20 flex flex-col items-center justify-center text-brand-blue dark:text-discord-accent mb-4 shadow-sm">
            <Bot size={32} />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-discord-text mb-1">Chào mừng trở lại</h1>
          <p className="text-sm text-gray-500 dark:text-discord-text-muted">Đăng nhập vào HR Helpdesk AI để tiếp tục.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Địa chỉ email</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Mail size={18} className="text-gray-400 dark:text-discord-text-muted" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="employee@example.com"
                className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-discord-bg rounded-xl focus:ring-brand-blue dark:focus:ring-discord-accent focus:border-brand-blue dark:focus:border-discord-accent sm:text-sm transition-shadow outline-none placeholder:text-gray-300 dark:placeholder:text-discord-text-muted text-gray-700 dark:text-discord-text bg-white dark:bg-discord-card"
                required
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-discord-text-muted mt-1">Demo: employee@example.com / employee123 hoặc admin@example.com / admin123.</p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Mật khẩu</label>
              <Link to="/forgot-password" className="text-sm font-medium text-brand-blue dark:text-discord-accent hover:text-[#051c5e] dark:hover:text-[#7983F5]">
                Quên mật khẩu?
              </Link>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Lock size={18} className="text-gray-400 dark:text-discord-text-muted" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="********"
                className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-discord-bg rounded-xl focus:ring-brand-blue dark:focus:ring-discord-accent focus:border-brand-blue dark:focus:border-discord-accent sm:text-sm transition-shadow outline-none placeholder:text-gray-300 dark:placeholder:text-discord-text-muted text-gray-700 dark:text-discord-text bg-white dark:bg-discord-card"
                required
              />
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-red-100 dark:border-red-500/20 bg-red-50 dark:bg-red-500/10 px-4 py-3 text-sm font-medium text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-blue dark:bg-discord-accent hover:bg-[#051c5e] dark:hover:bg-[#4752C4] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue dark:focus:ring-discord-accent transition-colors mt-2 disabled:opacity-60"
          >
            {isSubmitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
            <ArrowRight size={18} />
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-gray-500 dark:text-discord-text-muted">
          Cần hỗ trợ truy cập? Liên hệ <span className="font-medium text-brand-blue dark:text-discord-accent">bộ phận IT</span>.
        </p>
      </div>
    </div>
  );
}
