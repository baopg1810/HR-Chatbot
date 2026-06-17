import { ReactNode, useState } from 'react';
import { Sidebar } from './Sidebar';
import { Menu } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from '../hooks/useAuth';

export function Layout({ children }: { children: ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="flex w-full h-[100dvh] overflow-hidden bg-[#fafbfc] relative">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/40 z-20 md:hidden transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar - sliding on mobile, fixed on desktop */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-30 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 h-full",
        isSidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
         <Sidebar onClose={() => setIsSidebarOpen(false)} />
      </div>

      <main className="flex-1 h-full flex flex-col w-full overflow-hidden relative">
        {/* Mobile Header */}
        <div className="md:hidden flex items-center justify-between p-4 bg-white border-b border-gray-200 shrink-0 z-10 w-full">
           <div className="flex items-center gap-3">
             <button 
               onClick={() => setIsSidebarOpen(true)}
               className="p-1.5 text-gray-600 rounded-lg hover:bg-gray-100"
             >
               <Menu size={24} />
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
