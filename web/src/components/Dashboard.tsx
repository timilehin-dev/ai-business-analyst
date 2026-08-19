import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, AlertTriangle, CheckCircle, ArrowRight, Plus } from 'lucide-react';

const mockBriefings = [
  {
    id: 1,
    type: 'critical',
    title: 'Churn Spike Detected in EMEA',
    summary: 'Churn increased by 23% in the EMEA segment over the last 48 hours. Root cause traced to pricing changes on Aug 12.',
    timestamp: '2 hours ago',
    metric: 'Churn Rate',
    change: '+23%',
    status: 'investigating'
  },
  {
    id: 2,
    type: 'positive',
    title: 'Q3 Revenue Tracking Above Forecast',
    summary: 'Revenue is tracking 8% above forecast driven by enterprise renewals. On track to beat Q3 targets.',
    timestamp: '5 hours ago',
    metric: 'Revenue',
    change: '+8%',
    status: 'verified'
  },
  {
    id: 3,
    type: 'neutral',
    title: 'Data Freshness Warning',
    summary: 'Stripe connector has not synced new data in 6 hours. Automated retry initiated.',
    timestamp: '1 hour ago',
    metric: 'Data Health',
    change: '-6h',
    status: 'auto-fixing'
  }
];

const mockKPIs = [
  { name: 'Total Revenue', value: '$2.4M', change: '+12%', trend: 'up' },
  { name: 'Active Users', value: '14,205', change: '+5%', trend: 'up' },
  { name: 'Churn Rate', value: '2.1%', change: '-0.4%', trend: 'down' },
  { name: 'CAC', value: '$450', change: '+2%', trend: 'up' },
];

export default function Dashboard() {
  const [briefings, setBriefings] = useState(mockBriefings);
  const [kpis, setKpis] = useState(mockKPIs);

  const getIcon = (type) => {
    switch (type) {
      case 'critical': return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'positive': return <CheckCircle className="h-5 w-5 text-green-500" />;
      default: return <Activity className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'verified': return 'bg-green-100 text-green-800';
      case 'investigating': return 'bg-blue-100 text-blue-800';
      case 'auto-fixing': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Good Morning, Team</h1>
          <p className="text-gray-500">Here is what I found while you were sleeping.</p>
        </div>
        <button className="gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center">
          <Plus className="h-4 w-4" /> New Analysis
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.name} className="border rounded-lg bg-white shadow-sm">
            <div className="flex flex-row items-center justify-between space-y-0 p-6 pb-2">
              <span className="text-sm font-medium">{kpi.name}</span>
              {kpi.trend === 'up' ? (
                <TrendingUp className="h-4 w-4 text-gray-400" />
              ) : (
                <Activity className="h-4 w-4 text-gray-400" />
              )}
            </div>
            <div className="p-6 pt-0">
              <div className="text-2xl font-bold">{kpi.value}</div>
              <p className={kpi.change.startsWith('+') ? 'text-green-600 text-xs' : 'text-red-600 text-xs'}>{
                kpi.change} from last month
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Overnight Briefing</h2>
        {briefings.map((brief) => (
          <div key={brief.id} className="hover:shadow-md transition-shadow cursor-pointer border rounded-lg bg-white">
            <div className="flex flex-row items-start justify-between space-y-0 p-6">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-3">
                  {getIcon(brief.type)}
                  <div>
                    <span className="text-lg font-semibold">{brief.title}</span>
                    <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                      <span>{brief.timestamp}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(brief.status)}`}>
                        {brief.status.replace('-', ' ')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-gray-400" />
            </div>
            <div className="p-6 pt-0">
              <p className="text-gray-600">{brief.summary}</p>
              <div className="mt-4 flex gap-2">
                <button className="text-sm px-4 py-2 border rounded-md hover:bg-gray-50">View Full Analysis</button>
                <button className="text-sm px-4 py-2 text-gray-600 hover:text-gray-900">Ask Follow-up</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}