import React from 'react';
import { Users, Ticket, CheckCircle2, Clock, Activity, TrendingUp } from 'lucide-react';

export function AdminDashboard() {
  return (
    <div className="w-full max-w-6xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 md:mb-8 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 tracking-tight mb-2">Tổng quan HR</h1>
          <p className="text-gray-500 text-sm md:text-[15px]">Theo dõi hiệu suất xử lý yêu cầu và trạng thái hệ thống hỗ trợ.</p>
        </div>
        <button className="bg-white border w-fit border-gray-200 shadow-sm text-gray-700 px-4 py-2 rounded-xl text-sm font-medium hover:bg-gray-50">
          Xuất báo cáo
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)]">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Ticket size={20} />
            </div>
            <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full flex items-center gap-1">
              <TrendingUp size={12} /> +12%
            </span>
          </div>
          <p className="text-sm font-medium text-gray-500 mb-1">Tổng yêu cầu (Tháng)</p>
          <p className="text-2xl font-bold text-gray-900">1,284</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)]">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
              <Activity size={20} />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-500 mb-1">Cần phản hồi gấp</p>
          <p className="text-2xl font-bold text-gray-900">24</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)]">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Clock size={20} />
            </div>
            <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full flex items-center gap-1">
              <TrendingUp size={12} /> Nhanh hơn 5h
            </span>
          </div>
          <p className="text-sm font-medium text-gray-500 mb-1">Th/gian phản hồi TB</p>
          <p className="text-2xl font-bold text-gray-900">2.4<span className="text-base font-normal text-gray-500">h</span></p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)]">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 size={20} />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-500 mb-1">Đã giải quyết (Tuần)</p>
          <p className="text-2xl font-bold text-gray-900">156</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
         <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Trạng thái khối lượng công việc</h3>
            <div className="space-y-5">
               <div>
                  <div className="flex justify-between text-sm mb-2">
                     <span className="font-medium text-gray-700">Tư vấn chính sách</span>
                     <span className="text-gray-500">45%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                     <div className="bg-brand-blue h-2 rounded-full" style={{ width: '45%' }}></div>
                  </div>
               </div>
               <div>
                  <div className="flex justify-between text-sm mb-2">
                     <span className="font-medium text-gray-700">Thủ tục hành chính</span>
                     <span className="text-gray-500">30%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                     <div className="bg-[#66f0cb] h-2 rounded-full" style={{ width: '30%' }}></div>
                  </div>
               </div>
               <div>
                  <div className="flex justify-between text-sm mb-2">
                     <span className="font-medium text-gray-700">Trợ cấp & Phúc lợi</span>
                     <span className="text-gray-500">25%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                     <div className="bg-indigo-400 h-2 rounded-full" style={{ width: '25%' }}></div>
                  </div>
               </div>
            </div>
         </div>

         <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)] p-6">
            <div className="flex items-center justify-between mb-6">
               <h3 className="text-lg font-semibold text-gray-900">Hoạt động gần đây</h3>
               <button className="text-sm font-medium text-brand-blue hover:underline">Xem tất cả</button>
            </div>
            <div className="space-y-4">
               {[
                 { action: 'Cập nhật tài liệu', subject: 'Chính sách nghỉ phép 2024', time: '10 phút trước', user: 'Admin' },
                 { action: 'Đóng ticket', subject: '#TK-0038 - Cấp màn hình', time: '2 giờ trước', user: 'Hoài Thương' },
                 { action: 'Phân quyền mới', subject: 'Lê Văn A - Trưởng nhóm', time: 'Hôm qua', user: 'Admin' },
               ].map((act, i) => (
                 <div key={i} className="flex items-start gap-4 p-3 rounded-xl hover:bg-gray-50 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 shrink-0 mt-0.5">
                       <Users size={14} />
                    </div>
                    <div>
                       <p className="text-[14px] font-medium text-gray-900">{act.action}: <span className="font-normal text-gray-600">{act.subject}</span></p>
                       <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-400">{act.time}</span>
                          <span className="text-[10px] text-gray-300">•</span>
                          <span className="text-xs font-medium text-brand-blue">{act.user}</span>
                       </div>
                    </div>
                 </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
}
