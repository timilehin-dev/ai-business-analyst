import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Database, Brain, Zap, CheckCircle, AlertCircle } from 'lucide-react';

export default function SetupWizard() {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState({
    dbType: 'sqlite',
    dbUrl: '',
    aiProvider: 'ollama',
    apiKey: '',
    enableNewsroom: true,
    enableSandbox: true,
    airGapMode: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      await axios.post('/api/setup/configure', config);
      setStep(4);
    } catch (err) {
      setError(err.response?.data?.detail || 'Configuration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden">
        {/* Header */}
        <div className="bg-slate-50 px-8 py-6 border-b border-slate-200">
          <h1 className="text-2xl font-bold text-slate-900">Welcome to AI Business Analyst</h1>
          <p className="text-slate-600 mt-2">Let's get you set up in 3 simple steps</p>
        </div>

        {/* Progress */}
        <div className="px-8 py-4 bg-slate-50">
          <div className="flex items-center justify-between">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  step >= s ? 'bg-blue-600 text-white' : 'bg-slate-300 text-slate-600'
                }`}>
                  {step > s ? <CheckCircle className="w-5 h-5" /> : s}
                </div>
                {s < 3 && (
                  <div className={`w-24 h-1 mx-2 ${step > s ? 'bg-blue-600' : 'bg-slate-300'}`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-slate-600">
            <span>Data Connection</span>
            <span>AI Brain</span>
            <span>Superpowers</span>
          </div>
        </div>

        {/* Content */}
        <div className="px-8 py-8">
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-2">Connect Your Data</h2>
                <p className="text-slate-600">Where should we analyze data from?</p>
              </div>
              
              <div className="space-y-4">
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Database Type</span>
                  <select 
                    value={config.dbType}
                    onChange={(e) => setConfig({...config, dbType: e.target.value})}
                    className="mt-1 block w-full rounded-lg border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-3 border"
                  >
                    <option value="sqlite">SQLite (Recommended for getting started)</option>
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                    <option value="csv">CSV Files</option>
                  </select>
                </label>

                {config.dbType !== 'sqlite' && config.dbType !== 'csv' && (
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Connection String</span>
                    <input
                      type="text"
                      placeholder="postgresql://user:pass@localhost:5432/dbname"
                      value={config.dbUrl}
                      onChange={(e) => setConfig({...config, dbUrl: e.target.value})}
                      className="mt-1 block w-full rounded-lg border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-3 border"
                    />
                    <p className="text-xs text-slate-500 mt-1">We only use read-only access</p>
                  </label>
                )}
              </div>

              <button
                onClick={() => setStep(2)}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
              >
                Next: Choose AI Model
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-2">Choose Your AI Brain</h2>
                <p className="text-slate-600">Select the intelligence engine</p>
              </div>

              <div className="grid gap-4">
                {[
                  { id: 'ollama', name: 'Ollama (Local & Free)', desc: 'Runs on your machine. Zero cost, complete privacy.', icon: '🦙' },
                  { id: 'openai', name: 'OpenAI GPT-4', desc: 'Most powerful reasoning. Requires API key.', icon: '🧠' },
                  { id: 'anthropic', name: 'Anthropic Claude', desc: 'Excellent at analysis. Requires API key.', icon: '🤖' },
                  { id: 'ollama-cloud', name: 'Ollama Cloud', desc: 'Hosted Ollama models. Balanced cost/performance.', icon: '☁️' },
                ].map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => setConfig({...config, aiProvider: provider.id})}
                    className={`p-4 rounded-lg border-2 text-left transition ${
                      config.aiProvider === provider.id 
                        ? 'border-blue-600 bg-blue-50' 
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">{provider.icon}</span>
                      <div>
                        <h3 className="font-semibold text-slate-900">{provider.name}</h3>
                        <p className="text-sm text-slate-600">{provider.desc}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {['openai', 'anthropic', 'ollama-cloud'].includes(config.aiProvider) && (
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">API Key</span>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={config.apiKey}
                    onChange={(e) => setConfig({...config, apiKey: e.target.value})}
                    className="mt-1 block w-full rounded-lg border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-3 border"
                  />
                  <p className="text-xs text-slate-500 mt-1">Stored encrypted locally</p>
                </label>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 bg-slate-200 text-slate-700 py-3 rounded-lg font-semibold hover:bg-slate-300 transition"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
                >
                  Next: Enable Features
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-slate-900 mb-2">Enable Superpowers</h2>
                <p className="text-slate-600">Customize your analyst's capabilities</p>
              </div>

              <div className="space-y-4">
                <label className="flex items-start gap-3 p-4 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={config.enableNewsroom}
                    onChange={(e) => setConfig({...config, enableNewsroom: e.target.checked})}
                    className="mt-1 w-5 h-5 text-blue-600 rounded"
                  />
                  <div>
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <Zap className="w-5 h-5 text-yellow-500" />
                      Newsroom (Market Intelligence)
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      Automatically searches web for market trends, competitor news, and external context
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-4 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={config.enableSandbox}
                    onChange={(e) => setConfig({...config, enableSandbox: e.target.checked})}
                    className="mt-1 w-5 h-5 text-blue-600 rounded"
                  />
                  <div>
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <Brain className="w-5 h-5 text-purple-500" />
                      Code Sandbox (100% Accurate Math)
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      Executes Python code for calculations, ensuring zero hallucinations in statistics
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-4 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={config.airGapMode}
                    onChange={(e) => setConfig({...config, airGapMode: e.target.checked})}
                    className="mt-1 w-5 h-5 text-blue-600 rounded"
                  />
                  <div>
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-red-500" />
                      Air-Gap Mode (Maximum Security)
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      Disables all internet calls. Requires local models only. Ultimate privacy.
                    </p>
                  </div>
                </label>
              </div>

              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 bg-slate-200 text-slate-700 py-3 rounded-lg font-semibold hover:bg-slate-300 transition"
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50"
                >
                  {loading ? 'Setting Up...' : 'Launch Analyst'}
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="text-center py-12">
              <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-6" />
              <h2 className="text-2xl font-bold text-slate-900 mb-2">You're All Set!</h2>
              <p className="text-slate-600 mb-8">Your AI Business Analyst is ready to work.</p>
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
              >
                Go to Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
