import { Check, Copy } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const ANALYSIS_STEPS = [
  'Reading resume signals',
  'Comparing job requirements',
  'Checking ATS keywords',
  'Preparing recommendations',
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

export const AssistantRobotLoader = ({ size = 'md' }) => (
  <span
    className={[
      'bidwise-robot-shell relative inline-flex shrink-0 items-center justify-center rounded-2xl bg-blue-50 ring-1 ring-blue-100',
      size === 'sm' ? 'h-12 w-12' : 'h-16 w-16',
    ].join(' ')}
    aria-hidden="true"
  >
    <img
      src="/Robot-Bot%203D.svg"
      alt=""
      className={[
        'bidwise-robot-loader object-contain',
        size === 'sm' ? 'h-11 w-11' : 'h-15 w-15',
      ].join(' ')}
      loading="eager"
    />
  </span>
);

export const SimpleLoader = ({ text = null }) => {
  const { t } = useLanguage();

  return (
    <div className="flex items-center gap-2.5">
      <AssistantRobotLoader size="sm" />
      <span className="text-sm text-gray-600">{text || t('opportunities.detail.aiWorking')}</span>
    </div>
  );
};

export const JobAnalysisLoader = ({ step = null, steps = null }) => {
  const visibleSteps = Array.isArray(steps) && steps.length ? steps : ANALYSIS_STEPS;
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const stepInterval = window.setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % visibleSteps.length);
    }, 1800);

    return () => {
      window.clearInterval(stepInterval);
    };
  }, [visibleSteps.length]);

  return (
    <div className="rounded-2xl rounded-tl-md bg-white px-4 py-3 shadow-sm ring-1 ring-blue-100">
      <div className="flex items-center gap-3">
        <AssistantRobotLoader />
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-800">{step || visibleSteps[currentStep]}</p>
          <div className="mt-1.5 h-1 w-44 max-w-full overflow-hidden rounded-full bg-gray-100">
            <div className="bidwise-thinking-bar h-full rounded-full bg-gradient-to-r from-blue-600 via-emerald-500 to-sky-500" />
          </div>
        </div>
      </div>
    </div>
  );
};

export const MinimalThinkingLoader = () => {
  const { t } = useLanguage();

  return (
    <div className="flex items-center gap-2">
      <AssistantRobotLoader size="sm" />
      <span className="text-xs text-gray-500">{t('opportunities.detail.aiWorking')}</span>
    </div>
  );
};

export const ThinkingLoader = ({ label = null, steps: customSteps }) => (
  <JobAnalysisLoader step={label} steps={customSteps} />
);

export const CopyMessageButton = ({ markdown, label = null }) => {
  const { t } = useLanguage();
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
      aria-label={copied ? t('common.copied') : label || t('common.copyMessage')}
      title={copied ? t('common.copied') : label || t('common.copyMessage')}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
};
