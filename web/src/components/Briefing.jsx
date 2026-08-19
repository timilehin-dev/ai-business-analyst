import { TrendingUp, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';

export default function Briefing() {
  const findings = [
    {
      id: 1,
      urgency: 'high',
      title: 'Churn spiked 23% in EMEA segment',
      summary: 'Traced to pricing change on Aug 12. Enterprise customers most affected.',
      trend: 'down',
      metric: '-23%',
    },
    {
      id: 2,
      urgency: 'positive',
      title: 'Q3 revenue tracking 8% above forecast',
      summary: 'Driver: enterprise renewals exceeding expectations by 34%.',
      trend: 'up',
      metric: '+8%',
    },
    {
      id: 3,
      urgency: 'medium',
      title: '3 metrics need your input',
      summary: 'Unusual patterns detected in customer acquisition cost, LTV, and support tickets.',
      trend: 'neutral',
      metric: '?',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-900">Morning Briefing</h1>
          <nav className="flex gap-4">
            <a href="/dashboard" className="text-slate-600 hover:text-slate-900">Chat</a>
            <a href="/briefing" className="text-blue-600 font-medium">Briefing</a>
          </nav>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Greeting */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-900">Good morning! Here's what I found overnight:</h2>
          <p className="text-slate-600 mt-2">3 insights require your attention</p>
        </div>

        {/* Findings */}
        <div className="space-y-4 mb-8">
          {findings.map((finding) => (
            <div key={finding.id} className="bg-white border border-slate-200 rounded-lg p-6 hover:shadow-md transition cursor-pointer">
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                  finding.urgency === 'high' ? 'bg-red-100 text-red-600' :
                  finding.urgency === 'positive' ? 'bg-green-100 text-green-600' :
                  'bg-yellow-100 text-yellow-600'
                }`}>
                  {finding.urgency === 'high' ? <AlertTriangle className="w-6 h-6" /> :
                   finding.urgency === 'positive' ? <TrendingUp className="w-6 h-6" /> :
                   <CheckCircle className="w-6 h-6" />}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-slate-900">{finding.title}</h3>
                    <span className={`text-2xl font-bold ${
                      finding.trend === 'up' ? 'text-green-600' :
                      finding.trend === 'down' ? 'text-red-600' :
                      'text-slate-600'
                    }`}>
                      {finding.metric}
                    </span>
                  </div>
                  <p className="text-slate-600 mt-2">{finding.summary}</p>
                  <button className="mt-4 flex items-center text-blue-600 font-medium hover:underline">
                    View full analysis <ArrowRight className="w-4 h-4 ml-1" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Watched KPIs */}
        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Your Watched KPIs</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { name: 'Revenue', trend: [1, 3, 2, 4, 5, 7, 6], change: '+12%' },
              { name: 'Churn', trend: [7, 6, 5, 4, 3, 2, 1], change: '-8%' },
              { name: 'NPS', trend: [2, 3, 4, 3, 5, 4, 5], change: '+5' },
            ].map((kpi) => (
              <div key={kpi.name} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-slate-600">{kpi.name}</span>
                  <span className={`text-sm font-bold ${
                    kpi.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {kpi.change}
                  </span>
                </div>
                <div className="h-16 flex items-end gap-1">
                  {kpi.trend.map((val, idx) => (
                    <div
                      key={idx}
                      className="flex-1 bg-blue-500 rounded-t"
                      style={{ height: `${(val / 7) * 100}%` }}
                    />
                  ))}
                </div>
              </div>
            ))}
            <button className="border-2 border-dashed border-slate-300 rounded-lg p-4 flex items-center justify-center text-slate-500 hover:border-blue-500 hover:text-blue-600 transition">
              + Add KPI
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
