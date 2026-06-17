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
    <div className="min-h-screen w-full bg-[#f8f9fa] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-10 border border-gray-100">
        
        {!isSubmitted ? (
          <>
            <div className="flex flex-col items-center mb-8 text-center">
              <div className="w-14 h-14 rounded-full bg-indigo-50 flex items-center justify-center text-brand-blue mb-5 shadow-sm">
                <KeyRound size={28} />
              </div>
              <h1 className="text-2xl font-semibold text-gray-900 mb-2">Quên mật khẩu?</h1>
              <p className="text-sm text-gray-500">
                Đừng lo lắng, hãy nhập địa chỉ email của bạn và chúng tôi sẽ gửi liên kết để đặt lại mật khẩu.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700">Địa chỉ Email</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <Mail size={18} className="text-gray-400" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="nhanvien@congty.com"
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl focus:ring-brand-blue focus:border-brand-blue sm:text-sm transition-shadow outline-none placeholder:text-gray-300 text-gray-700"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-brand-blue hover:bg-[#051c5e] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue transition-colors"
              >
                Gửi liên kết đặt lại
              </button>
            </form>
          </>
        ) : (
          <div className="flex flex-col items-center text-center py-4">
            <div className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-500 mb-6 shadow-sm">
              <CheckCircle2 size={32} />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Đã gửi liên kết!</h1>
            <p className="text-[15px] text-gray-500 mb-8 leading-relaxed">
              Chúng tôi đã gửi một email có chứa hướng dẫn đặt lại mật khẩu đến <br/>
              <span className="font-medium text-gray-900">{email}</span>
            </p>
            <button
              onClick={() => setIsSubmitted(false)}
              className="text-sm font-medium text-brand-blue hover:text-[#051c5e] hover:underline"
            >
              Gửi lại email
            </button>
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-gray-100 flex justify-center">
          <Link 
            to="/" 
            className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft size={16} />
            Quay lại Đăng nhập
          </Link>
        </div>

      </div>
    </div>
  );
}
