import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Styled markdown renderer used for briefing summaries and chat answers.
 * Renders headings, bold/italic, lists, links, code blocks, and tables
 * with the app's design language instead of raw markdown text.
 */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown-body text-[15px] leading-relaxed text-slate-700">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-slate-900 mt-6 mb-3 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold text-slate-900 mt-6 mb-2 first:mt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold text-slate-900 mt-5 mb-2 first:mt-0">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-semibold text-slate-900 mt-4 mb-1 first:mt-0">{children}</h4>
          ),
          p: ({ children }) => <p className="my-3 first:mt-0 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => (
            <ul className="list-disc pl-6 my-3 space-y-1.5 marker:text-slate-400">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-6 my-3 space-y-1.5 marker:text-slate-400">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-brand-600 font-medium hover:text-brand-700 hover:underline"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-brand-200 bg-brand-50/60 rounded-r-lg px-4 py-2 my-3 text-slate-600">
              {children}
            </blockquote>
          ),
          code: ({ className, children }) => {
            const isBlock = /language-/.test(className || '');
            if (isBlock) {
              return (
                <pre className="bg-slate-900 text-slate-100 rounded-xl p-4 my-3 overflow-x-auto text-[13px] leading-relaxed font-mono">
                  <code className={className}>{children}</code>
                </pre>
              );
            }
            return (
              <code className="bg-slate-100 text-slate-800 rounded-md px-1.5 py-0.5 text-[13px] font-mono border border-slate-200">
                {children}
              </code>
            );
          },
          pre: ({ children }) => <>{children}</>,
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-xl border border-slate-200">
              <table className="w-full text-sm divide-y divide-slate-200">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-slate-50 text-slate-600 text-left text-xs uppercase tracking-wide">
              {children}
            </thead>
          ),
          th: ({ children }) => <th className="px-4 py-2.5 font-semibold">{children}</th>,
          td: ({ children }) => <td className="px-4 py-2.5 border-t border-slate-100">{children}</td>,
          hr: () => <hr className="my-6 border-slate-200" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}