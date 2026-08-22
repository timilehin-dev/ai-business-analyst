import { useState, useRef } from 'react';
import { CheckCircle2, Loader2, Database, Brain, Sparkles, ArrowLeft, ArrowRight, Upload, FileText, Globe } from 'lucide-react';

interface SetupWizardProps {
  onComplete: () => void;
}

const steps = [
  { n: 1, label: 'Connect data' },
  { n: 2, label: 'Choose AI' },
  { n: 3, label: 'Data sources' },
  { n: 4, label: 'Enable features' },
];

export default function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [config, setConfig] = useState({
    dbType: 'sqlite',
    dbHost: '',
    dbPort: '',
    dbName: '',
    dbUser: '',
    dbPassword: '',
    aiProvider: 'ollama-local',
    apiKey: '',
    baseUrl: '',
    modelReasoning: '',
    modelSql: '',
    newsroomEnabled: true,
    codeSandboxEnabled: true,
    airGapMode: false,
    proactiveMonitoring: true,
    sampleData: true,
  });

  // FastAPI validation errors return detail as an array of objects —
  // stringify them into a readable message instead of "[object Object]".
  const apiError = (data: any, fallback: string): string => {
    const detail = data?.detail;
    if (Array.isArray(detail)) {
      return detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ');
    }
    return detail || fallback;
  };

  const dbPayload = () => ({
    type: config.dbType,
    host: config.dbHost || null,
    port: config.dbPort ? Number(config.dbPort) : null,
    database: config.dbName || null,
    username: config.dbUser || null,
    password: config.dbPassword || null,
  });

  const testConnection = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/setup/test-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dbPayload()),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(apiError(data, 'Connection failed'));
      }

      setStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveConfiguration = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/setup/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_name: 'My Organization',
          database: {
            ...dbPayload(),
            sample_data: config.sampleData,
          },
          ai: {
            provider: config.aiProvider,
            api_key: config.apiKey,
            base_url: config.baseUrl,
            models: {
              reasoning: config.modelReasoning,
              sql: config.modelSql,
            },
          },
          features: {
            newsroom: config.newsroomEnabled,
            code_sandbox: config.codeSandboxEnabled,
            air_gap: config.airGapMode,
            proactive_monitoring: config.proactiveMonitoring,
          },
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(apiError(data, 'Setup failed'));
      }

      onComplete();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (step === 1) {
      testConnection();
    } else if (step === 2) {
      setStep(3);
    } else if (step === 3) {
      setStep(4);
    } else if (step === 4) {
      saveConfiguration();
    }
  };

  const inputCls =
    'w-full px-3.5 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition-shadow bg-white';
  const labelCls = 'block text-[13px] font-medium text-slate-700 mb-1.5';

  const Toggle = ({
    checked,
    onChange,
    disabled,
  }: {
    checked: boolean;
    onChange: (v: boolean) => void;
    disabled?: boolean;
  }) => (
    <label className={`relative inline-flex items-center cursor-pointer ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="sr-only peer"
      />
      <div className="w-11 h-6 bg-slate-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
    </label>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-brand-50/40 to-slate-100 p-4">
      <div className="w-full max-w-xl">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-600/25">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="text-lg font-bold text-slate-900 tracking-tight">AI Business Analyst</div>
            <div className="text-xs text-slate-500">Setup in 4 simple steps</div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
          {/* Step indicator */}
          <div className="px-8 pt-6 pb-5 border-b border-slate-100">
            <div className="flex items-center">
              {steps.map((s, i) => (
                <div key={s.n} className={`flex items-center ${i > 0 ? 'flex-1' : ''}`}>
                  {i > 0 && (
                    <div className={`flex-1 h-0.5 mx-3 rounded-full ${step > s.n - 1 ? 'bg-brand-500' : 'bg-slate-200'}`} />
                  )}
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                        step === s.n
                          ? 'bg-brand-600 text-white'
                          : step > s.n
                          ? 'bg-brand-100 text-brand-700'
                          : 'bg-slate-100 text-slate-400'
                      }`}
                    >
                      {step > s.n ? <CheckCircle2 className="w-4 h-4" /> : s.n}
                    </div>
                    <span
                      className={`text-xs font-medium hidden sm:block ${
                        step === s.n ? 'text-slate-900' : 'text-slate-400'
                      }`}
                    >
                      {s.label}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-8">
            {error && (
              <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-700 text-[13px]">
                {error}
              </div>
            )}

            {/* Step 1: Database */}
            {step === 1 && (
              <div className="space-y-5">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center">
                    <Database className="w-4 h-4 text-brand-600" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">Connect Your Data</h3>
                </div>

                <div>
                  <label className={labelCls}>Database Type</label>
                  <select
                    value={config.dbType}
                    onChange={(e) => setConfig({ ...config, dbType: e.target.value })}
                    className={inputCls}
                  >
                    <option value="sqlite">SQLite (Recommended for getting started)</option>
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                    <option value="csv">CSV Files (Upload later)</option>
                  </select>
                </div>

                {config.dbType !== 'sqlite' && config.dbType !== 'csv' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelCls}>Host</label>
                      <input
                        type="text"
                        placeholder="localhost"
                        value={config.dbHost}
                        onChange={(e) => setConfig({ ...config, dbHost: e.target.value })}
                        className={inputCls}
                      />
                    </div>
                    <div>
                      <label className={labelCls}>Port</label>
                      <input
                        type="text"
                        placeholder="5432"
                        value={config.dbPort}
                        onChange={(e) => setConfig({ ...config, dbPort: e.target.value })}
                        className={inputCls}
                      />
                    </div>
                    <div className="col-span-2">
                      <label className={labelCls}>Database Name</label>
                      <input
                        type="text"
                        placeholder="my_database"
                        value={config.dbName}
                        onChange={(e) => setConfig({ ...config, dbName: e.target.value })}
                        className={inputCls}
                      />
                    </div>
                    <div>
                      <label className={labelCls}>Username</label>
                      <input
                        type="text"
                        placeholder="username"
                        value={config.dbUser}
                        onChange={(e) => setConfig({ ...config, dbUser: e.target.value })}
                        className={inputCls}
                      />
                    </div>
                    <div>
                      <label className={labelCls}>Password</label>
                      <input
                        type="password"
                        placeholder="password"
                        value={config.dbPassword}
                        onChange={(e) => setConfig({ ...config, dbPassword: e.target.value })}
                        className={inputCls}
                      />
                    </div>
                  </div>
                )}

                {config.dbType === 'sqlite' && (
                  <div className="space-y-3">
                    <div className="p-4 bg-brand-50/60 border border-brand-100 rounded-xl text-[13px] text-brand-900 leading-relaxed">
                      SQLite will be created automatically. Perfect for testing and small teams.
                      You can migrate to PostgreSQL later.
                    </div>
                    <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                      <div>
                        <label className="text-sm font-medium text-slate-900">Load Sample Data</label>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Seed demo tables (customers, products, orders) so you can ask questions
                          immediately — no setup needed.
                        </p>
                      </div>
                      <Toggle
                        checked={config.sampleData}
                        onChange={(v) => setConfig({ ...config, sampleData: v })}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: AI */}
            {step === 2 && (
              <div className="space-y-5">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center">
                    <Brain className="w-4 h-4 text-brand-600" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">Choose Your AI Brain</h3>
                </div>

                <div>
                  <label className={labelCls}>AI Provider</label>
                  <select
                    value={config.aiProvider}
                    onChange={(e) => setConfig({ ...config, aiProvider: e.target.value })}
                    className={inputCls}
                  >
                    <option value="ollama-local">Ollama (Local, Free, Private) - Recommended</option>
                    <option value="ollama-cloud">Ollama Cloud</option>
                    <option value="openai">OpenAI (GPT-4)</option>
                    <option value="anthropic">Anthropic (Claude)</option>
                    <option value="custom">Custom OpenAI-Compatible API</option>
                  </select>
                </div>

                {config.aiProvider !== 'ollama-local' && (
                  <div>
                    <label className={labelCls}>API Key</label>
                    <input
                      type="password"
                      placeholder="sk-..."
                      value={config.apiKey}
                      onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                      className={inputCls}
                    />
                    <p className="text-xs text-slate-400 mt-1.5">
                      Your API key is encrypted and stored locally. Never sent to our servers.
                    </p>
                  </div>
                )}

                {config.aiProvider === 'ollama-local' && (
                  <div className="p-4 bg-emerald-50/60 border border-emerald-100 rounded-xl text-[13px] text-emerald-900 flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                    <div>
                      Ollama will run on your machine. Make sure you have it installed:
                      <code className="bg-white px-2 py-1 rounded-md border border-emerald-200 block mt-2 font-mono text-xs">
                        curl -fsSL https://ollama.com/install.sh | sh
                      </code>
                    </div>
                  </div>
                )}

                {(config.aiProvider === 'ollama-local' ||
                  config.aiProvider === 'ollama-cloud' ||
                  config.aiProvider === 'custom') && (
                  <div>
                    <label className={labelCls}>
                      Base URL
                      {config.aiProvider === 'ollama-local' && (
                        <span className="text-slate-400 font-normal">
                          {' '}
                          (use http://host.docker.internal:11434 when running in Docker)
                        </span>
                      )}
                      {config.aiProvider === 'ollama-cloud' && (
                        <span className="text-slate-400 font-normal"> (https://ollama.com)</span>
                      )}
                    </label>
                    <input
                      type="text"
                      placeholder={
                        config.aiProvider === 'ollama-local'
                          ? 'http://localhost:11434'
                          : config.aiProvider === 'ollama-cloud'
                          ? 'https://ollama.com'
                          : 'https://your-endpoint.example.com/v1'
                      }
                      value={config.baseUrl}
                      onChange={(e) => setConfig({ ...config, baseUrl: e.target.value })}
                      className={inputCls}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Data Sources */}
            {step === 3 && (
              <div className="space-y-5">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                    <Upload className="w-4 h-4 text-emerald-600" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">Connect Your Data</h3>
                </div>

                <p className="text-sm text-slate-600 leading-relaxed">
                  Upload files or connect external data sources. You can always add more later from the Data Sources page.
                </p>

                {/* File upload zone */}
                <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-brand-300 hover:bg-brand-50/30 transition-colors">
                  <Upload className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                  <p className="text-sm font-medium text-slate-700">Drop files here or click to browse</p>
                  <p className="text-xs text-slate-400 mt-1">CSV, JSON, TXT, PDF, DOCX — up to 50 MB each</p>
                  <p className="text-xs text-slate-400 mt-0.5">Files are stored locally and never leave your machine</p>
                </div>

                {/* Supported formats */}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { icon: FileText, label: 'Documents', desc: 'PDF, DOCX, TXT — extract text and tables' },
                    { icon: Database, label: 'Spreadsheets', desc: 'CSV, XLSX — structured data ingestion' },
                    { icon: Globe, label: 'Google Workspace', desc: 'Drive, Gmail, Sheets — OAuth connected' },
                    { icon: Database, label: 'SQL Database', desc: 'Connected in Step 1 — already linked' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 border border-slate-200 rounded-xl">
                      <item.icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="text-[13px] font-medium text-slate-700 block">{item.label}</span>
                        <span className="text-[11px] text-slate-400">{item.desc}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="p-4 bg-emerald-50/60 border border-emerald-100 rounded-xl text-[13px] text-emerald-900">
                  <strong>Tip:</strong> The more data you provide, the better the AI understands your business.
                  You can upload files now or later — the system adapts automatically.
                </div>
              </div>
            )}

            {/* Step 4: Features */}
            {step === 4 && (
              <div className="space-y-5">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-brand-600" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">Enable Superpowers</h3>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                    <div>
                      <label className="text-sm font-medium text-slate-900">Newsroom (Market Intelligence)</label>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Search web for market trends, competitor news, and industry insights
                      </p>
                    </div>
                    <Toggle
                      checked={config.newsroomEnabled}
                      onChange={(v) => setConfig({ ...config, newsroomEnabled: v })}
                    />
                  </div>

                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                    <div>
                      <label className="text-sm font-medium text-slate-900">Code Sandbox (Advanced Math)</label>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Execute Python code for 100% accurate calculations and statistics
                      </p>
                    </div>
                    <Toggle
                      checked={config.codeSandboxEnabled}
                      onChange={(v) => setConfig({ ...config, codeSandboxEnabled: v })}
                    />
                  </div>

                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                    <div>
                      <label className="text-sm font-medium text-slate-900">Air-Gap Mode (Maximum Security)</label>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Disable all internet access. Only works with local AI models.
                      </p>
                    </div>
                    <Toggle
                      checked={config.airGapMode}
                      onChange={(v) => setConfig({ ...config, airGapMode: v })}
                      disabled={config.aiProvider === 'ollama-local'}
                    />
                  </div>

                  <div className="flex items-center justify-between p-4 border border-slate-200 rounded-xl">
                    <div>
                      <label className="text-sm font-medium text-slate-900">Proactive Monitoring</label>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Run a nightly anomaly scan and morning briefing, plus periodic data sync
                      </p>
                    </div>
                    <Toggle
                      checked={config.proactiveMonitoring}
                      onChange={(v) => setConfig({ ...config, proactiveMonitoring: v })}
                    />
                  </div>
                </div>

                <div className="p-4 bg-brand-50/60 border border-brand-100 rounded-xl text-[13px] text-brand-900 leading-relaxed">
                  <strong>You are almost ready!</strong> Once you click Finish, the AI will analyze
                  your database schema and prepare its first briefing. This takes about 30 seconds.
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-between mt-8">
              <button
                onClick={() => setStep(step - 1)}
                disabled={loading || step === 1}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium text-slate-600 rounded-xl hover:bg-slate-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>

              <button
                onClick={handleNext}
                disabled={loading}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {step === 4 ? 'Finish Setup' : 'Continue'}
                {!loading && <ArrowRight className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}