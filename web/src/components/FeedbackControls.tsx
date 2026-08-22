import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check, Loader2, Lightbulb } from 'lucide-react';
import { api } from '../lib/api';

/**
 * Feedback on one analysis.
 *
 * A thumbs-down opens a correction box, because a negative rating with a
 * written correction is what the backend promotes into a standing rule —
 * a bare downvote records dissatisfaction but teaches nothing.
 */
export default function FeedbackControls({ episodeId }: { episodeId: number }) {
  const [rating, setRating] = useState<number | null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correction, setCorrection] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ruleCreated: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (value: number, text?: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.post<{ rule_created: boolean }>('/api/feedback', {
        episode_id: episodeId,
        rating: value,
        correction: text || null,
      });
      setRating(value);
      setResult({ ruleCreated: response.rule_created });
      setShowCorrection(false);
    } catch (e: any) {
      setError(e.message || 'Could not save feedback');
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-600 bg-emerald-50 rounded-full px-2.5 py-1">
        <Check className="w-3 h-3" />
        {result.ruleCreated ? 'Saved — now a standing instruction' : 'Feedback saved'}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => submit(5)}
          disabled={submitting}
          title="This answer was correct"
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-600 rounded-full px-2.5 py-1 transition-colors disabled:opacity-50"
        >
          {submitting && rating === 5 ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <ThumbsUp className="w-3 h-3" />
          )}
          Helpful
        </button>
        <button
          onClick={() => setShowCorrection((v) => !v)}
          disabled={submitting}
          title="Tell the analyst what it got wrong"
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-amber-50 hover:text-amber-600 rounded-full px-2.5 py-1 transition-colors disabled:opacity-50"
        >
          <ThumbsDown className="w-3 h-3" />
          Needs work
        </button>
      </div>

      {showCorrection && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
          <label className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-800 mb-2">
            <Lightbulb className="w-3.5 h-3.5" />
            What should it do differently next time?
          </label>
          <textarea
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            rows={2}
            placeholder="e.g. Always exclude test accounts from revenue totals"
            className="w-full text-[13px] rounded-lg border border-amber-200 bg-white px-3 py-2 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400/40"
          />
          <p className="text-[11px] text-amber-700 mt-1.5">
            Saved corrections become standing instructions applied to every future analysis.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={() => submit(2, correction)}
              disabled={submitting || !correction.trim()}
              className="inline-flex items-center gap-1.5 text-[11px] font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-40"
            >
              {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
              Save correction
            </button>
            <button
              onClick={() => submit(2)}
              disabled={submitting}
              className="text-[11px] font-medium text-amber-700 hover:text-amber-900 px-2 py-1.5"
            >
              Just downvote
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-[11px] text-rose-600">{error}</p>}
    </div>
  );
}
