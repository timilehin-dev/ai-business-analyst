import { useState, useEffect, useCallback } from 'react';
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
  ShoppingCart,
  Users,
  Package,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import AppShell from './AppShell';
import Markdown from './Markdown';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface DashboardMetrics {
  revenue: number;
  revenue_30d: number;
  revenue_prev_30d: number;
  total_orders: number;
  total_customers: number;
  total_products: number;
  active_customers: number;
}

interface Category {
  category: string;
  revenue: number;
  order_count: number;
}

interface Trend {
  day: string;
  orders: number;
  revenue: number;
}

interface RecentOrder {
  id: number;
  ordered_at: string;
  status: string;
  quantity: number;
  unit_price: number;
  total: number;
  customer_name: string;
  product_name: string;
}

interface TopCustomer {
  name: string;
  revenue: number;
  orders: number;
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
  metrics: DashboardMetrics;
  categories: Category[];
  trends: Trend[];
  recent_orders: RecentOrder[];
  top_customers: TopCustomer[];
  message?: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
const fmt = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
};

const fmtInt = (n: number) => n.toLocaleString();

const pctChange = (curr: number, prev: number) => {
  if (prev === 0) return curr > 0 ? 100 : 0;
  return ((curr - prev) / prev) * 100;
};

const statusColor = (s: string) => {
  if (s === 'Completed') return 'bg-emerald-50 text-emerald-700';
  if (s === 'Pending') return 'bg-amber-50 text-amber-700';
  if (s === 'Cancelled') return 'bg-red-50 text-red-600';
  return 'bg-slate-100 text-slate-600';
};

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
      const dashData = await dashRes.json();
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
    // Auto-refresh every 5 minutes
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
  // Growth compares the last 30 days against the prior 30 days (backend
  // provides both windows explicitly — the all-time total stayed as display)
  const revenueGrowth = m ? pctChange(m.revenue_30d, m.revenue_prev_30d) : 0;

  /* ---- KPI card config ---- */
  const kpis = m
    ? [
        { label: 'Total Revenue', value: fmt(m.revenue), icon: DollarSign, change: revenueGrowth, color: 'brand' },
        { label: 'Total Orders', value: fmtInt(m.total_orders), icon: ShoppingCart, change: null, color: 'slate' },
        { label: 'Customers', value: fmtInt(m.total_customers), icon: Users, change: null, color: 'slate' },
        { label: 'Active (30d)', value: fmtInt(m.active_customers), icon: Activity, change: null, color: 'emerald' },
      ]
    : [];

  return (
    <AppShell>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            {today} · Live data from your database.
            {lastRefresh && (
              <span className="ml-2 text-slate-400">
                Updated {lastRefresh.toLocaleTimeString()}
              </span>
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

      {loading && !dash ? (
        <div className="flex items-center justify-center py-32 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading dashboard…
        </div>
      ) : dash?.status === 'no_database' ? (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-16 text-center">
          <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-slate-100 flex items-center justify-center">
            <BarChart3 className="w-7 h-7 text-slate-400" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">No database connected</h2>
          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
            Run the setup wizard to connect your organization's database. Once connected,
            this dashboard will show live business metrics in real time.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* ---- KPI Row ---- */}
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

          {/* ---- Two-column: Categories + Top Customers ---- */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Revenue by Category */}
            {dash!.categories.length > 0 && (
              <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h2 className="text-[15px] font-semibold text-slate-900">Revenue by Category</h2>
                </div>
                <div className="divide-y divide-slate-100">
                  {dash!.categories.map((cat, i) => {
                    const maxRev = dash!.categories[0].revenue;
                    const pct = maxRev > 0 ? (cat.revenue / maxRev) * 100 : 0;
                    return (
                      <div key={i} className="px-6 py-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium text-slate-700 capitalize">{cat.category}</span>
                          <span className="text-sm font-semibold text-slate-900">{fmt(cat.revenue)}</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5">
                          <div
                            className="bg-brand-500 h-1.5 rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-400">{cat.order_count} orders</span>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Top Customers */}
            {dash!.top_customers.length > 0 && (
              <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h2 className="text-[15px] font-semibold text-slate-900">Top Customers</h2>
                </div>
                <div className="divide-y divide-slate-100">
                  {dash!.top_customers.map((c, i) => (
                    <div key={i} className="px-6 py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center text-brand-700 text-xs font-bold">
                          {c.name?.charAt(0) || '?'}
                        </div>
                        <div>
                          <span className="text-sm font-medium text-slate-700">{c.name}</span>
                          <p className="text-[11px] text-slate-400">{c.orders} orders</p>
                        </div>
                      </div>
                      <span className="text-sm font-semibold text-slate-900">{fmt(c.revenue)}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* ---- Daily Trend ---- */}
          {dash!.trends.length > 0 && (
            <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">Daily Revenue Trend (30 days)</h2>
              </div>
              <div className="px-6 py-4">
                <div className="flex items-end gap-1 h-32">
                  {dash!.trends.map((t, i) => {
                    const maxRev = Math.max(...dash!.trends.map((x) => x.revenue));
                    const height = maxRev > 0 ? (t.revenue / maxRev) * 100 : 0;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                        <div
                          className="w-full bg-brand-400 rounded-t hover:bg-brand-600 transition-colors min-h-[2px]"
                          style={{ height: `${height}%` }}
                        />
                        {/* Tooltip */}
                        <div className="hidden group-hover:block absolute bottom-full mb-2 bg-slate-900 text-white text-[11px] px-2 py-1 rounded-lg whitespace-nowrap z-10">
                          {t.day}: {fmt(t.revenue)} ({t.orders} orders)
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

          {/* ---- Recent Orders ---- */}
          {dash!.recent_orders.length > 0 && (
            <section className="bg-white border border-slate-200 rounded-2xl shadow-card overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">Recent Orders</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-[12px] font-medium text-slate-500 uppercase tracking-wide">
                      <th className="px-6 py-3">Order</th>
                      <th className="px-6 py-3">Customer</th>
                      <th className="px-6 py-3">Product</th>
                      <th className="px-6 py-3 text-right">Qty</th>
                      <th className="px-6 py-3 text-right">Total</th>
                      <th className="px-6 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {dash!.recent_orders.map((o, i) => (
                      <tr key={i} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-3 font-medium text-slate-900">#{o.id}</td>
                        <td className="px-6 py-3 text-slate-600">{o.customer_name || '—'}</td>
                        <td className="px-6 py-3 text-slate-600">{o.product_name || '—'}</td>
                        <td className="px-6 py-3 text-right text-slate-600">{o.quantity}</td>
                        <td className="px-6 py-3 text-right font-medium text-slate-900">{fmt(o.total)}</td>
                        <td className="px-6 py-3">
                          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${statusColor(o.status)}`}>
                            {o.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ---- Briefing Section ---- */}
          {briefing && (
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

              {/* Anomaly findings */}
              {briefing.findings.length > 0 && (
                <div className="px-6 pb-5 space-y-3">
                  <h3 className="text-[13px] font-semibold text-slate-700">Detected Anomalies</h3>
                  {briefing.findings.map((f, i) => {
                    const critical = f.severity === 'critical';
                    const down = f.direction === 'down';
                    const sign = f.change_pct !== null ? (f.change_pct > 0 ? '+' : '') : '';
                    return (
                      <div
                        key={i}
                        className="flex items-center justify-between gap-4 p-4 bg-slate-50 rounded-xl"
                      >
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
          )}

          {/* No briefing */}
          {!briefing && (
            <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-10 text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
                <FileText className="w-6 h-6 text-slate-400" />
              </div>
              <h2 className="text-base font-semibold text-slate-900">No briefing yet</h2>
              <p className="text-sm text-slate-500 mt-1">
                The Sense loop runs nightly at 6 AM. Click <span className="font-medium">Generate Briefing</span> to run it now.
              </p>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
