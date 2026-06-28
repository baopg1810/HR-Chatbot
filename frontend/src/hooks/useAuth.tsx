import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User } from '../types';
import { loginRequest, logoutRequest, mapLoginUser } from '../lib/api';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('hr-helpdesk-user');
    if (stored) {
      setUser(JSON.parse(stored));
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await loginRequest(email, password);
    const nextUser = mapLoginUser(response);
    localStorage.setItem('hr-helpdesk-user', JSON.stringify(nextUser));
    setUser(nextUser);
  };

  const logout = async () => {
    const refreshToken = user?.refreshToken;
    if (refreshToken) {
      try {
        await logoutRequest(refreshToken);
      } catch {
        // Local logout should still succeed if the session already expired server-side.
      }
    }
    localStorage.removeItem('hr-helpdesk-user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
