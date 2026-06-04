import { Check, Copy, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';

const ANALYSIS_STEPS = [
  { icon: "📄", text: "Reading resume" },
  { icon: "", text: "Comparing with job description" },
  { icon: "", text: "Checking keyword matches" },
  { icon: "", text: "Evaluating experience fit" },
  { icon: "", text: "Preparing insights" },
];

const escapeHtml = (value) =>
  String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const renderInlineMarkdown = (value) =>
  escapeHtml(value).replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');

export const markdownToHtml = (markdown) => {
  const lines = String(markdown || '').split(/\r?\n/);
  const html = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      html.push('</ul>');
      inList = false;
    }
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      return;
    }

    if (line.startsWith('## ')) {
      closeList();
      html.push(`<h4 class="mt-4 first:mt-0 text-[15px] font-semibold leading-snug text-gray-900">${renderInlineMarkdown(line.slice(3))}</h4>`);
      return;
    }

    if (line.startsWith('### ')) {
      closeList();
      html.push(`<h5 class="mt-2 first:mt-0 text-xs font-medium text-gray-600">${renderInlineMarkdown(line.slice(4))}</h5>`);
      return;
    }

    if (line.startsWith('- ')) {
      if (!inList) {
        html.push('<ul class="mt-2 space-y-1.5 pl-4 list-disc">');
        inList = true;
      }
      html.push(`<li class="text-sm leading-relaxed text-gray-600">${renderInlineMarkdown(line.slice(2))}</li>`);
      return;
    }

    closeList();
    html.push(`<p class="mt-2 first:mt-0 text-sm leading-relaxed text-gray-600">${renderInlineMarkdown(line)}</p>`);
  });

  closeList();
  return html.join('');
};

const sleep = (duration) => new Promise((resolve) => {
  window.setTimeout(resolve, duration);
});

const useStreamingMarkdown = (markdown, { enabled = true, speed = 45 } = {}) => {
  const [streamState, setStreamState] = useState(() => ({
    source: String(markdown || ''),
    visible: enabled ? '' : String(markdown || ''),
  }));

  useEffect(() => {
    const fullText = String(markdown || '');
    if (!enabled || !fullText) {
      setStreamState({ source: fullText, visible: fullText });
      return undefined;
    }

    let isCancelled = false;
    const chunks = fullText.match(/[^\n]*\n+|[^\n]+$/g) || [fullText];

    const run = async () => {
      setStreamState({ source: fullText, visible: '' });
      let output = '';
      for (const chunk of chunks) {
        if (isCancelled) return;
        output += chunk;
        setStreamState({ source: fullText, visible: output });
        await sleep(Math.min(120, Math.max(24, speed + Math.round(chunk.length / 8))));
      }
    };

    run();
    return () => {
      isCancelled = true;
    };
  }, [markdown, enabled, speed]);

  const currentSource = String(markdown || '');
  return streamState.source === currentSource ? streamState.visible : '';
};

export const StreamingMarkdownMessage = ({ markdown, stream = true }) => {
  const visibleMarkdown = useStreamingMarkdown(markdown, { enabled: stream });

  return (
    <div
      className="prose prose-sm max-w-none"
      dangerouslySetInnerHTML={{ __html: markdownToHtml(visibleMarkdown) }}
    />
  );
};

// Professional loading indicator - Simple dot animation
export const SimpleLoader = ({ text = "Thinking" }) => {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500">{text}</span>
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '0ms' }} />
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '150ms' }} />
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '300ms' }} />
      </span>
    </div>
  );
};

// Professional job analysis loader
export const JobAnalysisLoader = ({ step = "Analyzing resume" }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % ANALYSIS_STEPS.length);
    }, 1800);
    
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) return 100;
        return Math.min(prev + 2, 100);
      });
    }, 100);

    return () => {
      clearInterval(stepInterval);
      clearInterval(progressInterval);
    };
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-500">{ANALYSIS_STEPS[currentStep].icon}</span>
        <span className="text-gray-700">{ANALYSIS_STEPS[currentStep].text}</span>
        <div className="flex gap-0.5">
          <span className="h-1 w-1 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="h-1 w-1 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="h-1 w-1 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-gray-100">
        <div 
          className="h-full rounded-full bg-blue-400 transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};

// Minimal thinking loader
export const MinimalThinkingLoader = () => {
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-xs text-gray-400">AI is thinking</span>
    </div>
  );
};

// Keep ThinkingLoader for backward compatibility but make it cleaner
export const ThinkingLoader = ({ label = "Analyzing", steps: customSteps }) => {
  return <JobAnalysisLoader step={label} />;
};

export const CopyMessageButton = ({ markdown, label = 'Copy message' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!markdown) return;
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch (error) {
      console.log('Failed to copy generated message', error);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
      aria-label={copied ? 'Copied' : label}
      title={copied ? 'Copied' : label}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
};
