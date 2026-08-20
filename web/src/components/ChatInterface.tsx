import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Code, Database, ShieldCheck } from 'lucide-react';
import AppShell from './AppShell';
import Markdown from './Markdown';

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
      content:
        "Hi! I'm your autonomous business analyst. I've been monitoring your data overnight.\n\nAsk me anything about your business — revenue, orders, customers, trends — and I'll query your database and show my work.",
      timestamp: new Date(),
      confidence: 0.95,
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedWork, setExpandedWork] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
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
        sqlQuery: data.sql_query || undefined,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ ${err.message || 'Something went wrong. Is the backend running?'}`,
        timestamp: new Date(),
        confidence: 0,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWork = (id: string) => {
    setExpandedWork((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  return (
    <AppShell>
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Header */}
        <div className="mb-5">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Chat</h1>
          <p className="text-sm text-slate-500 mt-1">
            Ask questions in plain language — the analyst writes and executes the queries itself.
          </p>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto pr-1 space-y-5">
          {messages.map((message) => {
            const isUser = message.role === 'user';
            return (
              <div key={message.id} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
                {/* Avatar */}
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    isUser
                      ? 'bg-slate-800'
                      : 'bg-gradient-to-br from-brand-500 to-brand-700 shadow-sm'
                  }`}
                >
                  {isUser ? (
                    <User className="w-[18px] h-[18px] text-white" />
                  ) : (
                    <Bot className="w-[18px] h-[18px] text-white" />
                  )}
                </div>

                {/* Bubble */}
                <div className={`max-w-[78%] ${isUser ? 'text-right' : ''}`}>
                  <div
                    className={`rounded-2xl px-5 py-4 text-left ${
                      isUser
                        ? 'bg-brand-600 text-white rounded-tr-md'
                        : 'bg-white border border-slate-200 shadow-card rounded-tl-md'
                    }`}
                  >
                    {isUser ? (
                      <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    ) : (
                      <Markdown>{message.content}</Markdown>
                    )}

                    {/* Assistant meta row */}
                    {!isUser && (
                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {message.confidence !== undefined && message.confidence > 0 && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-100 rounded-full px-2 py-1">
                              <ShieldCheck className="w-3 h-3 text-emerald-500" />
                              {Math.round(message.confidence * 100)}% grounded
                            </span>
                          )}
                          {message.sqlQuery && (
                            <button
                              onClick={() => toggleWork(message.id)}
                              className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-full px-2.5 py-1 transition-colors"
                            >
                              <Code className="w-3 h-3" />
                              {expandedWork.includes(message.id) ? 'Hide work' : 'Show work'}
                            </button>
                          )}
                        </div>
                        <span className="text-[11px] text-slate-400">
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* SQL work panel */}
                  {!isUser && expandedWork.includes(message.id) && message.sqlQuery && (
                    <div className="mt-2 rounded-xl bg-slate-900 text-slate-100 overflow-hidden text-left">
                      <div className="px-4 py-2.5 bg-slate-800/60 flex items-center gap-2 text-[11px] text-slate-400 font-medium uppercase tracking-wide">
                        <Database className="w-3.5 h-3.5" /> SQL executed
                      </div>
                      <pre className="p-4 text-[13px] font-mono leading-relaxed overflow-x-auto">
                        {message.sqlQuery}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center flex-shrink-0">
                <Bot className="w-[18px] h-[18px] text-white" />
              </div>
              <div className="bg-white border border-slate-200 shadow-card rounded-2xl rounded-tl-md px-5 py-4 flex items-center gap-2.5">
                <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                <span className="text-sm text-slate-500">
                  Querying your data and grounding the answer…
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="mt-5 pt-4 border-t border-slate-200">
          <div className="flex items-end gap-2.5 bg-white border border-slate-200 rounded-2xl shadow-card p-2 focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-400 transition-shadow">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask anything about your business data…"
              disabled={isLoading}
              rows={1}
              className="flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] text-slate-900 placeholder:text-slate-400 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="w-11 h-11 flex items-center justify-center bg-brand-600 text-white rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Enter to send · Shift+Enter for a new line · Every number is verified against your data
          </p>
        </div>
      </div>
    </AppShell>
  );
}