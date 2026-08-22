import { Link, useLocation } from 'react-router-dom';
import { Brain, LayoutDashboard, MessageSquare, Database, Moon, Settings } from 'lucide-react';

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/data', label: 'Data Sources', icon: Database },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-slate-900 text-slate-300 flex flex-col fixed inset-y-0 left-0">
        {/* Logo */}
        <div className="px-5 h-16 flex items-center gap-3 border-b border-slate-800">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-900/40">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold text-white tracking-tight">AI Business Analyst</div>
            <div className="text-[11px] text-slate-500">Autonomous insights</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {links.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-brand-600/15 text-white ring-1 ring-inset ring-brand-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Icon className={`w-[18px] h-[18px] ${active ? 'text-brand-400' : ''}`} />
                {label}
                {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-400" />}
              </Link>
            );
          })}
        </nav>

        {/* Footer status */}
        <div className="px-5 py-4 border-t border-slate-800">
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            Sense loop active · 06:00 UTC
          </div>
          <div className="mt-1.5 text-[11px] text-slate-600 flex items-center gap-1.5">
            <Moon className="w-3 h-3" /> Nightly briefing scheduled
          </div>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 ml-60">
        <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}