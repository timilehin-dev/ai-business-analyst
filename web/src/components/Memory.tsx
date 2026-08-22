import { useEffect, useState } from 'react';
import {
  BookOpen,
  ShieldCheck,
  History,
  ScrollText,
  Plus,
  Trash2,
  Loader2,
  Sparkles,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import AppShell from './AppShell';
import { api, AuditEntry, Episode, GlossaryTerm, ProceduralRule } from '../lib/api';

type Tab = 'glossary' | 'rules' | 'history' | 'audit';

const TABS: { id: Tab; label: string; icon: typeof BookOpen }[] = [
  { id: 'glossary', label: 'Glossary', icon: BookOpen },
  { id: 'rules', label: 'Standing Instructions', icon: ShieldCheck },
  { id: 'history', label: 'Past Analyses', icon: History },
  { id: 'audit', label: 'Audit Log', icon: ScrollText },
];

export default function Memory() {
  const [tab, setTab] = useState<Tab>('glossary');

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Memory</h1>
        <p className="text-sm text-slate-500 mt-1">
          What the analyst has learned about your business — and everything it has done.
        </p>
      </div>

      <div className="flex items-center gap-1 mb-6 border-b border-slate-200">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === id
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'glossary' && <GlossaryPanel />}
      {tab === 'rules' && <RulesPanel />}
      {tab === 'history' && <HistoryPanel />}
      {tab === 'audit' && <AuditPanel />}
    </AppShell>
  );
}

/* ------------------------------------------------------------------ */

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-card p-5">{children}</div>
  );
}

function Empty({ message }: { message: string }) {
  return <p className="text-sm text-slate-400 py-6 text-center">{message}</p>;
}

function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="text-sm text-rose-600 mt-2">{error}</p>;
}

/* ------------------------------------------------------------------ */

function GlossaryPanel() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [term, setTerm] = useState('');
  const [definition, setDefinition] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api
      .get<{ terms: GlossaryTerm[] }>('/api/memory/glossary')
      .then((d) => setTerms(d.terms))
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const add = async () => {
    if (!term.trim() || !definition.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.post('/api/memory/glossary', { term: term.trim(), definition: definition.trim() });
      setTerm('');
      setDefinition('');
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post('/api/memory/glossary/generate');
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    try {
      await api.del(`/api/memory/glossary/${id}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Define a business term</h2>
            <p className="text-xs text-slate-500 mt-1">
              Definitions are injected into every analysis, so the analyst uses your meaning of
              &ldquo;active customer&rdquo; rather than guessing.
            </p>
          </div>
          <button
            onClick={generate}
            disabled={busy}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg px-3 py-2 transition-colors disabled:opacity-50 flex-shrink-0"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Generate from schema
          </button>
        </div>
        <div className="grid gap-2 sm:grid-cols-[minmax(0,200px)_1fr_auto]">
          <input
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Term (e.g. ARR)"
            className="px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
          />
          <input
            value={definition}
            onChange={(e) => setDefinition(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="Definition"
            className="px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
          />
          <button
            onClick={add}
            disabled={busy || !term.trim() || !definition.trim()}
            className="inline-flex items-center justify-center gap-1.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-xl px-4 py-2 transition-colors disabled:opacity-40"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
        <ErrorNote error={error} />
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-slate-900 mb-3">
          Glossary ({terms.length})
        </h2>
        {terms.length === 0 ? (
          <Empty message="No terms yet. Add one above or generate them from your schema." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {terms.map((t) => (
              <li key={t.id} className="py-3 flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900">{t.term}</span>
                    <span className="text-[10px] uppercase tracking-wide text-slate-400 bg-slate-100 rounded px-1.5 py-0.5">
                      {t.source}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mt-0.5">{t.definition}</p>
                </div>
                <button
                  onClick={() => remove(t.id)}
                  className="text-slate-400 hover:text-rose-600 transition-colors flex-shrink-0"
                  title="Delete term"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function RulesPanel() {
  const [rules, setRules] = useState<ProceduralRule[]>([]);
  const [rule, setRule] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api
      .get<{ rules: ProceduralRule[] }>('/api/memory/rules')
      .then((d) => setRules(d.rules))
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const add = async () => {
    if (!rule.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.post('/api/memory/rules', { rule: rule.trim() });
      setRule('');
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const deactivate = async (id: number) => {
    try {
      await api.del(`/api/memory/rules/${id}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-5">
      <Card>
        <h2 className="text-sm font-semibold text-slate-900">Add a standing instruction</h2>
        <p className="text-xs text-slate-500 mt-1 mb-3">
          Applied to every future analysis. Corrections you submit on an answer land here
          automatically.
        </p>
        <div className="flex gap-2">
          <input
            value={rule}
            onChange={(e) => setRule(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="e.g. Always exclude test accounts from revenue"
            className="flex-1 px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
          />
          <button
            onClick={add}
            disabled={busy || !rule.trim()}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-xl px-4 py-2 transition-colors disabled:opacity-40"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
        <ErrorNote error={error} />
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Instructions ({rules.length})</h2>
        {rules.length === 0 ? (
          <Empty message="No standing instructions yet." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {rules.map((r) => (
              <li key={r.id} className="py-3 flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p
                    className={`text-sm ${
                      r.active ? 'text-slate-800' : 'text-slate-400 line-through'
                    }`}
                  >
                    {r.rule}
                  </p>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                    <span>Applied {r.times_applied}×</span>
                    {r.source_episode_id && <span>· from your correction</span>}
                    {!r.active && <span>· inactive</span>}
                  </div>
                </div>
                {r.active && (
                  <button
                    onClick={() => deactivate(r.id)}
                    className="text-xs font-medium text-slate-500 hover:text-rose-600 transition-colors flex-shrink-0"
                  >
                    Deactivate
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function HistoryPanel() {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<{ episodes: Episode[] }>('/api/memory/episodes?limit=50')
      .then((d) => setEpisodes(d.episodes))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-900 mb-3">
        Past analyses ({episodes.length})
      </h2>
      <ErrorNote error={error} />
      {episodes.length === 0 ? (
        <Empty message="No analyses recorded yet. Ask a question in Chat." />
      ) : (
        <ul className="divide-y divide-slate-100">
          {episodes.map((e) => (
            <li key={e.id} className="py-3">
              <div className="flex items-start justify-between gap-4">
                <p className="text-sm font-medium text-slate-800">{e.question}</p>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {e.confidence != null && (
                    <span className="text-[11px] text-slate-500 bg-slate-100 rounded-full px-2 py-0.5">
                      {Math.round(e.confidence * 100)}%
                    </span>
                  )}
                  {e.rating != null && (
                    <span
                      className={`text-[11px] rounded-full px-2 py-0.5 ${
                        e.rating > 3
                          ? 'bg-emerald-50 text-emerald-600'
                          : 'bg-amber-50 text-amber-600'
                      }`}
                    >
                      rated {e.rating}/5
                    </span>
                  )}
                </div>
              </div>
              {e.correction && (
                <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-2.5 py-1.5 mt-2">
                  Correction: {e.correction}
                </p>
              )}
              {e.sql_query && (
                <pre className="text-[11px] font-mono text-slate-500 bg-slate-50 rounded-lg px-2.5 py-1.5 mt-2 overflow-x-auto">
                  {e.sql_query}
                </pre>
              )}
              <p className="text-[11px] text-slate-400 mt-1.5">
                {e.timestamp ? new Date(e.timestamp).toLocaleString() : ''}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ */

function AuditPanel() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<{ entries: AuditEntry[] }>('/api/audit?limit=200')
      .then((d) => setEntries(d.entries))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-900 mb-1">Audit log</h2>
      <p className="text-xs text-slate-500 mb-3">
        Append-only record of analyses, configuration changes, syncs, and feedback.
      </p>
      <ErrorNote error={error} />
      {entries.length === 0 ? (
        <Empty message="No audit entries yet." />
      ) : (
        <div className="max-h-[32rem] overflow-y-auto">
          <ul className="divide-y divide-slate-100">
            {entries.map((entry) => (
              <li key={entry.id} className="py-2.5 flex items-start gap-3">
                {entry.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <code className="text-xs font-semibold text-slate-800">{entry.action}</code>
                    <span className="text-[10px] uppercase tracking-wide text-slate-400 bg-slate-100 rounded px-1.5 py-0.5">
                      {entry.actor}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : ''}
                    </span>
                  </div>
                  {Object.keys(entry.detail || {}).length > 0 && (
                    <pre className="text-[11px] font-mono text-slate-500 mt-1 overflow-x-auto">
                      {JSON.stringify(entry.detail)}
                    </pre>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
