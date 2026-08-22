import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  FileText,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import AppShell from './AppShell';
import Markdown from './Markdown';

/* ------------------------------------------------------------------ */
/*  Types (backend is schema-agnostic)                                 */
/* ------------------------------------------------------------------ */
interface DashboardMetrics {
  fact_table: string | null;
  measure: string | null;
  date_column: string | null;
  total_records: number;
  table_count: number;
  measure_total?: number | null;
  records_30d?: number | null;
  records_prev_30d?: number | null;
  measure_30d?: number | null;
  measure_prev_30d?: number | null;
}

interface Category {
  label: string;
  value: number | null;
  records: number;
}

interface Trend {
  day: string;
  records: number;
  value?: number | null;
}

interface RecentRow {
  [column: string]: string | number | null;
}

interface TopDimension {
  dimension: string;
  values: Category[];
}

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

interface DashboardData {
  status: string;
  message?: string;
  metrics: DashboardMetrics;
  categories: Category[];
  category_dimension: string | null;
  trends: Trend[];
  recent_activity: RecentRow[];
  top_dimensions: TopDimension[];
  schema?: { tables: string[]; table_count: number };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
const fmt = (n?: number | null) => {
  if (n == null) return '—';
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
};

const fmtInt = (n?: number | null) => (n == null ? '—' : n.toLocaleString());

const fmtAuto = (v: string | number | null) => {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') return fmtInt(v);
  const text = String(v);
  if (/^-?\d[\d.,]*$/.test(text.trim())) return text;
  return text;
};

const pctChange = (curr?: number | null, prev?: number | null) => {
  if (curr == null || prev == null) return null;
  if (prev === 0) return curr > 0 ? 100 : 0;
  return ((curr - prev) / prev) * 100;
};

const isMonetary = (name?: string | null) =>
  !!name &&
  /revenue|sales|amount|total|gross|net|price|cost|value|balance|spend|fee|charge|payment|turnover/i.test(name);

/* ------------------------------------------------------------------ */
/*  Dashboard                                                          */
/* ------------------------------------------------------------------ */
export default function Dashboard() {
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadDashboard = useCallback(async () => {
    try {
      const [dashRes, briefRes] = await Promise.all([
        fetch('/api/dashboard'),
        fetch('/api/briefing'),
      ]);
      const dashData = (await dashRes.json()) as DashboardData;
      const briefData = await briefRes.json();
      setDash(dashData);
      setBriefing(briefData.briefing);
      setLastRefresh(new Date());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadDashboard]);

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

  const m = dash?.metrics;
  const monetary = isMonetary(m?.measure);
  const format = (n?: number | null) => (monetary ? fmt(n) : fmtInt(n));

  const metricLabel = m?.measure ? m.measure.replace(/_/g, ' ') : 'Total';
  const measureGrowth = pctChange(m?.measure_30d, m?.measure_prev_30d);
  const recordGrowth = pctChange(m?.records_30d, m?.records_prev_30d);

  const kpis = m
    ? [
        {
          label: `${metricLabel} (30d)`,
          value: format(m.measure_30d),
          icon: DollarSign,
          change: measureGrowth,
        },
        {
          label: 'Records (30d)',
          value: fmtInt(m.records_30d),
          icon: Activity,
          change: recordGrowth,
        },
        {
          label: 'All-time records',
          value: fmtInt(m.total_records),
          icon: BarChart3,
          change: null,
        },
        {
          label: 'Tables',
          value: fmtInt(m.table_count),
          icon: FileText,
          change: null,
        },
      ]
    : [];

  const factSource = m?.fact_table ? ` · ${m.fact_table}` : '';

  if (loading && !dash) {
    return (
      <AppShell>
        <div className="flex items-center justify-center py-32 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading dashboard…
        </div>
      </AppShell>
    );
  }

  const empty = (title: string, body: string) => (
    <AppShell>
      <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-16 text-center">
        <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-slate-100 flex items-center justify-center">
          <BarChart3 className="w-7 h-7 text-slate-400" />
        </div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">{body}</p>
      </div>
    </AppShell>
  );

  if (dash && (dash.status === 'no_database' || dash.status === 'no_tables')) {
    return empty(
      dash.status === 'no_database' ? 'No database connected' : 'No business tables found',
      dash.message || 'Run the setup wizard to connect your organization’s data.'
    );
  }

  return (
    <AppShell>
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            {today} · Live data from your database{factSource}
            {lastRefresh && (
              <span className="ml-2 text-slate-400">Updated {lastRefresh.toLocaleTimeString()}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setLoading(true); loadDashboard(); }}
            className="inline-flex items-center gap-2 bg-white border border-slate-200 text-slate-700 text-sm font-medium px-3 py-2 rounded-xl hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={generateNow}
            disabled={generating}
            className="inline-flex items-center gap-2 bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-xl shadow-sm hover:bg-brand-700 transition-colors disabled:opacity-50"
          >
            {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {generating ? 'Analyzing…' : 'Generate Briefing'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
      )}

      <div className="space-y-8">
        {kpis.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((kpi, i) => {
              const Icon = kpi.icon;
              const up = kpi.change !== null && kpi.change > 0;
              const down = kpi.change !== null && kpi.change < 0;
              return (
                <div key={i} className="bg-white border border-slate-200 rounded-2xl shadow-card p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[13px] font-medium text-slate-500">{kpi.label}</span>
                    <Icon className="w-4 h-4 text-slate-300" />
                  </div>
                  <div className="text-[28px] font-bold text-slate-900 tracking-tight leading-none">
                    {kpi.value}
                  </div>
                  {kpi.change !== null && (
                    <div className="mt-3 flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${
                          up ? 'bg-emerald-50 text-emerald-600' : down ? 'bg-red-50 text-red-600' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {up ? <ArrowUpRight className="w-3.5 h-3.5" /> : down ? <ArrowDownRight className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />}
                        {kpi.change > 0 ? '+' : ''}{kpi.change.toFixed(1)}%
                      </span>
                      <span className="text-[11px] text-slate-400">vs prior 30d</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {dash!.categories.length > 0 && (
            <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">
                  By {dash!.category_dimension || 'category'}
                </h2>
              </div>
              <div className="divide-y divide-slate-100">
                {dash!.categories.slice(0, 8).map((cat, i) => {
                  const maxVal = Math.max(1, ...dash!.categories.map((c) => c.value || 0));
                  const pct = ((cat.value || 0) / maxVal) * 100;
                  return (
                    <div key={i} className="px-6 py-3">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-medium text-slate-700 capitalize">{cat.label || '—'}</span>
                        <span className="text-sm font-semibold text-slate-900">{format(cat.value)}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5">
                        <div className="bg-brand-500 h-1.5 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-[11px] text-slate-400">{fmtInt(cat.records)} records</span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {dash!.top_dimensions.length > 0 && (
            <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">Top Breakdowns</h2>
              </div>
              <div className="divide-y divide-slate-100">
                {dash!.top_dimensions.map((dim) => (
                  <div key={dim.dimension} className="px-6 py-3.5">
                    <span className="text-[11px] uppercase tracking-wide text-slate-400 font-medium">
                      {dim.dimension.replace(/_/g, ' ')}
                    </span>
                    <div className="mt-2 flex items-end gap-1 h-14">
                      {dim.values.map((v, j) => {
                        const maxVal = Math.max(1, ...dim.values.map((x) => x.value || 0));
                        const height = ((v.value || 0) / maxVal) * 100;
                        return (
                          <div key={j} className="flex-1 flex flex-col items-center gap-1 group relative">
                            <div
                              className="w-full bg-brand-300 rounded-t hover:bg-brand-500 transition-colors min-h-[2px]"
                              style={{ height: `${height}%` }}
                            />
                            <div className="hidden group-hover:block absolute bottom-full mb-1 bg-slate-900 text-white text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap z-10">
                              {v.label}: {format(v.value)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {dash!.trends.length > 0 && (
          <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-[15px] font-semibold text-slate-900">
                Daily trend — {m?.measure ? m.measure.replace(/_/g, ' ') : 'record count'} (30 days)
              </h2>
            </div>
            <div className="px-6 py-4">
              <div className="flex items-end gap-1 h-32">
                {dash!.trends.map((t, i) => {
                  const series = dash!.trends.map((x) => (m?.measure ? x.value ?? x.records : x.records));
                  const maxVal = Math.max(1, ...series.map((v) => v || 0));
                  const val = m?.measure ? t.value ?? t.records : t.records;
                  const height = ((val || 0) / maxVal) * 100;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                      <div
                        className="w-full bg-brand-400 rounded-t hover:bg-brand-600 transition-colors min-h-[2px]"
                        style={{ height: `${height}%` }}
                      />
                      <div className="hidden group-hover:block absolute bottom-full mb-2 bg-slate-900 text-white text-[11px] px-2 py-1 rounded-lg whitespace-nowrap z-10">
                        {t.day}: {format(val)} ({fmtInt(t.records)} records)
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-2 text-[11px] text-slate-400">
                <span>{dash!.trends[0]?.day}</span>
                <span>{dash!.trends[dash!.trends.length - 1]?.day}</span>
              </div>
            </div>
          </section>
        )}

        {dash!.recent_activity.length > 0 && (
          <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-[15px] font-semibold text-slate-900">Recent activity</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-[12px] font-medium text-slate-500 uppercase tracking-wide">
                    {Object.keys(dash!.recent_activity[0] || {}).map((col) => (
                      <th key={col} className="px-6 py-3 whitespace-nowrap">{col.replace(/_/g, ' ')}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dash!.recent_activity.map((row, i) => (
                    <tr key={i} className="hover:bg-slate-50 transition-colors">
                      {Object.values(row).map((val, j) => (
                        <td key={j} className="px-6 py-3 text-slate-600 whitespace-nowrap">{fmtAuto(val as string | number | null)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {briefing ? (
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

            {briefing.findings.length > 0 && (
              <div className="px-6 pb-5 space-y-3">
                <h3 className="text-[13px] font-semibold text-slate-700">Detected Anomalies</h3>
                {briefing.findings.map((f, i) => {
                  const critical = f.severity === 'critical';
                  const down = f.direction === 'down';
                  const sign = f.change_pct !== null ? (f.change_pct > 0 ? '+' : '') : '';
                  return (
                    <div key={i} className="flex items-center justify-between gap-4 p-4 bg-slate-50 rounded-xl">
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            critical ? 'bg-red-50 text-red-500' : down ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'
                          }`}
                        >
                          {critical ? <AlertTriangle className="w-4 h-4" /> : down ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                        </div>
                        <div className="min-w-0">
                          <span className="text-sm font-medium text-slate-900 truncate block">
                            {f.metric === '__row_count__' ? `${f.table} rows` : `${f.table} · ${f.metric.replace(/_/g, ' ')}`}
                          </span>
                          <span className="text-[11px] text-slate-400">{f.window}</span>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-sm font-bold text-slate-900">{fmtInt(f.current)}</div>
                        <div className={`text-xs font-semibold ${down ? 'text-red-600' : 'text-emerald-600'}`}>
                          {f.change_pct !== null ? `${sign}${f.change_pct.toFixed(1)}%` : 'new'}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        ) : (
          <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-10 text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
              <FileText className="w-6 h-6 text-slate-400" />
            </div>
            <h2 className="text-base font-semibold text-slate-900">No briefing yet</h2>
            <p className="text-sm text-slate-500 mt-1">
              Click <span className="font-medium">Generate Briefing</span> to run the anomaly scan now.
            </p>
          </div>
        )}

        {dash!.schema && dash!.schema.tables.length > 0 && (
          <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-[15px] font-semibold text-slate-900">
                Database schema ({dash!.schema.table_count} tables)
              </h2>
            </div>
            <div className="px-6 py-4 flex flex-wrap gap-2">
              {dash!.schema.tables.map((t) => (
                <span key={t} className="text-xs font-medium text-slate-600 bg-slate-100 rounded-lg px-2.5 py-1">
                  {t}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}