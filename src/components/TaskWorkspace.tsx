"use client";

import { Check, Copy, Download, Eye, Lock, Maximize2, Minimize2, Pencil, Play, RotateCcw, Square } from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import hljs from "highlight.js/lib/core";
import markdown from "highlight.js/lib/languages/markdown";
import python from "highlight.js/lib/languages/python";
import { resetTaskWorkAction, saveTaskWorkAction } from "@/app/actions";
import { Button, Card, cn } from "@/components/ui";

if (!hljs.getLanguage("python")) {
  hljs.registerLanguage("python", python);
}
if (!hljs.getLanguage("markdown")) {
  hljs.registerLanguage("markdown", markdown);
}

const Markdown = dynamic(() => import("@/components/Markdown").then((m) => m.Markdown), {
  loading: () => <p className="text-sm text-faint">Завантаження…</p>,
});

type Props = {
  taskId: number;
  kind: "html" | "markdown" | "python";
  base: string;
  work: string | null;
  fileName: string;
  allowRun?: boolean;
};

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js";
const RUN_TIMEOUT_MS = 28_000; // включно з одноразовим завантаженням Python

// Pyodide працює у Web Worker у браузері користувача — сервер не навантажується, а нескінченний цикл можна зупинити.
const WORKER_SRC = `
let py = null;
self.onmessage = async (e) => {
  const { code, stdin } = e.data;
  try {
    if (!py) {
      postMessage({ type: "status", text: "Завантажую Python (одноразово)…" });
      importScripts("${PYODIDE}");
      py = await loadPyodide();
    }
    const lines = stdin ? stdin.split("\\n") : [];
    let i = 0;
    py.setStdin({ stdin: () => (i < lines.length ? lines[i++] : undefined) });
    py.setStdout({ batched: (s) => postMessage({ type: "out", text: s }) });
    py.setStderr({ batched: (s) => postMessage({ type: "err", text: s }) });
    postMessage({ type: "status", text: "Виконую…" });
    await py.runPythonAsync(code);
  } catch (err) {
    let msg = String((err && err.message) || err);
    const k = msg.indexOf("Traceback");
    postMessage({ type: "err", text: k >= 0 ? msg.slice(k) : msg });
  }
  postMessage({ type: "done" });
};`;

export default function TaskWorkspace({ taskId, kind, base, work, fileName, allowRun = true }: Props) {
  const [text, setText] = useState(work ?? base);
  const [saved, setSaved] = useState<"idle" | "saving" | "saved">("idle");
  const [copied, setCopied] = useState(false);
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [full, setFull] = useState(false);
  const [mounted, setMounted] = useState(false);
  const savedText = useRef(work ?? base);
  const modified = text !== base;

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!full) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFull(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [full]);

  // Автозбереження особистої копії (без рядка в БД = базова версія)
  useEffect(() => {
    if (kind === "html" || text === savedText.current) return;
    setSaved("saving");
    const t = setTimeout(async () => {
      if (text === base) await resetTaskWorkAction(taskId);
      else await saveTaskWorkAction(taskId, text);
      savedText.current = text;
      setSaved("saved");
    }, 800);
    return () => clearTimeout(t);
  }, [text, base, kind, taskId]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard недоступний */
    }
  };

  const download = () => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const reset = async () => {
    if (!window.confirm("Скинути до базової версії? Твої зміни буде втрачено.")) return;
    setText(base);
    savedText.current = base;
    setSaved("idle");
    await resetTaskWorkAction(taskId);
  };

  const toolbar = (
    <div className="flex flex-wrap items-center gap-1.5">
      {(kind === "markdown" || kind === "python") && (
        <div className="mr-1 flex rounded-lg border border-line bg-surface-2 p-0.5">
          {(["view", "edit"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={cn("flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition", mode === m ? "bg-surface text-fg shadow-sm" : "text-muted hover:text-fg")}
            >
              {m === "view" ? <Eye size={12} /> : <Pencil size={12} />} {m === "view" ? "Перегляд" : "Редагувати"}
            </button>
          ))}
        </div>
      )}
      <Button onClick={copy} className="h-8 px-2.5 text-xs">
        {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Скопійовано" : "Копіювати"}
      </Button>
      <Button onClick={download} className="h-8 px-2.5 text-xs">
        <Download size={13} /> Завантажити
      </Button>
      {kind !== "html" && modified && (
        <Button variant="ghost" onClick={reset} className="h-8 px-2.5 text-xs">
          <RotateCcw size={13} /> До базової
        </Button>
      )}
      <span className="ml-auto text-xs text-faint">
        {kind === "html" ? "" : saved === "saving" ? "Зберігаю…" : modified ? "Моя копія збережена" : "Базова версія"}
      </span>
    </div>
  );

  if (kind === "html") {
    const htmlContent = (
      <div className={cn(full ? "fixed inset-0 z-[100] flex h-screen w-screen flex-col bg-bg p-4" : "space-y-2")}>
        <div className="flex items-center gap-1.5">
          <Button onClick={download} className="h-8 px-2.5 text-xs">
            <Download size={13} /> Завантажити
          </Button>
          <Button onClick={() => setFull(!full)} className="h-8 px-2.5 text-xs">
            {full ? <Minimize2 size={13} /> : <Maximize2 size={13} />} {full ? "Згорнути" : "На весь екран"}
          </Button>
          <span className="ml-auto text-xs text-faint">
            {full ? "Esc для виходу • " : ""}Відповіді не зберігаються й не перевіряються сервером
          </span>
        </div>
        {/* sandbox без allow-same-origin: сторінка виконує свої скрипти, але не має доступу до сесії сайту */}
        <iframe
          title="Завдання"
          srcDoc={text}
          sandbox="allow-scripts allow-forms allow-modals allow-popups"
          className={cn("w-full rounded-xl border border-line bg-white", full ? "mt-3 flex-1" : "h-[75vh]")}
        />
      </div>
    );

    if (full && mounted) {
      return createPortal(htmlContent, document.body);
    }
    return htmlContent;
  }

  return (
    <div className="space-y-3">
      {toolbar}
      {kind === "markdown" ? (
        mode === "view" ? (
          <Card className="p-6">
            <Markdown source={text} />
          </Card>
        ) : (
          <HighlightedCodeEditor value={text} onChange={setText} language="markdown" minHeight="500px" />
        )
      ) : (
        <PythonRunner code={text} onChange={setText} mode={mode} allowRun={allowRun} />
      )}
    </div>
  );
}

function HighlightedCodeEditor({
  value,
  onChange,
  language = "python",
  minHeight = "460px",
}: {
  value: string;
  onChange: (v: string) => void;
  language?: string;
  minHeight?: string;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);

  const highlighted = useMemo(() => {
    try {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(value || " ", { language }).value;
      }
      return value;
    } catch {
      return value;
    }
  }, [value, language]);

  const syncScroll = () => {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  return (
    <div
      className="relative w-full rounded-xl border border-line bg-code font-mono text-[13px] leading-6 overflow-hidden transition focus-within:border-line-strong focus-within:ring-4 focus-within:ring-focus"
      style={{ minHeight }}
    >
      {/* Підсвічений шар з токенами кольору hljs під низом */}
      <pre
        ref={preRef}
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-auto p-4 m-0 font-mono text-[13px] leading-6 whitespace-pre select-none"
        style={{ minHeight }}
      >
        <code
          className={`hljs language-${language}`}
          dangerouslySetInnerHTML={{ __html: highlighted + (value.endsWith("\n") ? "\n" : "") }}
        />
      </pre>

      {/* Прозоре поле для комфортного редагування з живим курсором */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={syncScroll}
        onKeyDown={(e) => {
          if (e.key === "Tab" && !e.shiftKey) {
            e.preventDefault();
            const el = e.currentTarget;
            const { selectionStart: s, selectionEnd: end } = el;
            const next = value.slice(0, s) + "    " + value.slice(end);
            onChange(next);
            requestAnimationFrame(() => {
              el.setSelectionRange(s + 4, s + 4);
              syncScroll();
            });
          }
        }}
        spellCheck={false}
        autoCapitalize="none"
        autoCorrect="off"
        wrap="off"
        className="relative z-10 block h-full w-full resize-y overflow-auto bg-transparent p-4 font-mono text-[13px] leading-6 !text-transparent caret-[var(--fg)] outline-none whitespace-pre"
        style={{ minHeight }}
      />
    </div>
  );
}

type OutLine = { type: "out" | "err"; text: string };

function PythonRunner({
  code,
  onChange,
  mode,
  allowRun = true,
}: {
  code: string;
  onChange: (v: string) => void;
  mode: "view" | "edit";
  allowRun?: boolean;
}) {
  const workerRef = useRef<Worker | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [output, setOutput] = useState<OutLine[]>([]);
  const [stdin, setStdin] = useState("");

  const highlighted = useMemo(() => {
    try {
      return hljs.highlight(code || "# порожній файл", { language: "python" }).value;
    } catch {
      return code;
    }
  }, [code]);

  const stop = useCallback((message?: string) => {
    if (timer.current) clearTimeout(timer.current);
    workerRef.current?.terminate();
    workerRef.current = null;
    setRunning(false);
    setStatus("");
    if (message) setOutput((o) => [...o, { type: "err", text: message }]);
  }, []);

  useEffect(() => () => stop(), [stop]);

  const run = () => {
    if (!allowRun || running) return;
    if (!workerRef.current) {
      const url = URL.createObjectURL(new Blob([WORKER_SRC], { type: "text/javascript" }));
      const w = new Worker(url);
      w.onmessage = (e: MessageEvent<{ type: string; text?: string }>) => {
        const m = e.data;
        if (m.type === "status") setStatus(m.text ?? "");
        else if (m.type === "done") {
          if (timer.current) clearTimeout(timer.current);
          setRunning(false);
          setStatus("");
        } else setOutput((o) => [...o, { type: m.type as "out" | "err", text: m.text ?? "" }]);
      };
      w.onerror = () => stop("Не вдалося запустити Python (перевір інтернет-з'єднання).");
      workerRef.current = w;
    }
    setOutput([]);
    setRunning(true);
    setStatus("Запуск…");
    timer.current = setTimeout(() => stop("Зупинено: виконання тривало надто довго (можливо, нескінченний цикл)."), RUN_TIMEOUT_MS);
    workerRef.current.postMessage({ code, stdin });
  };

  return (
    <>
      {mode === "view" ? (
        <pre className="max-h-[560px] overflow-auto rounded-xl border border-line bg-code p-4 font-mono text-[13px] leading-6">
          <code
            className="hljs language-python"
            dangerouslySetInnerHTML={{ __html: highlighted }}
          />
        </pre>
      ) : (
        <HighlightedCodeEditor value={code} onChange={onChange} language="python" minHeight="460px" />
      )}

      {allowRun ? (
        <>
          <div className="flex items-center gap-2">
            {running ? (
              <Button onClick={() => stop("Зупинено.")} variant="secondary">
                <Square size={13} fill="currentColor" /> Зупинити
              </Button>
            ) : (
              <Button onClick={run} variant="primary">
                <Play size={13} fill="currentColor" /> Запустити
              </Button>
            )}
            <span className="text-xs text-faint">{status || "Виконується у твоєму браузері (Pyodide), без серверу"}</span>
          </div>

          <details className="text-sm">
            <summary className="cursor-pointer text-xs text-muted hover:text-fg">Вхідні дані для input() — по одному рядку</summary>
            <textarea
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              rows={3}
              spellCheck={false}
              className="mt-2 w-full rounded-lg border border-line bg-surface p-3 font-mono text-[13px] outline-none focus:border-line-strong focus:ring-4 focus:ring-focus"
            />
          </details>

          {(output.length > 0 || running) && (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-code p-4 font-mono text-[13px] leading-6">
              {output.length === 0 && <span className="text-faint">…</span>}
              {output.map((l, i) => (
                <div key={i} className={l.type === "err" ? "text-red-fg" : undefined}>
                  {l.text || "\u00a0"}
                </div>
              ))}
            </pre>
          )}
        </>
      ) : (
        <div className="flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-xs text-muted">
          <Lock size={14} className="text-faint shrink-0" />
          <span>Запуск коду Python вимкнено адміністратором для безпеки (доступні перегляд, підсвітка та редагування).</span>
        </div>
      )}
    </>
  );
}

