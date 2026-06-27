import React, { useState } from 'react';
import { User, Bell, Shield, MonitorSmartphone } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { Moon, Sun, Monitor, Palette } from 'lucide-react';
import { cn } from '../lib/utils';

type SettingsTab = 'account' | 'notifications' | 'security' | 'appearance';

export function Settings() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<SettingsTab>('account');

  const tabs = [
    { id: 'account' as SettingsTab, label: 'Tài khoản', icon: User },
    { id: 'notifications' as SettingsTab, label: 'Thông báo', icon: Bell },
    { id: 'security' as SettingsTab, label: 'Bảo mật', icon: Shield },
    { id: 'appearance' as SettingsTab, label: 'Giao diện', icon: MonitorSmartphone },
  ];

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="mb-6 md:mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-discord-text tracking-tight mb-2">Cài đặt</h1>
        <p className="text-gray-500 dark:text-discord-text-muted text-sm md:text-[15px]">Quản lý thông tin cá nhân và tùy chọn hệ thống.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 md:gap-8">
        {/* Settings Navigation */}
        <div className="md:col-span-1 flex flex-row overflow-x-auto md:flex-col space-x-2 md:space-x-0 md:space-y-1 pb-2 md:pb-0 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
           {tabs.map((tab) => (
             <button
               key={tab.id}
               onClick={() => setActiveTab(tab.id)}
               className={cn(
                 "w-full flex items-center justify-center md:justify-start gap-3 px-4 md:px-3 py-2.5 text-sm font-medium rounded-xl transition-colors whitespace-nowrap",
                 activeTab === tab.id
                   ? "bg-brand-mint dark:bg-discord-accent text-brand-blue dark:text-white"
                   : "text-gray-600 dark:text-discord-text-muted hover:bg-gray-100 dark:hover:bg-discord-card"
               )}
             >
               <tab.icon size={18} />
               {tab.label}
             </button>
           ))}
        </div>

        {/* Settings Content */}
        <div className="md:col-span-3 space-y-6">

           {/* === TAB: TÀI KHOẢN === */}
           {activeTab === 'account' && (
             <>
               <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 md:p-8 transition-colors">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-discord-text mb-6">Thông tin cá nhân</h2>
                  
                  <div className="flex items-center gap-6 mb-8">
                     <div className="w-20 h-20 rounded-full bg-brand-blue dark:bg-discord-accent text-white flex items-center justify-center text-2xl font-bold">
                        {user?.name.charAt(0).toUpperCase() || 'U'}
                     </div>
                     <div>
                        <button className="bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg text-sm font-medium text-gray-700 dark:text-discord-text px-4 py-2 rounded-xl shadow-sm hover:bg-gray-50 dark:hover:bg-discord-card-hover mb-2 transition-colors">Thay đổi ảnh đại diện</button>
                        <p className="text-xs text-gray-500 dark:text-discord-text-muted">JPG, GIF hoặc PNG. Dung lượng tối đa 1MB.</p>
                     </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                     <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted mb-1.5">Họ và tên</label>
                        <input type="text" defaultValue={user?.name || ''} className="w-full p-3 border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-[15px] bg-gray-50 dark:bg-discord-card dark:text-discord-text transition-colors" readOnly />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted mb-1.5">Email liên hệ</label>
                        <input type="email" defaultValue={user?.email || ''} className="w-full p-3 border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-[15px] bg-gray-50 dark:bg-discord-card dark:text-discord-text transition-colors" readOnly />
                     </div>
                  </div>

                  <div>
                     <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted mb-1.5">Vai trò hệ thống</label>
                     <div className="w-full p-3 border border-gray-200 dark:border-discord-bg rounded-xl outline-none text-[15px] bg-gray-50 dark:bg-discord-card text-gray-500 dark:text-discord-text-muted font-medium font-mono transition-colors">
                        {user?.role === 'admin' ? 'Quản trị viên' : 'Nhân viên'}
                     </div>
                  </div>
               </div>

               <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-5 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-colors">
                   <div>
                     <h3 className="text-[15px] font-semibold text-gray-900 dark:text-discord-text mb-1">Ngôn ngữ</h3>
                     <p className="text-sm text-gray-500 dark:text-discord-text-muted">Thay đổi ngôn ngữ hiển thị của hệ thống.</p>
                   </div>
                   <select className="bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl px-4 py-2 text-sm font-medium text-gray-700 dark:text-discord-text outline-none focus:border-brand-blue dark:focus:border-discord-accent w-full md:w-auto transition-colors">
                      <option value="vi">Tiếng Việt</option>
                      <option value="en">Tiếng Anh</option>
                   </select>
               </div>

               <div className="flex justify-end pt-4">
                  <button className="bg-brand-blue dark:bg-discord-accent text-white font-medium text-sm px-6 py-2.5 rounded-xl hover:bg-[#051c5e] dark:hover:bg-[#4752C4] transition-colors shadow-sm">
                     Lưu thay đổi
                  </button>
               </div>
             </>
           )}

           {/* === TAB: THÔNG BÁO === */}
           {activeTab === 'notifications' && (
             <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 md:p-8 transition-colors">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-discord-text mb-6">Thông báo</h2>
                <div className="space-y-5">
                  {[
                    { label: 'Thông báo email khi có ticket mới', desc: 'Nhận email khi có yêu cầu mới được tạo.' },
                    { label: 'Thông báo khi ticket được cập nhật', desc: 'Nhận thông báo khi trạng thái ticket thay đổi.' },
                    { label: 'Bản tin hàng tuần', desc: 'Nhận tóm tắt hoạt động HR hàng tuần.' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-discord-bg last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-discord-text">{item.label}</p>
                        <p className="text-xs text-gray-500 dark:text-discord-text-muted mt-0.5">{item.desc}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked={i < 2} className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 dark:bg-discord-card peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-blue dark:peer-checked:bg-discord-accent"></div>
                      </label>
                    </div>
                  ))}
                </div>
             </div>
           )}

           {/* === TAB: BẢO MẬT === */}
           {activeTab === 'security' && (
             <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 md:p-8 transition-colors">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-discord-text mb-6">Bảo mật</h2>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted mb-1.5">Mật khẩu hiện tại</label>
                    <input type="password" placeholder="••••••••" className="w-full p-3 border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-[15px] bg-gray-50 dark:bg-discord-card dark:text-discord-text placeholder:text-gray-300 dark:placeholder:text-discord-text-muted transition-colors" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted mb-1.5">Mật khẩu mới</label>
                    <input type="password" placeholder="••••••••" className="w-full p-3 border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-[15px] bg-gray-50 dark:bg-discord-card dark:text-discord-text placeholder:text-gray-300 dark:placeholder:text-discord-text-muted transition-colors" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-discord-text-muted mb-1.5">Xác nhận mật khẩu mới</label>
                    <input type="password" placeholder="••••••••" className="w-full p-3 border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-[15px] bg-gray-50 dark:bg-discord-card dark:text-discord-text placeholder:text-gray-300 dark:placeholder:text-discord-text-muted transition-colors" />
                  </div>
                  <div className="flex justify-end pt-2">
                    <button className="bg-brand-blue dark:bg-discord-accent text-white font-medium text-sm px-6 py-2.5 rounded-xl hover:bg-[#051c5e] dark:hover:bg-[#4752C4] transition-colors shadow-sm">
                      Đổi mật khẩu
                    </button>
                  </div>
                </div>
             </div>
           )}

           {/* === TAB: GIAO DIỆN === */}
           {activeTab === 'appearance' && (
             <div className="space-y-6">
               <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6 md:p-8 transition-colors">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-discord-accent/20 text-brand-blue dark:text-discord-accent flex items-center justify-center">
                      <Palette size={20} />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900 dark:text-discord-text">Chế độ giao diện</h2>
                      <p className="text-sm text-gray-500 dark:text-discord-text-muted">Chọn chế độ hiển thị phù hợp với mắt của bạn.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Light Mode Card */}
                    <button
                      onClick={() => setTheme('light')}
                      className={cn(
                        "relative flex flex-col items-center p-6 rounded-2xl border-2 transition-all group",
                        theme === 'light'
                          ? "border-brand-blue dark:border-discord-accent bg-brand-blue/5 dark:bg-discord-accent/10 shadow-md ring-1 ring-brand-blue/20 dark:ring-discord-accent/20"
                          : "border-gray-200 dark:border-discord-bg hover:border-gray-300 dark:hover:border-discord-text-muted/30 hover:shadow-sm"
                      )}
                    >
                      {theme === 'light' && (
                        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-brand-blue dark:bg-discord-accent text-white flex items-center justify-center">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                      )}
                      {/* Mini Preview - Light */}
                      <div className="w-full max-w-[160px] aspect-[4/3] bg-[#f8f9fa] rounded-xl border border-gray-200 mb-4 overflow-hidden p-2 flex gap-1.5">
                        <div className="w-1/4 bg-white rounded-lg border border-gray-100 flex flex-col gap-1 p-1.5">
                          <div className="h-1.5 w-full bg-brand-blue rounded-full"></div>
                          <div className="h-1 w-3/4 bg-gray-200 rounded-full"></div>
                          <div className="h-1 w-full bg-gray-200 rounded-full"></div>
                          <div className="h-1 w-2/3 bg-gray-200 rounded-full"></div>
                        </div>
                        <div className="flex-1 bg-white rounded-lg border border-gray-100 p-1.5 flex flex-col gap-1">
                          <div className="h-1.5 w-1/2 bg-gray-900 rounded-full"></div>
                          <div className="h-1 w-full bg-gray-100 rounded-full"></div>
                          <div className="h-1 w-3/4 bg-gray-100 rounded-full"></div>
                          <div className="flex-1"></div>
                          <div className="h-3 w-full bg-gray-50 rounded border border-gray-200"></div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Sun size={18} className={cn(theme === 'light' ? "text-brand-blue dark:text-discord-accent" : "text-gray-400 dark:text-discord-text-muted")} />
                        <span className={cn("text-sm font-semibold", theme === 'light' ? "text-brand-blue dark:text-discord-accent" : "text-gray-600 dark:text-discord-text-muted")}>
                          Chế độ Sáng
                        </span>
                      </div>
                    </button>

                    {/* Dark Mode Card */}
                    <button
                      onClick={() => setTheme('dark')}
                      className={cn(
                        "relative flex flex-col items-center p-6 rounded-2xl border-2 transition-all group",
                        theme === 'dark'
                          ? "border-discord-accent bg-discord-accent/10 shadow-md ring-1 ring-discord-accent/20"
                          : "border-gray-200 dark:border-discord-bg hover:border-gray-300 dark:hover:border-discord-text-muted/30 hover:shadow-sm"
                      )}
                    >
                      {theme === 'dark' && (
                        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-discord-accent text-white flex items-center justify-center">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                      )}
                      {/* Mini Preview - Dark */}
                      <div className="w-full max-w-[160px] aspect-[4/3] bg-[#1e1f22] rounded-xl border border-[#313338] mb-4 overflow-hidden p-2 flex gap-1.5">
                        <div className="w-1/4 bg-[#2b2d31] rounded-lg flex flex-col gap-1 p-1.5">
                          <div className="h-1.5 w-full bg-[#5865F2] rounded-full"></div>
                          <div className="h-1 w-3/4 bg-[#3f4147] rounded-full"></div>
                          <div className="h-1 w-full bg-[#3f4147] rounded-full"></div>
                          <div className="h-1 w-2/3 bg-[#3f4147] rounded-full"></div>
                        </div>
                        <div className="flex-1 bg-[#313338] rounded-lg p-1.5 flex flex-col gap-1">
                          <div className="h-1.5 w-1/2 bg-[#dbdee1] rounded-full"></div>
                          <div className="h-1 w-full bg-[#3f4147] rounded-full"></div>
                          <div className="h-1 w-3/4 bg-[#3f4147] rounded-full"></div>
                          <div className="flex-1"></div>
                          <div className="h-3 w-full bg-[#1e1f22] rounded border border-[#3f4147]"></div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Moon size={18} className={cn(theme === 'dark' ? "text-discord-accent" : "text-gray-400 dark:text-discord-text-muted")} />
                        <span className={cn("text-sm font-semibold", theme === 'dark' ? "text-discord-accent" : "text-gray-600 dark:text-discord-text-muted")}>
                          Chế độ Tối
                        </span>
                      </div>
                    </button>
                  </div>
               </div>

               <div className="bg-white dark:bg-discord-sidebar rounded-2xl border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-5 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-colors">
                   <div>
                     <h3 className="text-[15px] font-semibold text-gray-900 dark:text-discord-text mb-1">Đồng bộ với hệ thống</h3>
                     <p className="text-sm text-gray-500 dark:text-discord-text-muted">Tự động chuyển đổi theo cài đặt giao diện của máy tính.</p>
                   </div>
                   <label className="relative inline-flex items-center cursor-pointer shrink-0">
                     <input type="checkbox" className="sr-only peer" />
                     <div className="w-11 h-6 bg-gray-200 dark:bg-discord-card peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-blue dark:peer-checked:bg-discord-accent"></div>
                   </label>
               </div>
             </div>
           )}

        </div>
      </div>
    </div>
  );
}
