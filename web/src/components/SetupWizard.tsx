import { useState } from 'react';
import { CheckCircle2, Loader2, Database, Brain, Sparkles } from "lucide-react";

interface SetupWizardProps {
  onComplete: () => void;
}

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
    modelReasoning: '',
    modelSql: '',
    newsroomEnabled: true,
    codeSandboxEnabled: true,
    airGapMode: false,
  });

  const testConnection = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/setup/test-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: config.dbType,
          host: config.dbHost,
          port: config.dbPort,
          database: config.dbName,
          username: config.dbUser,
          password: config.dbPassword,
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Connection failed');
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
          database: {
            type: config.dbType,
            host: config.dbHost,
            port: config.dbPort,
            database: config.dbName,
            username: config.dbUser,
            password: config.dbPassword,
          },
          ai: {
            provider: config.aiProvider,
            api_key: config.apiKey,
            models: {
              reasoning: config.modelReasoning,
              sql: config.modelSql,
            },
          },
          features: {
            newsroom: config.newsroomEnabled,
            code_sandbox: config.codeSandboxEnabled,
            air_gap: config.airGapMode,
          },
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Setup failed');
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
      saveConfiguration();
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-2xl bg-white border rounded-lg shadow-lg">
        <div className="p-6 border-b">
          <div className="flex items-center gap-3 mb-2">
            <Brain className="h-8 w-8 text-indigo-600" />
            <h2 className="text-2xl font-bold">Welcome to Your AI Business Analyst</h2>
          </div>
          <p className="text-gray-600 text-sm">
            Let us get you set up in 3 simple steps. No technical knowledge required.
          </p>
          
          <div className="flex gap-2 mt-4">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full ${s <= step ? 'bg-indigo-600' : 'bg-gray-200'}`}
              />
            ))}
          </div>
        </div>
        
        <div className="p-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
          
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Database className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold">Connect Your Data</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Database Type</label>
                  <select
                    value={config.dbType}
                    onChange={(e) => setConfig({ ...config, dbType: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="sqlite">SQLite (Recommended for getting started)</option>
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                    <option value="csv">CSV Files (Upload later)</option>
                  </select>
                </div>
                
                {config.dbType !== 'sqlite' && config.dbType !== 'csv' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Host</label>
                      <input
                        type="text"
                        placeholder="localhost"
                        value={config.dbHost}
                        onChange={(e) => setConfig({ ...config, dbHost: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                      <input
                        type="text"
                        placeholder="5432"
                        value={config.dbPort}
                        onChange={(e) => setConfig({ ...config, dbPort: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Database Name</label>
                      <input
                        type="text"
                        placeholder="my_database"
                        value={config.dbName}
                        onChange={(e) => setConfig({ ...config, dbName: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                      <input
                        type="text"
                        placeholder="username"
                        value={config.dbUser}
                        onChange={(e) => setConfig({ ...config, dbUser: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                      <input
                        type="password"
                        placeholder="password"
                        value={config.dbPassword}
                        onChange={(e) => setConfig({ ...config, dbPassword: e.target.value })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                  </>
                )}
                
                {config.dbType === 'sqlite' && (
                  <div className="col-span-2">
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
                      SQLite will be created automatically. Perfect for testing and small teams.
                      You can migrate to PostgreSQL later.
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold">Choose Your AI Brain</h3>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">AI Provider</label>
                <select
                  value={config.aiProvider}
                  onChange={(e) => setConfig({ ...config, aiProvider: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={config.apiKey}
                    onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your API key is encrypted and stored locally. Never sent to our servers.
                  </p>
                </div>
              )}
              
              {config.aiProvider === 'ollama-local' && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <div>
                    Ollama will run on your machine. Make sure you have it installed:
                    <br />
                    <code className="bg-gray-100 px-2 py-1 rounded mt-2 block">
                      curl -fsSL https://ollama.com/install.sh | sh
                    </code>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold">Enable Superpowers</h3>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <label className="font-medium">Newsroom (Market Intelligence)</label>
                    <p className="text-sm text-gray-500">
                      Search web for market trends, competitor news, and industry insights
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.newsroomEnabled}
                      onChange={(e) => setConfig({ ...config, newsroomEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
                
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <label className="font-medium">Code Sandbox (Advanced Math)</label>
                    <p className="text-sm text-gray-500">
                      Execute Python code for 100% accurate calculations and statistics
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.codeSandboxEnabled}
                      onChange={(e) => setConfig({ ...config, codeSandboxEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
                
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <label className="font-medium">Air-Gap Mode (Maximum Security)</label>
                    <p className="text-sm text-gray-500">
                      Disable all internet access. Only works with local AI models.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.airGapMode}
                      onChange={(e) => setConfig({ ...config, airGapMode: e.target.checked })}
                      disabled={config.aiProvider === 'ollama-local'}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
              </div>
              
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
                <strong>You are almost ready!</strong> Once you click Finish, the AI will analyze 
                your database schema and prepare its first briefing. This takes about 30 seconds.
              </div>
            </div>
          )}
          
          <div className="flex justify-between mt-6">
            {step > 1 ? (
              <button
                onClick={() => setStep(step - 1)}
                disabled={loading}
                className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                Back
              </button>
            ) : (
              <div />
            )}
            
            <button
              onClick={handleNext}
              disabled={loading}
              className="px-8 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {step === 3 ? 'Finish Setup' : 'Continue'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}