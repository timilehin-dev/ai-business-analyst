import { useState, useEffect } from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  RefreshCw,
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  FileText,
} from 'lucide-react';
import AppShell from './AppShell';
import Markdown from './Markdown';

interface Finding {
  table: string;
  metric: string;
  current: number;
  previous: number;
  change_pct: number | null;
  direction: string;
  severity: string;
  window: string;
}

interface Briefing {
  id: number;
  generated_at: string;
  summary: string;
  findings: Finding[];
  status: string;
}

const formatNumber = (n: number) => {
  if (Math.abs(n) >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

const formatChange = (f: Finding) => {
  if (f.change_pct === null) return 'new activity';
  const sign = f.change_pct > 0 ? '+' : '';
  return `${sign}${f.change_pct.toFixed(1)}%`;
};

const metricLabel = (f: Finding) =>
  f.metric === '__row_count__' ? `${f.table} rows` : `${f.table} · ${f.metric.replace(/_/g, ' ')}`;

export default function Dashboard() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const res = await fetch('/api/briefing');
      const data = await res.json();
      setBriefing(data.briefing);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const generateNow = async () => {
    setGenerating(true);
    setError('');
    try {
      const res = await fetch('/api/briefing/generate', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Generation failed');
      setBriefing(data.briefing);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const today = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <AppShell>
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">{today} · Here's what the analyst found overnight.</p>
        </div>
        <button
          onClick={generateNow}
          disabled={generating}
          className="inline-flex items-center gap-2 bg-brand-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl shadow-sm hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {generating ? 'Analyzing…' : 'Generate Briefing Now'}
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-32 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading briefing…
        </div>
      ) : !briefing ? (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-16 text-center">
          <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-slate-100 flex items-center justify-center">
            <FileText className="w-7 h-7 text-slate-400" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">No briefing yet</h2>
          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
            The Sense loop runs automatically every night at 6 AM — it scans your database for
            anomalies and writes a briefing. Click <span className="font-medium">Generate Briefing Now</span>{' '}
            to run it immediately.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* KPI cards */}
          {briefing.findings.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {briefing.findings.slice(0, 4).map((f, i) => {
                const down = f.direction === 'down';
                const critical = f.severity === 'critical';
                const deltaColor = f.change_pct === null
                  ? 'bg-slate-100 text-slate-600'
                  : down
                  ? critical ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                  : 'bg-emerald-50 text-emerald-600';
                const DeltaIcon = f.change_pct === null ? Minus : down ? ArrowDownRight : ArrowUpRight;
                return (
                  <div key={i} className="bg-white border border-slate-200 rounded-2xl shadow-card p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[13px] font-medium text-slate-500 truncate pr-2">
                        {metricLabel(f)}
                      </span>
                      {critical ? (
                        <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      ) : (
                        <Activity className="w-4 h-4 text-slate-300 flex-shrink-0" />
                      )}
                    </div>
                    <div className="text-[28px] font-bold text-slate-900 tracking-tight leading-none">
                      {formatNumber(f.current)}
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${deltaColor}`}>
                        <DeltaIcon className="w-3.5 h-3.5" />
                        {formatChange(f)}
                      </span>
                      <span className="text-[11px] text-slate-400">vs prior period</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Briefing */}
          <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-brand-600" />
                </div>
                <div>
                  <h2 className="text-[15px] font-semibold text-slate-900">Overnight Briefing</h2>
                  <p className="text-[11px] text-slate-400">
                    {briefing.generated_at ? new Date(briefing.generated_at).toLocaleString() : ''}
                  </p>
                </div>
              </div>
              <span
                className={`text-[11px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full ${
                  briefing.status === 'anomalies'
                    ? 'bg-amber-50 text-amber-700'
                    : briefing.status === 'error'
                    ? 'bg-red-50 text-red-600'
                    : 'bg-emerald-50 text-emerald-700'
                }`}
              >
                {briefing.status}
              </span>
            </div>
            <div className="px-6 py-5">
              <Markdown>{briefing.summary}</Markdown>
            </div>
          </section>

          {/* Findings */}
          {briefing.findings.length > 0 && (
            <section>
              <h2 className="text-[15px] font-semibold text-slate-900 mb-3">Detected Anomalies</h2>
              <div className="space-y-3">
                {briefing.findings.map((f, i) => {
                  const critical = f.severity === 'critical';
                  const down = f.direction === 'down';
                  return (
                    <div
                      key={i}
                      className="bg-white border border-slate-200 rounded-2xl shadow-card p-5 flex items-center justify-between gap-4 hover:shadow-card-hover transition-shadow"
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                            critical
                              ? 'bg-red-50 text-red-500'
                              : down
                              ? 'bg-amber-50 text-amber-600'
                              : 'bg-emerald-50 text-emerald-600'
                          }`}
                        >
                          {critical ? (
                            <AlertTriangle className="w-5 h-5" />
                          ) : down ? (
                            <TrendingDown className="w-5 h-5" />
                          ) : (
                            <TrendingUp className="w-5 h-5" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-slate-900 truncate">
                              {metricLabel(f)}
                            </span>
                            <span
                              className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full flex-shrink-0 ${
                                critical ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-700'
                              }`}
                            >
                              {f.severity}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5 truncate">{f.window}</p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-lg font-bold text-slate-900 leading-none">
                          {formatNumber(f.current)}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          vs {formatNumber(f.previous)}
                        </div>
                        <div
                          className={`text-xs font-semibold mt-1 ${
                            f.change_pct === null
                              ? 'text-slate-500'
                              : down
                              ? 'text-red-600'
                              : 'text-emerald-600'
                          }`}
                        >
                          {formatChange(f)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* All clear */}
          {briefing.findings.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-10 text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-emerald-50 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              </div>
              <h2 className="text-base font-semibold text-slate-900">All clear</h2>
              <p className="text-sm text-slate-500 mt-1">
                No anomalies detected in the last monitoring window.
              </p>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}