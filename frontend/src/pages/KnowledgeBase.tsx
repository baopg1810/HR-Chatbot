import { useEffect, useState } from 'react';
import { BookOpen, FileText, Grid, List, Search, Trash2, TrendingUp, Upload } from 'lucide-react';
import { createTextDocument, deleteDocument, DocumentRecord, listDocuments, listTrendPins, TrendPin, uploadDocument } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

export function KnowledgeBase() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [pins, setPins] = useState<TrendPin[]>([]);
  const [query, setQuery] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [textTitle, setTextTitle] = useState('Chính sách mới');
  const [textContent, setTextContent] = useState('');
  const [message, setMessage] = useState('');
  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    if (!user) return;
    refresh();
  }, [user]);

  const refresh = async () => {
    if (!user) return;
    setMessage('');
    try {
      const [nextPins, nextDocuments] = await Promise.all([
        listTrendPins(user.token).catch(() => []),
        isAdmin ? listDocuments(user.token).catch(() => []) : Promise.resolve([]),
      ]);
      setPins(nextPins);
      setDocuments(nextDocuments);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể tải kho tri thức.');
    }
  };

  const handleUpload = async () => {
    if (!user || !file) return;
    try {
      await uploadDocument(user.token, file, title);
      setMessage(`Đã lập chỉ mục file ${file.name}.`);
      setFile(null);
      setTitle('');
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload thất bại.');
    }
  };

  const handleCreateText = async () => {
    if (!user || !textTitle.trim() || !textContent.trim()) return;
    try {
      await createTextDocument(user.token, {
        title: textTitle,
        content: textContent,
        visibility_roles: ['employee', 'department_admin', 'hr_admin'],
        department_ids: [],
      });
      setMessage(`Đã lập chỉ mục tài liệu ${textTitle}.`);
      setTextContent('');
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể tạo tài liệu.');
    }
  };

  const handleDeleteDocument = async (document: DocumentRecord) => {
    if (!user) return;
    const confirmed = window.confirm(`Xóa tài liệu "${document.title}" khỏi kho tri thức?`);
    if (!confirmed) return;

    try {
      await deleteDocument(user.token, document.id);
      setMessage(`Đã xóa tài liệu ${document.title}.`);
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể xóa tài liệu.');
    }
  };

  const visibleDocuments = documents.filter((document) => document.title.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 md:mb-10 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 tracking-tight mb-2">Kho tri thức</h1>
          <p className="text-gray-500 text-sm md:text-[15px]">Tài liệu chính sách được dùng làm nguồn RAG cho HR Helpdesk AI.</p>
        </div>
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm tài liệu..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
          />
        </div>
      </div>

      {message && (
        <div className="mb-6 rounded-xl border border-[#a6f4df] bg-[#e0fbf4] px-4 py-3 text-sm font-medium text-[#048261]">
          {message}
        </div>
      )}

      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)]">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-full bg-[#e0fbf4] text-[#048261] flex items-center justify-center">
                <Upload size={22} />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900">Upload file chính sách</h2>
                <p className="text-sm text-gray-500">Hỗ trợ .docx, .md, .txt.</p>
              </div>
            </div>
            <input
              type="file"
              accept=".docx,.md,.txt"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-600 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-blue file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
            />
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Tên hiển thị tùy chọn"
              className="mt-4 w-full p-3 bg-white border border-gray-200 rounded-xl outline-none focus:border-brand-blue"
            />
            <button
              onClick={handleUpload}
              disabled={!file}
              className="mt-4 w-full rounded-xl bg-brand-blue px-4 py-3 text-sm font-medium text-white hover:bg-[#051c5e] disabled:opacity-50"
            >
              Lập chỉ mục file upload
            </button>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)]">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-full bg-[#e8f2ff] text-brand-blue flex items-center justify-center">
                <FileText size={22} />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900">Nhập nhanh nội dung</h2>
                <p className="text-sm text-gray-500">Dùng cho demo hoặc chính sách ngắn.</p>
              </div>
            </div>
            <input
              value={textTitle}
              onChange={(event) => setTextTitle(event.target.value)}
              className="w-full p-3 bg-white border border-gray-200 rounded-xl outline-none focus:border-brand-blue"
            />
            <textarea
              value={textContent}
              onChange={(event) => setTextContent(event.target.value)}
              rows={5}
              placeholder="Nội dung chính sách..."
              className="mt-4 w-full p-3 bg-white border border-gray-200 rounded-xl outline-none focus:border-brand-blue resize-none"
            />
            <button
              onClick={handleCreateText}
              disabled={!textTitle.trim() || !textContent.trim()}
              className="mt-4 w-full rounded-xl bg-[#046c4e] px-4 py-3 text-sm font-medium text-white hover:bg-[#03543d] disabled:opacity-50"
            >
              Thêm vào kho tri thức
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{isAdmin ? 'Tài liệu đã lập chỉ mục' : 'Chủ đề đang được hỏi nhiều'}</h2>
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button className="p-1.5 bg-white rounded shadow-sm text-gray-800"><Grid size={18} /></button>
          <button className="p-1.5 text-gray-500 hover:text-gray-800"><List size={18} /></button>
        </div>
      </div>

      {isAdmin ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {visibleDocuments.map((document) => (
            <div key={document.id} className="bg-white rounded-2xl p-6 border border-gray-100 shadow-[0_2px_10px_rgb(0,0,0,0.02)] hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3 mb-5">
                <div className="w-12 h-12 rounded-full bg-[#e8f2ff] text-brand-blue flex items-center justify-center">
                  <BookOpen size={24} />
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteDocument(document)}
                  className="w-9 h-9 rounded-lg border border-red-100 bg-red-50 text-red-600 flex items-center justify-center hover:bg-red-100 transition-colors"
                  title="Xóa tài liệu"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 leading-tight">{document.title}</h3>
              <p className="text-gray-500 text-sm mb-4">{document.chunk_count} đoạn - {document.status}</p>
              <p className="text-xs text-gray-400">Đã tạo: {new Date(document.created_at).toLocaleString()}</p>
            </div>
          ))}
          {visibleDocuments.length === 0 && <p className="text-sm text-gray-500">Chưa có tài liệu nào.</p>}
        </div>
      ) : (
        <div className="flex flex-wrap gap-3">
          {pins.map((pin) => (
            <button key={pin.id} className="flex items-center gap-2 bg-brand-mint-light hover:bg-[#c9f9ec] text-[#048261] px-4 py-2 rounded-full text-sm font-medium transition-colors border border-[#a6f4df]">
              <TrendingUp size={16} />
              {pin.title} ({pin.source_query_count})
            </button>
          ))}
          {pins.length === 0 && <p className="text-sm text-gray-500">Chưa có chủ đề trending. Hãy hỏi chatbot vài câu về cùng chủ đề.</p>}
        </div>
      )}
    </div>
  );
}
