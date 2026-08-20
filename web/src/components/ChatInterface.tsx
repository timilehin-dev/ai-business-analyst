import React, { useState } from 'react';
import { Send, Bot, User, Loader2, ThumbsUp, ThumbsDown, Edit3, ChevronRight, Code, Database } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  showWork?: boolean;
  sqlQuery?: string;
  confidence?: number;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hi! I'm your autonomous business analyst. I've been monitoring your data overnight. Would you like to see my briefing, or do you have a specific question?",
      timestamp: new Date(),
      confidence: 0.95
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedWork, setExpandedWork] = useState<string[]>([]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Analysis failed');
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer || 'No answer returned.',
        timestamp: new Date(),
        confidence: data.confidence ?? 0.5,
        sqlQuery: data.sql_query || undefined
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ ${err.message || 'Something went wrong. Is the backend running?'}`,
        timestamp: new Date(),
        confidence: 0
      };
      setMessages(prev => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWork = (id: string) => {
    setExpandedWork(prev => 
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    );
  };

  return (
    <div className="flex flex-col h-screen max-w-5xl mx-auto p-4">
      {/* Messages Area */}
      <div className="flex-1 mb-4 space-y-4 pr-4 overflow-y-auto">
        {messages.map((message) => (
          <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.role === 'user' ? 'bg-blue-600' : 'bg-green-600'}`}>
              {message.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
            </div>
            
            <div className={`flex-1 rounded-lg border ${message.role === 'user' ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-200'}`}>
              <div className="p-4">
                <div className="whitespace-pre-wrap">{message.content}</div>
                
                {/* Confidence & Actions */}
                {message.role === 'assistant' && (
                  <div className="mt-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-1 bg-gray-100 rounded-full border">
                        {(message.confidence! * 100).toFixed(0)}% confidence
                      </span>
                      {message.sqlQuery && (
                        <button 
                          className="h-6 px-2 text-xs gap-1 bg-gray-100 rounded-md border hover:bg-gray-200 flex items-center"
                          onClick={() => toggleWork(message.id)}
                        >
                          <Code className="w-3 h-3" />
                          {expandedWork.includes(message.id) ? 'Hide Work' : 'Show Work'}
                        </button>
                      )}
                    </div>
                    
                    <div className="flex gap-1">
                      <button className="h-8 w-8 p-0 bg-gray-100 rounded-md border hover:bg-gray-200 flex items-center justify-center">
                        <ThumbsUp className="w-4 h-4" />
                      </button>
                      <button className="h-8 w-8 p-0 bg-gray-100 rounded-md border hover:bg-gray-200 flex items-center justify-center">
                        <ThumbsDown className="w-4 h-4" />
                      </button>
                      <button className="h-8 w-8 p-0 bg-gray-100 rounded-md border hover:bg-gray-200 flex items-center justify-center">
                        <Edit3 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* Expanded Work Panel */}
                {message.role === 'assistant' && expandedWork.includes(message.id) && message.sqlQuery && (
                  <div className="mt-4 p-3 bg-gray-900 text-gray-100 rounded-md font-mono text-sm overflow-x-auto">
                    <div className="flex items-center gap-2 mb-2 text-gray-400">
                      <Database className="w-4 h-4" />
                      <span>SQL Query Executed:</span>
                    </div>
                    <pre>{message.sqlQuery}</pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing data and searching market context...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask anything about your business data..."
          disabled={isLoading}
          className="flex-1 p-3 rounded-lg border border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50"
        />
        <button 
          onClick={handleSend} 
          disabled={isLoading || !input.trim()}
          className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}