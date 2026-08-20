import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import SetupWizard from './components/SetupWizard';
import Dashboard from './components/Dashboard';
import Briefing from './components/Briefing';
import ChatInterface from './components/ChatInterface';
import DataSources from './components/DataSources';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/setup" replace />} />
        <Route path="/setup" element={<SetupWizardWrapper />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/briefing" element={<Briefing />} />
        <Route path="/chat" element={<ChatInterface />} />
        <Route path="/data" element={<DataSources />} />
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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <p className="text-gray-500">Checking setup status…</p>
      </div>
    );
  }

  return <SetupWizard onComplete={() => navigate('/dashboard')} />;
}

export default App;
