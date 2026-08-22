import { useState, useEffect } from 'react';
import {
  Brain,
  Database,
  ToggleRight,
  Shield,
  RefreshCw,
  Save,
  CheckCircle2,
  AlertTriangle,
  Globe,
  Server,
  Cpu,
  FileText,
  Key,
} from 'lucide-react';
import AppShell from './AppShell';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface SettingsData {
  organization: { name: string };
  ai_provider: {
    provider: string;
    base_url: string | null;
    has_api_key: boolean;
    models: Record<string, string>;
  };
  database: { url_set: boolean };
  features: {
    newsroom: boolean;
    code_sandbox: boolean;
    air_gap: boolean;
    proactive_monitoring: boolean;
  };
  briefing: { hour: number; timezone: string };
}

/* ------------------------------------------------------------------ */
/*  Settings Page                                                       */
/* ------------------------------------------------------------------ */
export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  // Editable state
  const [orgName, setOrgName] = useState('');
  const [provider, setProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [features, setFeatures] = useState({
    newsroom: true,
    code_sandbox: true,
    air_gap: false,
    proactive_monitoring: true,
  });
  const [briefingHour, setBriefingHour] = useState(6);
  const [briefingTimezone, setBriefingTimezone] = useState('UTC');

  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((data: SettingsData) => {
        setSettings(data);
        setOrgName(data.organization.name);
        setProvider(data.ai_provider.provider);
        setBaseUrl(data.ai_provider.base_url || '');
        setFeatures(data.features);
        setBriefingHour(data.briefing.hour);
        setBriefingTimezone(data.briefing.timezone);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const saveAll = async () => {
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      // Save general (organization + briefing schedule)
      await fetch('/api/settings/general', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_name: orgName,
          briefing_hour: briefingHour,
          briefing_timezone: briefingTimezone,
        }),
      });

      // Save AI provider
      const aiBody: any = { provider };
      if (baseUrl) aiBody.base_url = baseUrl;
      if (apiKey) aiBody.api_key = apiKey;
      await fetch('/api/settings/ai-provider', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(aiBody),
      });

      // Save features
      await fetch('/api/settings/features', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(features),
      });

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center py-32 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading settings…
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Settings</h1>
          <p className="text-sm text-slate-500 mt-1">Manage your AI provider, data sources, and preferences.</p>
        </div>
        <button
          onClick={saveAll}
          disabled={saving}
          className="inline-flex items-center gap-2 bg-brand-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl shadow-sm hover:bg-brand-700 transition-colors disabled:opacity-50"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving…' : saved ? 'Saved!' : 'Save All'}
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
      )}

      <div className="space-y-6">
        {/* ---- Organization ---- */}
        <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center">
              <Globe className="w-4 h-4 text-brand-600" />
            </div>
            <h2 className="text-[15px] font-semibold text-slate-900">Organization</h2>
          </div>
          <div className="px-6 py-5">
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Organization Name</label>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full max-w-md px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              placeholder="My Organization"
            />
          </div>
        </section>

        {/* ---- AI Provider ---- */}
        <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center">
              <Brain className="w-4 h-4 text-violet-600" />
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-slate-900">AI Provider</h2>
              <p className="text-[11px] text-slate-400">Current: {settings?.ai_provider.provider || 'ollama-local'}</p>
            </div>
          </div>
          <div className="px-6 py-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full max-w-md px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="ollama-local">Ollama (Local)</option>
                <option value="ollama-cloud">Ollama Cloud</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full max-w-md px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="https://ollama.com/v1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                API Key {settings?.ai_provider.has_api_key && <span className="text-emerald-600 text-xs">(configured)</span>}
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full max-w-md px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder={settings?.ai_provider.has_api_key ? '••••••••' : 'Enter API key'}
              />
            </div>
            {Object.keys(settings?.ai_provider.models || {}).length > 0 && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Configured Models</label>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(settings!.ai_provider.models).map(([role, model]) => (
                    <span key={role} className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
                      {role}: {model}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ---- Database ---- */}
        <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
              <Database className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-slate-900">Database Connection</h2>
              <p className="text-[11px] text-slate-400">
                {settings?.database.url_set ? 'Connected' : 'Not configured'}
              </p>
            </div>
          </div>
          <div className="px-6 py-5">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${settings?.database.url_set ? 'bg-emerald-500' : 'bg-slate-300'}`} />
              <span className="text-sm text-slate-700">
                {settings?.database.url_set
                  ? 'Database is connected. Data flows to the dashboard and Sense loop.'
                  : 'No database connected. Run the setup wizard to connect your data source.'}
              </span>
            </div>
          </div>
        </section>

        {/* ---- Features ---- */}
        <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
              <ToggleRight className="w-4 h-4 text-amber-600" />
            </div>
            <h2 className="text-[15px] font-semibold text-slate-900">Features</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {/* Newsroom */}
            <div className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-sm font-medium text-slate-900">Newsroom</span>
                  <p className="text-[11px] text-slate-400">Real-time market intelligence and news monitoring</p>
                </div>
              </div>
              <button
                onClick={() => setFeatures({ ...features, newsroom: !features.newsroom })}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  features.newsroom ? 'bg-brand-500' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    features.newsroom ? 'translate-x-5' : ''
                  }`}
                />
              </button>
            </div>
            {/* Code Sandbox */}
            <div className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Server className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-sm font-medium text-slate-900">Code Sandbox</span>
                  <p className="text-[11px] text-slate-400">Restricted Python environment for deterministic analysis</p>
                </div>
              </div>
              <button
                onClick={() => setFeatures({ ...features, code_sandbox: !features.code_sandbox })}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  features.code_sandbox ? 'bg-brand-500' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    features.code_sandbox ? 'translate-x-5' : ''
                  }`}
                />
              </button>
            </div>
            {/* Air Gap */}
            <div className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-sm font-medium text-slate-900">Air Gap Mode</span>
                  <p className="text-[11px] text-slate-400">Disable all external connections — data never leaves your network</p>
                </div>
              </div>
              <button
                onClick={() => setFeatures({ ...features, air_gap: !features.air_gap })}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  features.air_gap ? 'bg-brand-500' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    features.air_gap ? 'translate-x-5' : ''
                  }`}
                />
              </button>
            </div>
            {/* Proactive Monitoring */}
            <div className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RefreshCw className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-sm font-medium text-slate-900">Proactive Monitoring</span>
                  <p className="text-[11px] text-slate-400">Nightly anomaly scan, morning briefing, and periodic data sync</p>
                </div>
              </div>
              <button
                onClick={() => setFeatures({ ...features, proactive_monitoring: !features.proactive_monitoring })}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  features.proactive_monitoring ? 'bg-brand-500' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    features.proactive_monitoring ? 'translate-x-5' : ''
                  }`}
                />
              </button>
            </div>
          </div>
        </section>

        {/* ---- Briefing Schedule ---- */}
        <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-indigo-600" />
            </div>
            <h2 className="text-[15px] font-semibold text-slate-900">Briefing Schedule</h2>
          </div>
          <div className="px-6 py-5 grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Hour (24h, UTC-relative)
              </label>
              <input
                type="number"
                min={0}
                max={23}
                value={briefingHour}
                onChange={(e) => setBriefingHour(Number(e.target.value))}
                className="w-full max-w-[5rem] px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Time Zone</label>
              <input
                type="text"
                value={briefingTimezone}
                onChange={(e) => setBriefingTimezone(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="UTC"
              />
            </div>
            <p className="text-[11px] text-slate-400 sm:col-span-2">
              The Sense loop runs a nightly anomaly scan and writes the next morning’s briefing.
              Schedule changes apply on the next server restart.
            </p>
          </div>
        </section>

        {/* ---- Danger Zone ---- */}
        <section className="bg-white border border-red-200 rounded-2xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-red-100 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <h2 className="text-[15px] font-semibold text-red-900">Danger Zone</h2>
          </div>
          <div className="px-6 py-5">
            <p className="text-sm text-slate-600 mb-4">
              Reset all configuration and run the setup wizard again. This does not delete your data.
            </p>
            <button
              onClick={async () => {
                if (!confirm('Reset all settings? You will need to run the setup wizard again.')) return;
                await fetch('/api/setup/reset', { method: 'POST' });
                window.location.href = '/setup';
              }}
              className="text-sm font-medium text-red-600 hover:text-red-700 underline underline-offset-2"
            >
              Reset Configuration
            </button>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
