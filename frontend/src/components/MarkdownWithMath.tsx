/**
 * Renders markdown with LaTeX math support.
 * Uses react-markdown + remark-math + rehype-katex for textbook-quality math.
 *
 * Supports all common LLM math syntax:
 * - Inline: $...$ or \(...\)
 * - Block: $$...$$ or \[...\]
 *
 * remark-math only understands $ and $$; we preprocess \[...\] and \(...\)
 * into that format. Same-line $$...$$ is converted to multi-line format.
 */

import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

type Props = {
  children: string;
  className?: string;
};

/** Normalize all math delimiters to $ and $$ for remark-math */
function normalizeMath(text: string): string {
  let out = text;
  // \[...\] (LaTeX display) -> $$...$$ with newlines for remark-math
  out = out.replace(/\\\[([\s\S]*?)\\\]/g, "$$\n$1\n$$");
  // \(...\) (LaTeX inline) -> $...$
  out = out.replace(/\\\((.+?)\\\)/g, "$$1$");
  // Same-line $$...$$ -> multi-line (remark-math requires $$ on its own line)
  out = out.replace(/\$\$([^\n$]*?)\$\$/g, "$$\n$1\n$$");
  return out;
}

export function MarkdownWithMath({ children, className }: Props) {
  const normalized = typeof children === "string" ? normalizeMath(children) : "";
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="list-disc list-inside my-2 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside my-2 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="ml-2">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          code: ({ className, children, ...props }) => {
            const isMath = className?.includes("math");
            if (isMath) return <span {...props}>{children}</span>;
            return (
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
}
