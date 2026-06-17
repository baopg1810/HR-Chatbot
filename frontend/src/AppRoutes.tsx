import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Chat } from './pages/Chat';
import { KnowledgeBase } from './pages/KnowledgeBase';
import { MyTickets } from './pages/MyTickets';
import { AdminDashboard } from './pages/AdminDashboard';
import { ManageTickets } from './pages/ManageTickets';
import { SubmitTicket } from './pages/SubmitTicket';
import { Settings } from './pages/Settings';
import { ForgotPassword } from './pages/ForgotPassword';

import { Resources } from './pages/Resources';

export function AppRoutes() {
  const { user } = useAuth();

  if (!user) {
    return (
      <Routes>
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/knowledge-base" element={<KnowledgeBase />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/submit-ticket" element={<SubmitTicket />} />
        <Route path="/settings" element={<Settings />} />
        
        {/* User only routes */}
        {user.role === 'user' && (
          <Route path="/tickets" element={<MyTickets />} />
        )}
        
        {/* Admin only routes */}
        {user.role === 'admin' && (
          <>
             <Route path="/admin" element={<AdminDashboard />} />
             <Route path="/admin/tickets" element={<ManageTickets />} />
          </>
        )}
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
