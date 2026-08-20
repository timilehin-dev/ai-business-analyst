import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
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
  return <SetupWizard onComplete={() => navigate('/dashboard')} />;
}

export default App;
