import React, { useState } from 'react';
import { Mail, ArrowLeft, KeyRound, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    
    // Simulate API call for password reset
    setIsSubmitted(true);
  };

  return (
    <div className="min-h-screen w-full bg-[#f8f9fa] dark:bg-discord-card flex items-center justify-center p-4 transition-colors">
      <div className="w-full max-w-md bg-white dark:bg-discord-sidebar rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.3)] p-10 border border-gray-100 dark:border-discord-bg transition-colors">
        
        {!isSubmitted ? (
          <>
            <div className="flex flex-col items-center mb-8 text-center">
              <div className="w-14 h-14 rounded-full bg-indigo-50 dark:bg-discord-accent/20 flex items-center justify-center text-brand-blue dark:text-discord-accent mb-5 shadow-sm">
                <KeyRound size={28} />
              </div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-discord-text mb-2">Quên mật khẩu?</h1>
              <p className="text-sm text-gray-500 dark:text-discord-text-muted">
                Đừng lo lắng, hãy nhập địa chỉ email của bạn và chúng tôi sẽ gửi liên kết để đặt lại mật khẩu.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted">Địa chỉ Email</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <Mail size={18} className="text-gray-400 dark:text-discord-text-muted" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="nhanvien@congty.com"
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-discord-bg rounded-xl focus:ring-brand-blue dark:focus:ring-discord-accent focus:border-brand-blue dark:focus:border-discord-accent sm:text-sm transition-shadow outline-none placeholder:text-gray-300 dark:placeholder:text-discord-text-muted text-gray-700 dark:text-discord-text bg-white dark:bg-discord-card"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-blue dark:bg-discord-accent hover:bg-[#051c5e] dark:hover:bg-[#4752C4] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue dark:focus:ring-discord-accent transition-colors"
              >
                Gửi liên kết đặt lại
              </button>
            </form>
          </>
        ) : (
          <div className="flex flex-col items-center text-center py-4">
            <div className="w-16 h-16 rounded-full bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-500 dark:text-emerald-400 mb-6 shadow-sm">
              <CheckCircle2 size={32} />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-discord-text mb-2">Đã gửi liên kết!</h1>
            <p className="text-[15px] text-gray-500 dark:text-discord-text-muted mb-8 leading-relaxed">
              Chúng tôi đã gửi một email có chứa hướng dẫn đặt lại mật khẩu đến <br/>
              <span className="font-medium text-gray-900 dark:text-discord-text">{email}</span>
            </p>
            <button
              onClick={() => setIsSubmitted(false)}
              className="text-sm font-medium text-brand-blue dark:text-discord-accent hover:text-[#051c5e] dark:hover:text-[#7983F5] hover:underline"
            >
              Gửi lại email
            </button>
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-gray-100 dark:border-discord-bg flex justify-center">
          <Link 
            to="/" 
            className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-discord-text-muted hover:text-gray-900 dark:hover:text-discord-text transition-colors"
          >
            <ArrowLeft size={16} />
            Quay lại Đăng nhập
          </Link>
        </div>

      </div>
    </div>
  );
}
