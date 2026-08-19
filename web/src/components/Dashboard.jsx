import { useState } from 'react';
import { Send, BarChart3, MessageSquare, Lightbulb, CheckCircle, XCircle } from 'lucide-react';

export default function Dashboard() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! I'm your AI Business Analyst. I've connected to your data and I'm ready to help. What would you like to explore today?" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // TODO: Connect to actual API
      setTimeout(() => {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: "I'll analyze that for you. Let me query the data and check for any relevant market trends...",
          showWork: true,
          sql: "SELECT * FROM orders WHERE date > '2024-01-01'",
          chart: 'bar'
        }]);
        setLoading(false);
      }, 1500);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "Sorry, I encountered an error. Please check your connection." 
      }]);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-900">AI Business Analyst</h1>
          <nav className="flex gap-4">
            <a href="/dashboard" className="text-blue-600 font-medium">Chat</a>
            <a href="/briefing" className="text-slate-600 hover:text-slate-900">Briefing</a>
          </nav>
        </div>
      </header>

      {/* Main Chat */}
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="space-y-6 mb-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.role === 'user' ? 'bg-blue-600' : 'bg-green-600'
              }`}>
                {msg.role === 'user' ? <MessageSquare className="w-6 h-6 text-white" /> : <Lightbulb className="w-6 h-6 text-white" />}
              </div>
              
              <div className={`flex-1 ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-block p-4 rounded-lg ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white border border-slate-200 text-slate-900'
                }`}>
                  <p>{msg.content}</p>
                </div>

                {/* Show Work Panel */}
                {msg.showWork && (
                  <div className="mt-4 bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <div className="bg-slate-50 px-4 py-2 border-b border-slate-200 flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-700">Analysis Details</span>
                      <button className="text-xs text-blue-600 hover:underline">Copy SQL</button>
                    </div>
                    <div className="p-4 space-y-4">
                      {msg.sql && (
                        <div>
                          <label className="text-xs font-medium text-slate-500 uppercase">SQL Query</label>
                          <pre className="mt-1 bg-slate-900 text-green-400 p-3 rounded text-sm overflow-x-auto">
                            {msg.sql}
                          </pre>
                        </div>
                      )}
                      {msg.chart && (
                        <div>
                          <label className="text-xs font-medium text-slate-500 uppercase">Visualization</label>
                          <div className="mt-2 h-48 bg-slate-100 rounded flex items-center justify-center text-slate-400">
                            <BarChart3 className="w-12 h-12" />
                            <span className="ml-2">Chart would render here</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Feedback Buttons */}
                {msg.role === 'assistant' && (
                  <div className="mt-2 flex gap-2">
                    <button className="p-1 hover:bg-green-100 rounded text-green-600">
                      <CheckCircle className="w-4 h-4" />
                    </button>
                    <button className="p-1 hover:bg-red-100 rounded text-red-600">
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-green-600 flex items-center justify-center">
                <Lightbulb className="w-6 h-6 text-white" />
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-lg">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-4">
          <div className="max-w-4xl mx-auto flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask anything about your business data..."
              className="flex-1 p-4 border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-blue-600 text-white px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
