import React, { useState } from 'react';
import { Search, Download, FileText, Folder, File, ArrowRight } from 'lucide-react';
import { cn } from '../lib/utils';

const CATEGORIES = ['Tất cả', 'Biểu mẫu Nhân sự', 'Chính sách Công ty', 'Tài liệu Đào tạo', 'Khác'];

const MOCK_RESOURCES = [
  { id: 1, title: 'Đơn xin nghỉ thai sản r3.pdf', type: 'PDF', category: 'Biểu mẫu Nhân sự', size: '245 KB', date: '10/10/2023' },
  { id: 2, title: 'Hướng dẫn đánh giá hiệu suất 2023.docx', type: 'DOCX', category: 'Tài liệu Đào tạo', size: '1.2 MB', date: '05/11/2023' },
  { id: 3, title: 'Mẫu đăng ký tài sản IT mới.xlsx', type: 'XLSX', category: 'Biểu mẫu Nhân sự', size: '120 KB', date: '01/09/2023' },
  { id: 4, title: 'Sổ tay văn hóa doanh nghiệp.pdf', type: 'PDF', category: 'Chính sách Công ty', size: '4.5 MB', date: '15/01/2023' },
  { id: 5, title: 'Chính sách WFH cập nhật.pdf', type: 'PDF', category: 'Chính sách Công ty', size: '890 KB', date: '20/08/2023' },
];

export function Resources() {
  const [activeCategory, setActiveCategory] = useState('Tất cả');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredResources = MOCK_RESOURCES.filter(res => {
    const matchesSearch = res.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = activeCategory === 'Tất cả' || res.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="w-full max-w-6xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 md:mb-10 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 tracking-tight mb-2">Tài nguyên & Biểu mẫu</h1>
          <p className="text-gray-500 text-sm md:text-[15px]">Tải xuống các tài liệu, mẫu đơn và biểu mẫu cần thiết.</p>
        </div>
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input 
            type="text" 
            placeholder="Tìm kiếm tài liệu..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 md:py-3 bg-white border border-gray-200 rounded-xl outline-none focus:border-brand-blue shadow-sm transition-all focus:ring-2 focus:ring-brand-blue/10"
          />
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-4 mb-6 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        {CATEGORIES.map(category => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={cn(
              "px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors border",
              activeCategory === category
                ? "bg-brand-blue text-white border-brand-blue shadow-sm"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300"
            )}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
         {filteredResources.map(resource => (
           <div key={resource.id} className="bg-white border border-gray-100 rounded-2xl p-5 hover:border-brand-blue/30 transition-all hover:shadow-md group flex flex-col h-full">
             <div className="flex items-start gap-4 mb-4">
               <div className="w-12 h-12 rounded-xl bg-indigo-50 text-brand-blue flex items-center justify-center shrink-0">
                 {resource.type === 'PDF' ? <FileText size={24} /> : <File size={24} />}
               </div>
               <div className="flex-1 min-w-0">
                 <h3 className="font-semibold text-gray-900 truncate mb-1" title={resource.title}>{resource.title}</h3>
                 <p className="text-xs font-medium text-brand-blue bg-[#e8f2ff] px-2 py-0.5 rounded w-fit">{resource.category}</p>
               </div>
             </div>
             
             <div className="mt-auto flex items-center justify-between pt-4 border-t border-gray-50">
                <div className="flex flex-col">
                  <span className="text-[11px] text-gray-400 font-medium uppercase tracking-wider">{resource.type} • {resource.size}</span>
                  <span className="text-xs text-gray-500 mt-0.5">Đã tải lên: {resource.date}</span>
                </div>
                <button className="w-8 h-8 rounded-full bg-gray-50 text-gray-600 flex items-center justify-center group-hover:bg-brand-blue group-hover:text-white transition-colors stretch-0 shrink-0">
                  <Download size={16} />
                </button>
             </div>
           </div>
         ))}
      </div>
      
      {filteredResources.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Folder size={32} className="text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">Không tìm thấy tài liệu</h3>
          <p className="text-gray-500">Hãy thử điều chỉnh từ khóa tìm kiếm hoặc danh mục.</p>
        </div>
      )}
    </div>
  );
}
