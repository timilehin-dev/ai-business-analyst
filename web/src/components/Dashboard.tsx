import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Sparkles, RefreshCw } from 'lucide-react';
import Nav from './Nav';

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

  useEffect(() => { load(); }, []);

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

  const getIcon = (f: Finding) => {
    if (f.severity === 'critical') return <AlertTriangle className="h-5 w-5 text-red-500" />;
    if (f.direction === 'up') return <TrendingUp className="h-5 w-5 text-green-500" />;
    if (f.direction === 'down') return <TrendingDown className="h-5 w-5 text-red-500" />;
    return <Activity className="h-5 w-5 text-yellow-500" />;
  };

  const formatNumber = (n: number) => {
    if (Math.abs(n) >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  };

  const formatChange = (f: Finding) => {
    if (f.change_pct === null) return 'new activity';
    const sign = f.change_pct > 0 ? '+' : '';
    return `${sign}${f.change_pct.toFixed(1)}%`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav />
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Good Morning, Team</h1>
            <p className="text-gray-500">Here is what I found while you were sleeping.</p>
          </div>
          <button
            onClick={generateNow}
            disabled={generating}
            className="gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center disabled:opacity-50"
          >
            {generating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {generating ? 'Analyzing...' : 'Generate Briefing Now'}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20 text-gray-400">
            <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading briefing...
          </div>
        ) : !briefing ? (
          <div className="border rounded-lg bg-white shadow-sm p-12 text-center">
            <CheckCircle className="h-10 w-10 text-gray-300 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-700">No briefing yet</h2>
            <p className="text-gray-500 mt-2 max-w-md mx-auto">
              The Sense loop runs automatically every night at 6 AM — it scans your
              database for anomalies and writes a briefing. Click "Generate Briefing Now"
              to run it immediately.
            </p>
          </div>
        ) : (
          <>
            {/* KPI cards from the latest findings */}
            {briefing.findings.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {briefing.findings.slice(0, 4).map((f, i) => (
                  <div key={i} className="border rounded-lg bg-white shadow-sm">
                    <div className="flex flex-row items-center justify-between space-y-0 p-6 pb-2">
                      <span className="text-sm font-medium capitalize">
                        {f.metric === '__row_count__' ? `${f.table} rows` : f.metric.replace(/_/g, ' ')}
                      </span>
                      {getIcon(f)}
                    </div>
                    <div className="p-6 pt-0">
                      <div className="text-2xl font-bold">{formatNumber(f.current)}</div>
                      <p className={`text-xs ${f.direction === 'down' && f.severity === 'critical' ? 'text-red-600' : 'text-green-600'}`}>
                        {formatChange(f)} vs prior period
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Briefing summary */}
            <div className="border rounded-lg bg-white shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">Overnight Briefing</h2>
                <span className="text-xs text-gray-400">
                  {briefing.generated_at ? new Date(briefing.generated_at).toLocaleString() : ''}
                </span>
              </div>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {briefing.summary}
              </div>
            </div>

            {/* Findings detail */}
            {briefing.findings.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xl font-semibold">Detected Anomalies</h2>
                {briefing.findings.map((f, i) => (
                  <div key={i} className="hover:shadow-md transition-shadow border rounded-lg bg-white">
                    <div className="flex flex-row items-start justify-between space-y-0 p-6">
                      <div className="flex items-center space-x-3">
                        {getIcon(f)}
                        <div>
                          <span className="text-lg font-semibold capitalize">
                            {f.metric === '__row_count__' ? `${f.table} volume` : `${f.table} · ${f.metric.replace(/_/g, ' ')}`}
                          </span>
                          <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                            <span>{f.window}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              f.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                            }`}>
                              {f.severity}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold">{formatNumber(f.current)}</div>
                        <div className="text-xs text-gray-500">vs {formatNumber(f.previous)}</div>
                        <div className={`text-sm font-medium ${f.direction === 'down' ? 'text-red-600' : 'text-green-600'}`}>
                          {formatChange(f)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}