import { ReactNode, useState } from 'react';
import { Sidebar } from './Sidebar';
import { Menu, Bot } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from '../hooks/useAuth';

export function Layout({ children }: { children: ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDesktopSidebarOpen, setIsDesktopSidebarOpen] = useState(true);
  const { user } = useAuth();

  return (
    <div className="flex w-full h-[100dvh] overflow-hidden bg-[#fafbfc] dark:bg-discord-bg relative transition-colors duration-300">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/40 z-20 md:hidden transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar - sliding on mobile, fixed on desktop */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-30 transform transition-all duration-300 ease-in-out md:relative h-full shrink-0 overflow-hidden",
        isSidebarOpen ? "translate-x-0 w-64" : "-translate-x-full w-0 md:translate-x-0",
        isDesktopSidebarOpen ? "md:w-64" : "md:w-20"
      )}>
         <div className="w-full h-full">
            <Sidebar 
               isCollapsed={!isDesktopSidebarOpen}
               onClose={() => setIsSidebarOpen(false)} 
               onDesktopToggle={() => setIsDesktopSidebarOpen(!isDesktopSidebarOpen)} 
            />
         </div>
      </div>

      <main className="flex-1 h-full flex flex-col w-full overflow-hidden relative">
        {/* Mobile Header */}
        <div className="md:hidden flex items-center justify-between p-4 bg-white dark:bg-discord-sidebar border-b border-gray-200 dark:border-discord-bg shrink-0 z-10 w-full transition-colors">
           <div className="flex items-center gap-3">
             <button 
               onClick={() => setIsSidebarOpen(true)}
               className="w-10 h-10 rounded-full bg-brand-blue flex items-center justify-center text-white shrink-0 shadow-md hover:opacity-90 transition-opacity"
             >
               <Bot size={24} />
             </button>
             <h1 className="font-semibold text-[17px] leading-tight text-brand-blue">Supportive AI</h1>
           </div>
        </div>
        


        {/* Page Content */}
        <div className="flex-1 overflow-x-hidden overflow-y-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
