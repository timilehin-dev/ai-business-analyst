import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import SetupWizard from './components/SetupWizard';
import Dashboard from './components/Dashboard';
import ChatInterface from './components/ChatInterface';
import DataSources from './components/DataSources';
import SettingsPage from './components/Settings';
import Memory from './components/Memory';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/setup" replace />} />
        <Route path="/setup" element={<SetupWizardWrapper />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chat" element={<ChatInterface />} />
        <Route path="/data" element={<DataSources />} />
        <Route path="/memory" element={<Memory />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

function SetupWizardWrapper() {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);

  // If setup is already complete, skip the wizard entirely
  useEffect(() => {
    let cancelled = false;
    fetch('/api/setup/status')
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled && data?.is_configured) {
          navigate('/dashboard', { replace: true });
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-brand-50/40 to-slate-100">
        <p className="text-sm text-slate-400">Checking setup status…</p>
      </div>
    );
  }

  return <SetupWizard onComplete={() => navigate('/dashboard')} />;
}

export default App;