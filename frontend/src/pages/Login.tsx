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
    <div className="min-h-screen w-full bg-[#f8f9fa] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-10 border border-gray-100">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-full bg-indigo-100 flex flex-col items-center justify-center text-brand-blue mb-4 shadow-sm">
            <Bot size={32} />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 mb-1">Chào mừng trở lại</h1>
          <p className="text-sm text-gray-500">Đăng nhập vào HR Helpdesk AI để tiếp tục.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-gray-700">Địa chỉ email</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Mail size={18} className="text-gray-400" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="employee@example.com"
                className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl focus:ring-brand-blue focus:border-brand-blue sm:text-sm transition-shadow outline-none placeholder:text-gray-300 text-gray-700"
                required
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Demo: employee@example.com / employee123 hoặc admin@example.com / admin123.</p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-medium text-gray-700">Mật khẩu</label>
              <Link to="/forgot-password" className="text-sm font-medium text-brand-blue hover:text-[#051c5e]">
                Quên mật khẩu?
              </Link>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Lock size={18} className="text-gray-400" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="********"
                className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl focus:ring-brand-blue focus:border-brand-blue sm:text-sm transition-shadow outline-none placeholder:text-gray-300 text-gray-700"
                required
              />
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-blue hover:bg-[#051c5e] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue transition-colors mt-2 disabled:opacity-60"
          >
            {isSubmitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
            <ArrowRight size={18} />
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-gray-500">
          Cần hỗ trợ truy cập? Liên hệ <span className="font-medium text-brand-blue">bộ phận IT</span>.
        </p>
      </div>
    </div>
  );
}
