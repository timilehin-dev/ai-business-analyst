import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, Loader2, Database, Brain, Sparkles } from "lucide-react";

interface SetupWizardProps {
  onComplete: () => void;
}

export default function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [config, setConfig] = useState({
    // Step 1: Database Connection
    dbType: 'sqlite',
    dbHost: '',
    dbPort: '',
    dbName: '',
    dbUser: '',
    dbPassword: '',
    
    // Step 2: AI Provider
    aiProvider: 'ollama-local',
    apiKey: '',
    modelReasoning: '',
    modelSql: '',
    
    // Step 3: Features
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
      
      // Success - move to next step
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
      
      // Setup complete!
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
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <Brain className="h-8 w-8 text-indigo-600" />
            <CardTitle className="text-2xl">Welcome to Your AI Business Analyst</CardTitle>
          </div>
          <CardDescription>
            Let's get you set up in 3 simple steps. No technical knowledge required.
          </CardDescription>
          
          {/* Progress Indicator */}
          <div className="flex gap-2 mt-4">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full ${
                  s <= step ? 'bg-indigo-600' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
        </CardHeader>
        
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          {/* STEP 1: Database Connection */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Database className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold">Connect Your Data</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Database Type</Label>
                  <Select
                    value={config.dbType}
                    onValueChange={(value) => setConfig({ ...config, dbType: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sqlite">SQLite (Recommended for getting started)</SelectItem>
                      <SelectItem value="postgresql">PostgreSQL</SelectItem>
                      <SelectItem value="mysql">MySQL</SelectItem>
                      <SelectItem value="csv">CSV Files (Upload later)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {config.dbType !== 'sqlite' && config.dbType !== 'csv' && (
                  <>
                    <div>
                      <Label>Host</Label>
                      <Input
                        placeholder="localhost"
                        value={config.dbHost}
                        onChange={(e) => setConfig({ ...config, dbHost: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>Port</Label>
                      <Input
                        placeholder="5432"
                        value={config.dbPort}
                        onChange={(e) => setConfig({ ...config, dbPort: e.target.value })}
                      />
                    </div>
                    <div className="col-span-2">
                      <Label>Database Name</Label>
                      <Input
                        placeholder="my_database"
                        value={config.dbName}
                        onChange={(e) => setConfig({ ...config, dbName: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>Username</Label>
                      <Input
                        placeholder="username"
                        value={config.dbUser}
                        onChange={(e) => setConfig({ ...config, dbUser: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>Password</Label>
                      <Input
                        type="password"
                        placeholder="••••••••"
                        value={config.dbPassword}
                        onChange={(e) => setConfig({ ...config, dbPassword: e.target.value })}
                      />
                    </div>
                  </>
                )}
                
                {config.dbType === 'sqlite' && (
                  <div className="col-span-2">
                    <Alert>
                      <AlertDescription>
                        SQLite will be created automatically. Perfect for testing and small teams.
                        You can migrate to PostgreSQL later.
                      </AlertDescription>
                    </Alert>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* STEP 2: AI Provider */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold">Choose Your AI Brain</h3>
              </div>
              
              <div>
                <Label>AI Provider</Label>
                <Select
                  value={config.aiProvider}
                  onValueChange={(value) => setConfig({ ...config, aiProvider: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ollama-local">
                      🆓 Ollama (Local, Free, Private) - Recommended
                    </SelectItem>
                    <SelectItem value="ollama-cloud">
                      ☁️ Ollama Cloud
                    </SelectItem>
                    <SelectItem value="openai">
                      🔵 OpenAI (GPT-4)
                    </SelectItem>
                    <SelectItem value="anthropic">
                      🟣 Anthropic (Claude)
                    </SelectItem>
                    <SelectItem value="custom">
                      🔧 Custom OpenAI-Compatible API
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {config.aiProvider !== 'ollama-local' && (
                <div>
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    placeholder="sk-..."
                    value={config.apiKey}
                    onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your API key is encrypted and stored locally. Never sent to our servers.
                  </p>
                </div>
              )}
              
              {config.aiProvider === 'ollama-local' && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <AlertDescription>
                    Ollama will run on your machine. Make sure you have it installed:
                    <br />
                    <code className="bg-gray-100 px-2 py-1 rounded mt-2 block">
                      curl -fsSL https://ollama.com/install.sh | sh
                    </code>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
          
          {/* STEP 3: Features */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold">Enable Superpowers</h3>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="font-medium">Newsroom (Market Intelligence)</Label>
                    <p className="text-sm text-gray-500">
                      Search web for market trends, competitor news, and industry insights
                    </p>
                  </div>
                  <Switch
                    checked={config.newsroomEnabled}
                    onCheckedChange={(checked) => setConfig({ ...config, newsroomEnabled: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="font-medium">Code Sandbox (Advanced Math)</Label>
                    <p className="text-sm text-gray-500">
                      Execute Python code for 100% accurate calculations and statistics
                    </p>
                  </div>
                  <Switch
                    checked={config.codeSandboxEnabled}
                    onCheckedChange={(checked) => setConfig({ ...config, codeSandboxEnabled: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="font-medium">Air-Gap Mode (Maximum Security)</Label>
                    <p className="text-sm text-gray-500">
                      Disable all internet access. Only works with local AI models.
                    </p>
                  </div>
                  <Switch
                    checked={config.airGapMode}
                    onCheckedChange={(checked) => setConfig({ ...config, airGapMode: checked })}
                    disabled={config.aiProvider === 'ollama-local'}
                  />
                </div>
              </div>
              
              <Alert className="bg-blue-50 border-blue-200">
                <AlertDescription>
                  <strong>You're almost ready!</strong> Once you click Finish, the AI will analyze 
                  your database schema and prepare its first briefing. This takes about 30 seconds.
                </AlertDescription>
              </Alert>
            </div>
          )}
          
          {/* Navigation Buttons */}
          <div className="flex justify-between mt-6">
            {step > 1 ? (
              <Button
                variant="outline"
                onClick={() => setStep(step - 1)}
                disabled={loading}
              >
                Back
              </Button>
            ) : (
              <div />
            )}
            
            <Button
              onClick={handleNext}
              disabled={loading}
              className="px-8"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {step === 3 ? 'Finish Setup' : 'Continue'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
