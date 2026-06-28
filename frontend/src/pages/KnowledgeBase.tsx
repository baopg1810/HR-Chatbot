import { useEffect, useState } from 'react';
import { BookOpen, FileText, Grid, List, Search, Trash2, TrendingUp, Upload } from 'lucide-react';
import { createTextDocument, deleteDocument, DocumentRecord, listDocuments, listTrendPins, TrendPin, uploadDocument } from '../lib/api';
import { useAuth } from '../hooks/useAuth';

export function KnowledgeBase() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [pins, setPins] = useState<TrendPin[]>([]);
  const [selectedPin, setSelectedPin] = useState<TrendPin | null>(null);
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
  const visiblePins = pins.filter((pin) => pin.title.toLowerCase().includes(query.toLowerCase()));
  const selectedPinSources = selectedPin ? uniqueCitationDocumentTitles(selectedPin.citations) : [];
  const pageTitle = isAdmin ? 'Kho tri thức' : 'Chủ đề phổ biến';
  const pageDescription = isAdmin
    ? 'Tài liệu chính sách được dùng làm nguồn RAG cho HR Helpdesk AI.'
    : 'Các chủ đề HR đang được nhiều nhân viên quan tâm gần đây.';
  const searchPlaceholder = isAdmin ? 'Tìm tài liệu...' : 'Tìm chủ đề...';

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 overflow-x-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 md:mb-10 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-discord-text tracking-tight mb-2">{pageTitle}</h1>
          <p className="text-gray-500 dark:text-discord-text-muted text-sm md:text-[15px]">{pageDescription}</p>
        </div>
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-discord-text-muted" size={20} />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={searchPlaceholder}
            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent focus:ring-1 focus:ring-brand-blue dark:focus:ring-discord-accent transition-all text-gray-800 dark:text-discord-text"
          />
        </div>
      </div>

      {message && (
        <div className="mb-6 rounded-xl border border-[#a6f4df] dark:border-discord-accent/30 bg-[#e0fbf4] dark:bg-discord-accent/10 px-4 py-3 text-sm font-medium text-[#048261] dark:text-discord-accent">
          {message}
        </div>
      )}

      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
          <div className="bg-white dark:bg-discord-sidebar rounded-2xl p-6 border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] transition-colors">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-full bg-[#e0fbf4] dark:bg-discord-accent/20 text-[#048261] dark:text-discord-accent flex items-center justify-center">
                <Upload size={22} />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900 dark:text-discord-text">Upload file chính sách</h2>
                <p className="text-sm text-gray-500 dark:text-discord-text-muted">Hỗ trợ .docx, .md, .txt.</p>
              </div>
            </div>
            <input
              type="file"
              accept=".docx,.md,.txt"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-600 dark:text-discord-text-muted file:mr-4 file:rounded-lg file:border-0 file:bg-brand-blue dark:file:bg-discord-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
            />
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Tên hiển thị tùy chọn"
              className="mt-4 w-full p-3 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-gray-800 dark:text-discord-text transition-colors"
            />
            <button
              onClick={handleUpload}
              disabled={!file}
              className="mt-4 w-full rounded-xl bg-brand-blue dark:bg-discord-accent px-4 py-3 text-sm font-medium text-white hover:bg-[#051c5e] dark:hover:bg-[#4752C4] disabled:opacity-50 transition-colors"
            >
              Lập chỉ mục file upload
            </button>
          </div>

          <div className="bg-white dark:bg-discord-sidebar rounded-2xl p-6 border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] transition-colors">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-full bg-[#e8f2ff] dark:bg-discord-accent/20 text-brand-blue dark:text-discord-accent flex items-center justify-center">
                <FileText size={22} />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900 dark:text-discord-text">Nhập nhanh nội dung</h2>
                <p className="text-sm text-gray-500 dark:text-discord-text-muted">Dùng cho demo hoặc chính sách ngắn.</p>
              </div>
            </div>
            <input
              value={textTitle}
              onChange={(event) => setTextTitle(event.target.value)}
              className="w-full p-3 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent text-gray-800 dark:text-discord-text transition-colors"
            />
            <textarea
              value={textContent}
              onChange={(event) => setTextContent(event.target.value)}
              rows={5}
              placeholder="Nội dung chính sách..."
              className="mt-4 w-full p-3 bg-white dark:bg-discord-card border border-gray-200 dark:border-discord-bg rounded-xl outline-none focus:border-brand-blue dark:focus:border-discord-accent resize-none text-gray-800 dark:text-discord-text placeholder:text-gray-400 dark:placeholder:text-discord-text-muted transition-colors"
            />
            <button
              onClick={handleCreateText}
              disabled={!textTitle.trim() || !textContent.trim()}
              className="mt-4 w-full rounded-xl bg-[#046c4e] dark:bg-emerald-600 px-4 py-3 text-sm font-medium text-white hover:bg-[#03543d] dark:hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              Thêm vào kho tri thức
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-discord-text">{isAdmin ? 'Tài liệu đã lập chỉ mục' : 'Chủ đề đang được quan tâm'}</h2>
        <div className="flex bg-gray-100 dark:bg-discord-card rounded-lg p-1">
          <button className="p-1.5 bg-white dark:bg-discord-sidebar rounded shadow-sm text-gray-800 dark:text-discord-text"><Grid size={18} /></button>
          <button className="p-1.5 text-gray-500 dark:text-discord-text-muted hover:text-gray-800 dark:hover:text-discord-text"><List size={18} /></button>
        </div>
      </div>

      {isAdmin ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {visibleDocuments.map((document) => (
            <div key={document.id} className="bg-white dark:bg-discord-sidebar rounded-2xl p-6 border border-gray-100 dark:border-discord-bg shadow-[0_2px_10px_rgb(0,0,0,0.02)] hover:shadow-md transition-all">
              <div className="flex items-start justify-between gap-3 mb-5">
                <div className="w-12 h-12 rounded-full bg-[#e8f2ff] dark:bg-discord-accent/20 text-brand-blue dark:text-discord-accent flex items-center justify-center">
                  <BookOpen size={24} />
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteDocument(document)}
                  className="w-9 h-9 rounded-lg border border-red-100 dark:border-red-500/20 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 flex items-center justify-center hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors"
                  title="Xóa tài liệu"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-discord-text mb-2 leading-tight">{document.title}</h3>
              <p className="text-gray-500 dark:text-discord-text-muted text-sm mb-4">{document.chunk_count} đoạn - {document.status}</p>
              <p className="text-xs text-gray-400 dark:text-discord-text-muted">Đã tạo: {new Date(document.created_at).toLocaleString()}</p>
            </div>
          ))}
          {visibleDocuments.length === 0 && <p className="text-sm text-gray-500 dark:text-discord-text-muted">Chưa có tài liệu nào.</p>}
        </div>
      ) : (
        <div className="flex flex-wrap gap-3">
          {visiblePins.map((pin) => (
            <button
              key={pin.id}
              onClick={() => setSelectedPin(pin)}
              className="flex items-center gap-2 bg-brand-mint-light dark:bg-discord-accent/10 hover:bg-[#c9f9ec] dark:hover:bg-discord-accent/20 text-[#048261] dark:text-discord-accent px-4 py-2 rounded-full text-sm font-medium transition-colors border border-[#a6f4df] dark:border-discord-accent/30"
            >
              <TrendingUp size={16} />
              {pin.title} ({pin.source_query_count})
            </button>
          ))}
          {visiblePins.length === 0 && <p className="text-sm text-gray-500 dark:text-discord-text-muted">Chưa có chủ đề nổi bật nào.</p>}
          {selectedPin && (
            <div className="basis-full mt-3 rounded-xl border border-[#a6f4df] dark:border-discord-accent/30 bg-white dark:bg-discord-sidebar p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#048261] dark:text-discord-accent">Chủ đề nổi bật</p>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-discord-text">{selectedPin.title}</h3>
                </div>
                <span className="rounded-full bg-brand-mint-light dark:bg-discord-accent/10 px-3 py-1 text-xs font-semibold text-[#048261] dark:text-discord-accent">
                  {selectedPin.source_query_count} câu hỏi
                </span>
              </div>
              <p className="text-sm leading-6 text-gray-700 dark:text-discord-text">{selectedPin.summary}</p>
              {selectedPinSources.length > 0 && (
                <div className="mt-4 border-t border-gray-100 dark:border-discord-bg pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-discord-text-muted mb-2">Nguồn tham khảo</p>
                  <div className="space-y-2">
                    {selectedPinSources.map((sourceTitle) => (
                      <div key={sourceTitle} className="rounded-lg bg-gray-50 dark:bg-discord-bg p-3">
                        <p className="text-sm font-semibold text-gray-800 dark:text-discord-text">{sourceTitle}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function uniqueCitationDocumentTitles(citations: TrendPin['citations']) {
  return [...new Set(citations.map((citation) => citation.document_title).filter(Boolean))];
}
