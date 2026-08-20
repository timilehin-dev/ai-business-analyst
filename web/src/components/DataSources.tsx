import { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Database, RefreshCw, Trash2, ExternalLink, CheckCircle2, XCircle } from 'lucide-react';
import Nav from './Nav';

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

  useEffect(() => { load(); }, [load]);

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
    <div className="min-h-screen bg-gray-50">
      <Nav />
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
            <p className="text-gray-500">
              Your knowledge graph — files, Google Drive, Sheets, and Gmail. {totalDocs} documents ingested.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}
        {message && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">{message}</div>
        )}

        {/* ===== Connectors ===== */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Local files */}
          <div className="border rounded-lg bg-white shadow-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <Upload className="h-6 w-6 text-indigo-600" />
              <div>
                <h2 className="font-semibold text-lg">File Upload</h2>
                <p className="text-sm text-gray-500">CSV, DOCX, PDF, TXT, JSON</p>
              </div>
            </div>
            <label className="flex items-center justify-center gap-2 border-2 border-dashed border-gray-300 rounded-lg p-6 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors">
              <input
                type="file"
                className="hidden"
                accept=".csv,.tsv,.docx,.pdf,.txt,.md,.json"
                onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0])}
              />
              <FileText className="h-5 w-5 text-gray-400" />
              <span className="text-sm text-gray-600">
                {loading ? 'Uploading...' : 'Click to upload a file'}
              </span>
            </label>
            {local && (
              <p className="text-xs text-gray-400 mt-3">
                {local.document_count} documents ingested
              </p>
            )}
          </div>

          {/* Google Workspace */}
          <div className="border rounded-lg bg-white shadow-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <Database className="h-6 w-6 text-indigo-600" />
              <div>
                <h2 className="font-semibold text-lg">Google Workspace</h2>
                <p className="text-sm text-gray-500">Drive, Sheets & Gmail (read-only)</p>
              </div>
              {google?.configured ? (
                <CheckCircle2 className="h-5 w-5 text-green-500 ml-auto" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-300 ml-auto" />
              )}
            </div>

            {google?.configured ? (
              <div className="space-y-3">
                <button
                  onClick={() => syncConnector('google')}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Sync Now
                </button>
                <p className="text-xs text-gray-500">
                  {google.document_count} documents · Last sync: {google.last_sync_at ? new Date(google.last_sync_at).toLocaleString() : 'never'}
                  {google.last_error && <span className="text-red-500 block mt-1">Last error: {google.last_error}</span>}
                </p>
                <p className="text-xs text-gray-400">
                  Continuous sync runs automatically every 6 hours while the app is running.
                </p>
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
                      className="w-full p-2 border border-gray-300 rounded-md text-sm"
                    />
                    <input
                      type="password"
                      placeholder="Client Secret"
                      value={googleClientSecret}
                      onChange={(e) => setGoogleClientSecret(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md text-sm"
                    />
                    <button
                      onClick={saveGoogleCreds}
                      className="w-full bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 text-sm"
                    >
                      Save Credentials
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setShowGoogleSetup(true)}
                    className="w-full border border-indigo-300 text-indigo-700 px-4 py-2 rounded-lg hover:bg-indigo-50 text-sm"
                  >
                    Configure Google Cloud OAuth
                  </button>
                )}
                <button
                  onClick={connectGoogle}
                  className="w-full bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  disabled={!google?.has_credentials}
                >
                  Connect Google Workspace
                </button>
                <p className="text-xs text-gray-400">
                  Setup: Google Cloud project → enable Drive/Sheets/Gmail APIs → OAuth client (Web) →
                  redirect URI <code className="bg-gray-100 px-1 rounded">http://localhost:3001/api/connectors/google/callback</code>
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ===== Documents ===== */}
        <div className="border rounded-lg bg-white shadow-sm">
          <div className="p-6 pb-3 flex items-center justify-between">
            <h2 className="text-xl font-semibold">Ingested Documents</h2>
            <span className="text-sm text-gray-500">{totalDocs} total</span>
          </div>
          <div className="divide-y">
            {documents.length === 0 && (
              <p className="p-6 text-gray-500 text-sm">
                No documents yet. Upload a file or connect Google Workspace to start building your knowledge graph.
              </p>
            )}
            {documents.map((doc) => (
              <div key={doc.id} className="p-4 flex items-start justify-between gap-4 hover:bg-gray-50">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <span className="font-medium truncate">{doc.title}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 flex-shrink-0">
                      {doc.source}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">{doc.content.slice(0, 200)}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {doc.updated_at ? new Date(doc.updated_at).toLocaleString() : ''}
                    {doc.metadata?.url && (
                      <a href={doc.metadata.url} target="_blank" rel="noreferrer" className="ml-2 inline-flex items-center gap-1 text-indigo-600 hover:underline">
                        Open source <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => deleteDocument(doc.id)}
                  className="text-gray-400 hover:text-red-500 flex-shrink-0"
                  title="Delete document"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}