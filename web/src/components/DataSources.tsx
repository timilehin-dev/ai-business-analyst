import { useState, useEffect, useCallback } from 'react';
import {
  Upload,
  FileText,
  Database,
  RefreshCw,
  Trash2,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Cloud,
  HardDrive,
  FileUp,
  Clock,
} from 'lucide-react';
import AppShell from './AppShell';

interface Connector {
  id: string;
  name: string;
  description: string;
  icon: string;
  configured: boolean;
  has_credentials: boolean;
  document_count: number;
  last_sync_at: string | null;
  last_error: string | null;
}

interface Document {
  id: number;
  source: string;
  title: string;
  content: string;
  metadata: Record<string, any>;
  updated_at: string | null;
}

export default function DataSources() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [googleClientId, setGoogleClientId] = useState('');
  const [googleClientSecret, setGoogleClientSecret] = useState('');
  const [showGoogleSetup, setShowGoogleSetup] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cRes, dRes] = await Promise.all([
        fetch('/api/connectors'),
        fetch('/api/connectors/documents?limit=50'),
      ]);
      const cData = await cRes.json();
      const dData = await dRes.json();
      setConnectors(cData.connectors || []);
      setDocuments(dData.documents || []);
      setTotalDocs(dData.total || 0);
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const uploadFile = async (file: File) => {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('/api/connectors/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setMessage(`Ingested "${file.name}"`);
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const syncConnector = async (id: string) => {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const res = await fetch(`/api/connectors/${id}/sync`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Sync failed');
      setMessage(data.message || `Synced ${data.synced} items`);
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const connectGoogle = async () => {
    setError('');
    try {
      const res = await fetch('/api/connectors/google/auth');
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start Google auth');
      window.open(data.auth_url, '_blank');
    } catch (err: any) {
      setError(err.message);
    }
  };

  const saveGoogleCreds = async () => {
    setError('');
    setMessage('');
    try {
      const res = await fetch('/api/connectors/google/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: googleClientId, client_secret: googleClientSecret }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save credentials');
      setMessage('Google credentials saved. Now click "Connect Google Workspace".');
      setShowGoogleSetup(false);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const deleteDocument = async (id: number) => {
    try {
      await fetch(`/api/connectors/documents/${id}`, { method: 'DELETE' });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const google = connectors.find((c) => c.id === 'google');
  const local = connectors.find((c) => c.id === 'local');

  return (
    <AppShell>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Data Sources</h1>
        <p className="text-sm text-slate-500 mt-1">
          Your knowledge graph — files, Google Drive, Sheets, and Gmail.{' '}
          <span className="font-medium text-slate-700">{totalDocs} documents</span> ingested.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
      )}
      {message && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-sm">
          {message}
        </div>
      )}

      {/* Connectors */}
      <div className="grid gap-5 md:grid-cols-2 mb-8">
        {/* Local files */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">File Upload</h2>
              <p className="text-xs text-slate-500">CSV · DOCX · PDF · TXT · JSON</p>
            </div>
            <span className="ml-auto text-[11px] font-medium text-slate-500 bg-slate-100 rounded-full px-2.5 py-1">
              {local?.document_count ?? 0} docs
            </span>
          </div>

          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const file = e.dataTransfer.files?.[0];
              if (file) uploadFile(file);
            }}
            className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors ${
              dragOver
                ? 'border-brand-400 bg-brand-50'
                : 'border-slate-200 hover:border-brand-300 hover:bg-slate-50'
            }`}
          >
            <input
              type="file"
              className="hidden"
              accept=".csv,.tsv,.docx,.pdf,.txt,.md,.json"
              onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0])}
            />
            <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm">
              <FileUp className="w-5 h-5 text-brand-600" />
            </div>
            <span className="text-sm font-medium text-slate-700">
              {loading ? 'Uploading…' : 'Drop a file or click to browse'}
            </span>
            <span className="text-xs text-slate-400">Parsed into your knowledge graph automatically</span>
          </label>
        </div>

        {/* Google Workspace */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
              <Cloud className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">Google Workspace</h2>
              <p className="text-xs text-slate-500">Drive · Sheets · Gmail (read-only)</p>
            </div>
            {google?.configured ? (
              <span className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 rounded-full px-2.5 py-1">
                <CheckCircle2 className="w-3 h-3" /> Connected
              </span>
            ) : (
              <span className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 bg-slate-100 rounded-full px-2.5 py-1">
                <XCircle className="w-3 h-3" /> Not connected
              </span>
            )}
          </div>

          {google?.configured ? (
            <div className="space-y-3">
              <button
                onClick={() => syncConnector('google')}
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 bg-brand-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Sync Now
              </button>
              <div className="text-xs text-slate-500 space-y-1">
                <p>
                  {google.document_count} documents · Last sync:{' '}
                  {google.last_sync_at ? new Date(google.last_sync_at).toLocaleString() : 'never'}
                </p>
                {google.last_error && <p className="text-red-500">Last error: {google.last_error}</p>}
                <p className="text-slate-400 flex items-center gap-1.5">
                  <Clock className="w-3 h-3" /> Continuous sync runs every 6 hours while the app is running.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {showGoogleSetup ? (
                <>
                  <input
                    type="text"
                    placeholder="Google Cloud OAuth Client ID"
                    value={googleClientId}
                    onChange={(e) => setGoogleClientId(e.target.value)}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
                  />
                  <input
                    type="password"
                    placeholder="Client Secret"
                    value={googleClientSecret}
                    onChange={(e) => setGoogleClientSecret(e.target.value)}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
                  />
                  <button
                    onClick={saveGoogleCreds}
                    className="w-full bg-brand-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl hover:bg-brand-700 transition-colors"
                  >
                    Save Credentials
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setShowGoogleSetup(true)}
                  className="w-full border border-brand-200 text-brand-700 text-sm font-medium px-4 py-2.5 rounded-xl hover:bg-brand-50 transition-colors"
                >
                  Configure Google Cloud OAuth
                </button>
              )}
              <button
                onClick={connectGoogle}
                disabled={!google?.has_credentials}
                className="w-full bg-brand-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Connect Google Workspace
              </button>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Setup: Google Cloud project → enable Drive/Sheets/Gmail APIs → OAuth client (Web) →
                redirect URI{' '}
                <code className="bg-slate-100 px-1 rounded text-[10px]">
                  http://localhost:3001/api/connectors/google/callback
                </code>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Documents */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
              <FileText className="w-4 h-4 text-slate-500" />
            </div>
            <h2 className="text-[15px] font-semibold text-slate-900">Ingested Documents</h2>
          </div>
          <span className="text-xs font-medium text-slate-500 bg-slate-100 rounded-full px-2.5 py-1">
            {totalDocs} total
          </span>
        </div>

        {documents.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
              <Database className="w-6 h-6 text-slate-400" />
            </div>
            <p className="text-sm text-slate-500">
              No documents yet. Upload a file or connect Google Workspace to start building your
              knowledge graph.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {documents.map((doc) => (
              <div key={doc.id} className="px-6 py-4 flex items-start justify-between gap-4 hover:bg-slate-50/60 transition-colors">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-slate-900 truncate">{doc.title}</span>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-brand-700 bg-brand-50 rounded-full px-2 py-0.5 flex-shrink-0">
                      {doc.source}
                    </span>
                  </div>
                  <p className="text-[13px] text-slate-500 mt-1 line-clamp-2">{doc.content.slice(0, 200)}</p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {doc.updated_at ? new Date(doc.updated_at).toLocaleString() : ''}
                    {doc.metadata?.url && (
                      <a
                        href={doc.metadata.url}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-2 inline-flex items-center gap-1 text-brand-600 hover:underline"
                      >
                        Open source <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => deleteDocument(doc.id)}
                  className="text-slate-300 hover:text-red-500 transition-colors flex-shrink-0"
                  title="Delete document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}