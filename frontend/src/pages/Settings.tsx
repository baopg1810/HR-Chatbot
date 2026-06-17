import React from 'react';
import { User, Bell, Shield, Globe, MonitorSmartphone } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export function Settings() {
  const { user } = useAuth();

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="mb-6 md:mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 tracking-tight mb-2">Cài đặt</h1>
        <p className="text-gray-500 text-sm md:text-[15px]">Quản lý thông tin cá nhân và tùy chọn hệ thống.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 md:gap-8">
        {/* Settings Navigation */}
        <div className="md:col-span-1 flex flex-row overflow-x-auto md:flex-col space-x-2 md:space-x-0 md:space-y-1 pb-2 md:pb-0 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
           <button className="w-full flex items-center justify-center md:justify-start gap-3 px-4 md:px-3 py-2.5 text-sm font-medium rounded-xl bg-brand-mint text-brand-blue transition-colors whitespace-nowrap">
              <User size={18} />
              Tài khoản
           </button>
           <button className="w-full flex items-center justify-center md:justify-start gap-3 px-4 md:px-3 py-2.5 text-sm font-medium rounded-xl text-gray-600 hover:bg-gray-100 transition-colors whitespace-nowrap">
              <Bell size={18} />
              Thông báo
           </button>
           <button className="w-full flex items-center justify-center md:justify-start gap-3 px-4 md:px-3 py-2.5 text-sm font-medium rounded-xl text-gray-600 hover:bg-gray-100 transition-colors whitespace-nowrap">
              <Shield size={18} />
              Bảo mật
           </button>
           <button className="w-full flex items-center justify-center md:justify-start gap-3 px-4 md:px-3 py-2.5 text-sm font-medium rounded-xl text-gray-600 hover:bg-gray-100 transition-colors whitespace-nowrap">
              <MonitorSmartphone size={18} />
              Giao diện
           </button>
        </div>

        {/* Settings Content */}
        <div className="md:col-span-3 space-y-6">
           <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 md:p-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Thông tin cá nhân</h2>
              
              <div className="flex items-center gap-6 mb-8">
                 <div className="w-20 h-20 rounded-full bg-brand-blue text-white flex items-center justify-center text-2xl font-bold">
                    {user?.name.charAt(0).toUpperCase() || 'U'}
                 </div>
                 <div>
                    <button className="bg-white border border-gray-200 text-sm font-medium text-gray-700 px-4 py-2 rounded-xl shadow-sm hover:bg-gray-50 mb-2">Thay đổi ảnh đại diện</button>
                    <p className="text-xs text-gray-500">JPG, GIF hoặc PNG. Dung lượng tối đa 1MB.</p>
                 </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                 <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Họ và tên</label>
                    <input type="text" defaultValue={user?.name || ''} className="w-full p-3 border border-gray-200 rounded-xl outline-none focus:border-brand-blue text-[15px] bg-gray-50" readOnly />
                 </div>
                 <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Email liên hệ</label>
                    <input type="email" defaultValue={user?.email || ''} className="w-full p-3 border border-gray-200 rounded-xl outline-none focus:border-brand-blue text-[15px] bg-gray-50" readOnly />
                 </div>
              </div>

              <div>
                 <label className="block text-sm font-medium text-gray-700 mb-1.5">Vai trò hệ thống</label>
                 <div className="w-full p-3 border border-gray-200 rounded-xl outline-none text-[15px] bg-gray-50 text-gray-500 font-medium font-mono">
                    {user?.role === 'admin' ? 'Quản trị viên' : 'Nhân viên'}
                 </div>
              </div>
           </div>

           <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-5 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
               <div>
                 <h3 className="text-[15px] font-semibold text-gray-900 mb-1">Ngôn ngữ</h3>
                 <p className="text-sm text-gray-500">Thay đổi ngôn ngữ hiển thị của hệ thống.</p>
               </div>
               <select className="bg-white border border-gray-200 rounded-xl px-4 py-2 text-sm font-medium text-gray-700 outline-none focus:border-brand-blue w-full md:w-auto">
                  <option value="vi">Tiếng Việt</option>
                  <option value="en">Tiếng Anh</option>
               </select>
           </div>
           
           <div className="flex justify-end pt-4">
              <button className="bg-brand-blue text-white font-medium text-sm px-6 py-2.5 rounded-xl hover:bg-[#051c5e] transition-colors shadow-sm">
                 Lưu thay đổi
              </button>
           </div>
        </div>
      </div>
    </div>
  );
}
