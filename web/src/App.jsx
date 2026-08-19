import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SetupWizard from './components/SetupWizard';
import Dashboard from './components/Dashboard';
import Briefing from './components/Briefing';
import ChatInterface from './components/ChatInterface';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/setup" replace />} />
        <Route path="/setup" element={<SetupWizard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/briefing" element={<Briefing />} />
        <Route path="/chat" element={<ChatInterface />} />
      </Routes>
    </Router>
  );
}

export default App;
