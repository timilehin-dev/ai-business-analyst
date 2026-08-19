import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, AlertTriangle, CheckCircle, ArrowRight, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// Mock data for demonstration - will be replaced by API calls
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
    summary: 'Stripe connector hasn\'t synced new data in 6 hours. Automated retry initiated.',
    timestamp: '1 hour ago',
    metric: 'Data Health',
    change: '-6h',
    status: 'auto-fixing'
  }
];

const mockKPIs = [
  { name: 'Total Revenue', value: '$2.4M', change: '+12%', trend: 'up' },
  { name: 'Active Users', value: '14,205', change: '+5%', trend: 'up' },
  { name: 'Churn Rate', value: '2.1%', change: '-0.4%', trend: 'down' }, // down is good for churn
  { name: 'CAC', value: '$450', change: '+2%', trend: 'up' }, // up is bad for CAC
];

export default function Dashboard() {
  const [briefings, setBriefings] = useState(mockBriefings);
  const [kpis, setKpis] = useState(mockKPIs);

  const getIcon = (type: string) => {
    switch (type) {
      case 'critical': return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'positive': return <CheckCircle className="h-5 w-5 text-green-500" />;
      default: return <Activity className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified': return 'bg-green-100 text-green-800';
      case 'investigating': return 'bg-blue-100 text-blue-800';
      case 'auto-fixing': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Good Morning, Team</h1>
          <p className="text-muted-foreground">Here's what I found while you were sleeping.</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" /> New Analysis
        </Button>
      </div>

      {/* KPI Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <Card key={kpi.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{kpi.name}</CardTitle>
              {kpi.trend === 'up' ? (
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Activity className="h-4 w-4 text-muted-foreground" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <p className={`text-xs ${kpi.change.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                {kpi.change} from last month
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Briefing Feed */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Overnight Briefing</h2>
        {briefings.map((brief) => (
          <Card key={brief.id} className="hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div className="flex items-center space-x-3">
                {getIcon(brief.type)}
                <div>
                  <CardTitle className="text-lg">{brief.title}</CardTitle>
                  <CardDescription className="flex items-center gap-2 mt-1">
                    <span>{brief.timestamp}</span>
                    <Badge className={getStatusColor(brief.status)}>
                      {brief.status.replace('-', ' ')}
                    </Badge>
                  </CardDescription>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">{brief.summary}</p>
              <div className="mt-4 flex gap-2">
                <Button variant="outline" size="sm">View Full Analysis</Button>
                <Button variant="ghost" size="sm">Ask Follow-up</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
