export type Role = 'user' | 'admin';

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  backendRole?: 'employee' | 'department_admin' | 'hr_admin';
  departmentId?: string;
  token: string;
  refreshToken?: string;
}

export interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  attachments?: { name: string; url?: string; data?: Record<string, unknown> | null }[];
  citations?: {
    document_title: string;
    section?: string | null;
    excerpt: string;
    score: number;
  }[];
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: 'In Progress' | 'Action Needed' | 'Resolved';
  dateCreated: string;
}

export interface PolicyCategory {
  id: string;
  title: string;
  description: string;
  icon: string;
  documentCount: number;
}
