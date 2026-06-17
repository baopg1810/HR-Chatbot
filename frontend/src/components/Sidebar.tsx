import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, MessageSquareText, BookOpen, Ticket, Settings as SettingsIcon, LogOut, Bot, Shield, FileText, X } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from '../hooks/useAuth';

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  
  const navItems = [
    { name: 'Chatbot AI', path: '/chat', icon: MessageSquareText, roles: ['user', 'admin'] },
    { name: 'Kho tri thức', path: '/knowledge-base', icon: BookOpen, roles: ['user', 'admin'] },
    { name: 'Yêu cầu của tôi', path: '/tickets', icon: Ticket, roles: ['user'] },
    { name: 'Tài nguyên', path: '/resources', icon: FileText, roles: ['user', 'admin'] },
    
    // Admin specific routes
    { name: 'Tổng quan Admin', path: '/admin', icon: LayoutDashboard, roles: ['admin'] },
    { name: 'Quản lý yêu cầu', path: '/admin/tickets', icon: Ticket, roles: ['admin'] },
  ];

  const visibleNavItems = navItems.filter(item => user?.role && item.roles.includes(user.role));

  const handleNavClick = () => {
    if (onClose) onClose();
  };

  return (
    <div className="w-64 h-full bg-brand-gray border-r border-gray-200 flex flex-col pt-6 pb-6 shadow-sm shrink-0 bg-white md:bg-brand-gray relative">
      {onClose && (
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-500 hover:bg-gray-100 rounded-lg md:hidden"
        >
          <X size={20} />
        </button>
      )}
      
      <div className="px-6 mb-10 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-brand-blue flex items-center justify-center text-white shrink-0 shadow-md">
          <Bot size={24} />
        </div>
        <div>
          <h1 className="font-semibold text-[17px] leading-tight text-brand-blue">Supportive AI</h1>
          <p className="text-xs text-brand-blue/70">HR Intelligence</p>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {visibleNavItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={handleNavClick}
              className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-xl text-[15px] font-medium transition-all duration-200",
                isActive 
                  ? "bg-brand-mint text-brand-blue shadow-sm" 
                  : "text-gray-600 hover:bg-gray-100 hover:text-brand-blue"
              )}
            >
              <item.icon size={20} className={cn(isActive ? "text-brand-blue" : "text-gray-500")} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="px-6 mt-6 pt-6 border-t border-gray-200 flex flex-col gap-2">
        <button 
          onClick={() => { navigate('/submit-ticket'); handleNavClick(); }}
          className="w-full bg-brand-blue hover:bg-[#051c5e] text-white py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 mb-4 shadow-md"
        >
          <span className="text-lg leading-none">+</span>
          Tạo yêu cầu mới
        </button>
        
        <button 
          onClick={() => { navigate('/settings'); handleNavClick(); }}
          className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-600 hover:text-brand-blue hover:bg-gray-100 rounded-lg transition-colors w-full text-left"
        >
          <SettingsIcon size={18} />
          Cài đặt
        </button>
        <button 
          onClick={() => { logout(); handleNavClick(); }}
          className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors w-full text-left"
        >
          <LogOut size={18} />
          Đăng xuất
        </button>
      </div>
    </div>
  );
}
