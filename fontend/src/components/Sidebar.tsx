import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, MessageSquareText, BookOpen, Ticket, Settings as SettingsIcon, LogOut, Bot, Shield, FileText, X } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from '../hooks/useAuth';

export function Sidebar({ onClose, onDesktopToggle, isCollapsed = false }: { onClose?: () => void, onDesktopToggle?: () => void, isCollapsed?: boolean }) {
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
    <div className={cn(
      "h-full border-r border-gray-200 dark:border-discord-bg flex flex-col pt-6 pb-6 shadow-sm shrink-0 bg-white dark:bg-discord-sidebar relative transition-all duration-300",
      isCollapsed ? "w-20" : "w-64"
    )}>
      {onClose && (
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-500 hover:bg-gray-100 rounded-lg md:hidden"
        >
          <X size={20} />
        </button>
      )}
      <div className={cn("mb-10 flex items-center gap-3", isCollapsed ? "justify-center px-0" : "px-6")}>
        <button 
          onClick={() => { if (onDesktopToggle) onDesktopToggle(); }}
          className="w-10 h-10 rounded-full bg-brand-blue flex items-center justify-center text-white shrink-0 shadow-md hover:opacity-90 transition-opacity cursor-pointer md:cursor-pointer"
          title={isCollapsed ? "Mở rộng Sidebar" : "Thu gọn Sidebar"}
        >
          <Bot size={24} />
        </button>
        {!isCollapsed && (
          <div className="overflow-hidden">
            <h1 className="font-semibold text-[17px] leading-tight text-brand-blue dark:text-discord-text whitespace-nowrap">Supportive AI</h1>
            <p className="text-xs text-brand-blue/70 dark:text-discord-text-muted whitespace-nowrap">HR Intelligence</p>
          </div>
        )}
      </div>

      <nav className={cn("flex-1 space-y-1 overflow-y-auto overflow-x-hidden", isCollapsed ? "px-2" : "px-3")}>
        {visibleNavItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={handleNavClick}
              className={cn(
                "flex items-center gap-3 rounded-xl transition-all duration-200",
                isCollapsed ? "justify-center py-3 px-0 mx-auto w-12" : "px-3 py-3 w-full",
                isActive 
                  ? "bg-brand-mint dark:bg-discord-accent text-brand-blue dark:text-white shadow-sm" 
                  : "text-gray-600 dark:text-discord-text-muted hover:bg-gray-100 dark:hover:bg-discord-card dark:hover:text-discord-text hover:text-brand-blue"
              )}
              title={isCollapsed ? item.name : undefined}
            >
              <item.icon size={20} className={cn("shrink-0", isActive ? "text-brand-blue dark:text-white" : "text-gray-500 dark:text-discord-text-muted")} />
              {!isCollapsed && <span className="text-[15px] font-medium truncate">{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <div className={cn("mt-6 pt-6 border-t border-gray-200 dark:border-discord-bg flex flex-col gap-2 transition-all duration-300", isCollapsed ? "px-2 items-center" : "px-6")}>
        <button 
          onClick={() => { navigate('/submit-ticket'); handleNavClick(); }}
          className={cn("bg-brand-blue dark:bg-discord-accent hover:bg-[#051c5e] dark:hover:bg-[#4752C4] text-white py-2.5 transition-all duration-200 flex items-center justify-center mb-4 shadow-md", isCollapsed ? "w-10 h-10 rounded-full mx-auto" : "w-full gap-2 rounded-lg text-sm font-medium")}
          title={isCollapsed ? "Tạo yêu cầu mới" : undefined}
        >
          <span className="text-lg leading-none shrink-0">+</span>
          {!isCollapsed && <span className="truncate">Tạo yêu cầu mới</span>}
        </button>
        
        <button 
          onClick={() => { navigate('/settings'); handleNavClick(); }}
          className={cn("flex items-center gap-3 py-2 text-gray-600 dark:text-discord-text-muted hover:text-brand-blue dark:hover:text-discord-text hover:bg-gray-100 dark:hover:bg-discord-card transition-all duration-200 text-left", isCollapsed ? "justify-center px-0 w-12 rounded-xl mx-auto" : "px-3 w-full rounded-lg text-sm font-medium")}
          title={isCollapsed ? "Cài đặt" : undefined}
        >
          <SettingsIcon size={18} className="shrink-0" />
          {!isCollapsed && <span className="truncate">Cài đặt</span>}
        </button>
        <button 
          onClick={() => { logout(); handleNavClick(); }}
          className={cn("flex items-center gap-3 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all duration-200 text-left", isCollapsed ? "justify-center px-0 w-12 rounded-xl mx-auto" : "px-3 w-full rounded-lg text-sm font-medium")}
          title={isCollapsed ? "Đăng xuất" : undefined}
        >
          <LogOut size={18} className="shrink-0" />
          {!isCollapsed && <span className="truncate">Đăng xuất</span>}
        </button>
      </div>
    </div>
  );
}
