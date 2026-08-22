import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Loader2,
  Code,
  Database,
  ShieldCheck,
  BookOpen,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import AppShell from './AppShell';
import Markdown from './Markdown';
import FeedbackControls from './FeedbackControls';
import { api, AnalysisResponse, ContextUsed } from '../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sqlQuery?: string;
  confidence?: number;
  episodeId?: number | null;
  contextUsed?: ContextUsed | null;
  isError?: boolean;
}

interface HistoryItem {
  id: number;
  question: string;
  confidence: string | null;
  timestamp: string;
  sql_query?: string;
  answer?: string;
}

const GREETING: Message = {
  id: 'greeting',
  role: 'assistant',
  content:
    "Hi! I'm your autonomous business analyst.\n\nAsk me anything about your business — revenue, orders, customers, trends — and I'll query your database and show my work. Every number I report is checked against your data before you see it.",
  timestamp: new Date(),
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedWork, setExpandedWork] = useState<string[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadHistory = () => {
    api
      .get<{ history: HistoryItem[] }>('/api/chat/history')
      .then((d) => setHistory(d.history || []))
      .catch(() => setHistory([]));
  };

  useEffect(loadHistory, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', content: question, timestamp: new Date() },
    ]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await api.post<AnalysisResponse>('/api/analyze', { question });
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: data.answer || 'No answer returned.',
          timestamp: new Date(),
          confidence: data.confidence ?? 0,
          sqlQuery: data.sql_query || undefined,
          episodeId: data.episode_id,
          contextUsed: data.context_used,
        },
      ]);
      loadHistory();
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: err.message || 'Something went wrong. Is the backend running?',
          timestamp: new Date(),
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWork = (id: string) =>
    setExpandedWork((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );

  return (
    <AppShell>
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        <div className="mb-5">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Chat</h1>
          <p className="text-sm text-slate-500 mt-1">
            Ask questions in plain language — the analyst writes and executes the queries itself.
          </p>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto pr-1 space-y-5">
          {messages.map((message) => {
            const isUser = message.role === 'user';
            return (
              <div key={message.id} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    isUser
                      ? 'bg-slate-800'
                      : message.isError
                        ? 'bg-rose-500'
                        : 'bg-gradient-to-br from-brand-500 to-brand-700 shadow-sm'
                  }`}
                >
                  {isUser ? (
                    <User className="w-[18px] h-[18px] text-white" />
                  ) : message.isError ? (
                    <AlertTriangle className="w-[18px] h-[18px] text-white" />
                  ) : (
                    <Bot className="w-[18px] h-[18px] text-white" />
                  )}
                </div>

                <div className={`max-w-[78%] ${isUser ? 'text-right' : ''}`}>
                  <div
                    className={`rounded-2xl px-5 py-4 text-left ${
                      isUser
                        ? 'bg-brand-600 text-white rounded-tr-md'
                        : message.isError
                          ? 'bg-rose-50 border border-rose-200 rounded-tl-md'
                          : 'bg-white border border-slate-200 shadow-card rounded-tl-md'
                    }`}
                  >
                    {isUser ? (
                      <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </p>
                    ) : message.isError ? (
                      <p className="text-[15px] leading-relaxed text-rose-700">{message.content}</p>
                    ) : (
                      <Markdown>{message.content}</Markdown>
                    )}

                    {!isUser && !message.isError && (
                      <div className="mt-4 pt-3 border-t border-slate-100 space-y-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            {message.confidence !== undefined && message.confidence > 0 && (
                              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-100 rounded-full px-2 py-1">
                                <ShieldCheck className="w-3 h-3 text-emerald-500" />
                                {Math.round(message.confidence * 100)}% confidence
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
                            {message.timestamp.toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>

                        <ContextChips context={message.contextUsed} />

                        {message.episodeId != null && (
                          <FeedbackControls episodeId={message.episodeId} />
                        )}
                      </div>
                    )}
                  </div>

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

        {history.length > 0 && (
          <details className="mt-4 bg-white border border-slate-200 rounded-2xl shadow-card">
            <summary className="cursor-pointer select-none px-5 py-3 text-sm font-semibold text-slate-900">
              Query history ({history.length})
            </summary>
            <div className="px-5 pb-4 space-y-3 max-h-64 overflow-y-auto">
              {history.map((item) => (
                <div key={item.id} className="p-3 bg-slate-50 rounded-xl">
                  <div className="text-sm font-medium text-slate-800 truncate">{item.question}</div>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                        item.confidence && parseFloat(item.confidence) >= 0.8
                          ? 'bg-emerald-50 text-emerald-600'
                          : 'bg-amber-50 text-amber-600'
                      }`}
                    >
                      {item.confidence ? Math.round(parseFloat(item.confidence) * 100) : 0}%
                      confidence
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <button
                    onClick={() => setInput(item.question)}
                    className="mt-1.5 text-[11px] text-brand-600 hover:text-brand-700 font-medium underline underline-offset-2"
                  >
                    Ask again
                  </button>
                </div>
              ))}
            </div>
          </details>
        )}

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
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
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

/** Shows which remembered knowledge shaped an answer. */
function ContextChips({ context }: { context?: ContextUsed | null }) {
  if (!context) return null;

  const chips: { icon: typeof BookOpen; label: string }[] = [];
  if (context.rules_applied?.length) {
    chips.push({
      icon: ShieldCheck,
      label: `${context.rules_applied.length} standing instruction${
        context.rules_applied.length > 1 ? 's' : ''
      }`,
    });
  }
  if (context.glossary_terms?.length) {
    chips.push({ icon: BookOpen, label: `Glossary: ${context.glossary_terms.join(', ')}` });
  }
  if (context.documents_used?.length) {
    chips.push({
      icon: FileText,
      label: `${context.documents_used.length} document${
        context.documents_used.length > 1 ? 's' : ''
      }`,
    });
  }

  if (!chips.length) return null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[11px] text-slate-400">Used:</span>
      {chips.map(({ icon: Icon, label }) => (
        <span
          key={label}
          className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded-full px-2 py-0.5"
        >
          <Icon className="w-3 h-3" />
          {label}
        </span>
      ))}
    </div>
  );
}
