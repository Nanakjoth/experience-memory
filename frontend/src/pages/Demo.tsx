import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ChevronRight, Play, RotateCcw, XCircle } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useApp } from "../lib/appState";
import type { DemoRun, DemoState, DemoStep } from "../lib/types";
import { Bar, Chip, ErrorNote, Panel, Spinner, Stat } from "../components/ui";
import { pct } from "../lib/format";

interface Control {
  step: string;
  key: string;
  label: string;
  narration: string;
}

const ENDPOINT: Record<string, string> = {
  seed: "/api/demo/seed",
  "seed-incidents": "/api/demo/seed-incidents",
  capture: "/api/demo/capture",
  promote: "/api/demo/promote",
  ask: "/api/demo/ask",
  outcome: "/api/demo/outcome",
  "queue-v2": "/api/demo/queue-v2",
  evolution: "/api/demo/evolution",
  privacy: "/api/demo/privacy",
  reset: "/api/demo/reset",
  "resolve-contradictions": "/api/demo/resolve-contradictions",
};

const TONE: Record<string, string> = {
  experience: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300",
  lesson: "border-violet-500/40 bg-violet-500/10 text-violet-300",
  fact: "border-slate-700 bg-slate-800 text-slate-300",
  event: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  correction: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  exception: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  observation: "border-teal-500/40 bg-teal-500/10 text-teal-300",
};

export function Demo() {
  const { refreshShell } = useApp();
  const [controls, setControls] = useState<Control[]>([]);
  const [state, setState] = useState<DemoState | null>(null);
  const [run, setRun] = useState<DemoRun | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [openStep, setOpenStep] = useState<number | null>(null);
  const [log, setLog] = useState<string[]>([]);

  const loadState = useCallback(async () => {
    const body = await api.get<DemoState>("/api/demo/state");
    setState(body);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [controlsBody] = await Promise.all([
          api.get<{ controls: Control[] }>("/api/demo/controls"),
          loadState(),
        ]);
        setControls(controlsBody.controls);
      } catch (err) {
        setError(err);
      }
    })();
  }, [loadState]);

  async function press(key: string) {
    setBusy(key);
    setError(null);
    try {
      const body = await api.post<{ message?: string; payload?: unknown }>(
        ENDPOINT[key] ?? `/api/demo/${key}`,
      );
      setLog((prev) => [
        `${new Date().toLocaleTimeString()} · ${key} · ${
          (body as { message?: string }).message ?? "done"
        }`,
        ...prev,
      ]);
      setRun(null);
      await loadState();
      await refreshShell();
    } catch (err) {
      setError(err);
      setLog((prev) => [
        `${new Date().toLocaleTimeString()} · ${key} · ${(err as Error).message}`,
        ...prev,
      ]);
    } finally {
      setBusy(null);
    }
  }

  async function runAll() {
    setBusy("run");
    setError(null);
    setLog([]);
    try {
      const body = await api.post<DemoRun>("/api/demo/run");
      setRun(body);
      setLog(
        body.steps.map(
          (s) =>
            `${s.index}. ${s.title} — ${s.status === "ok" ? s.narration : (s.error ?? "failed")}`,
        ),
      );
      setOpenStep(body.steps.find((s) => s.status !== "ok")?.index ?? null);
      await loadState();
      await refreshShell();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <Panel
        title="The 13-step MemoryOS story"
        subtitle="Run the whole narrative, or drive it one control at a time. Every step calls the real API — nothing on this page is faked."
        actions={
          <>
            <button className="btn-ghost" onClick={runAll} disabled={busy !== null}>
              <Play className="h-4 w-4" />
              {busy === "run" ? "Running…" : "Run full demo"}
            </button>
            <button
              className="btn-subtle"
              onClick={() => press("reset")}
              disabled={busy !== null}
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
          {(state
            ? [
                ["Memories", state.memories],
                ["Incidents", state.incidents],
                ["Open contradictions", state.open_contradictions],
                ["Resolved", state.resolved_contradictions],
                ["Personal", state.by_visibility.PERSONAL ?? 0],
                ["Organizational", state.by_visibility.ORGANIZATION ?? 0],
                ["Environment", state.current_environment],
              ]
            : []
          ).map(([label, value]) => (
            <Stat key={String(label)} label={String(label)} value={String(value)} />
          ))}
        </div>
        {!state && (
          <div className="mt-4">
            <Spinner label="Loading demo state" />
          </div>
        )}
        <div className="mt-4">
          <ErrorNote error={error} />
        </div>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Panel
          title={run ? `Run ${run.id}` : "Step-by-step results"}
          subtitle={
            run
              ? `${run.status === "ok" ? "All steps succeeded" : "Some steps failed"} in ${run.duration_ms} ms`
              : "Press a control, or run the full demo to see every step."
          }
        >
          {!run && (
            <p className="text-sm text-slate-500">
              The story: an expert teaches the system what the runbook leaves out → a new engineer
              asks a question → the answer is evidence-backed → the outcome is remembered →
              the environment changes → old knowledge stops applying automatically → history is
              preserved, scope is narrowed, never deleted.
            </p>
          )}

          {run && (
            <ol className="space-y-1.5">
              {run.steps.map((step) => (
                <StepRow
                  key={step.index}
                  step={step}
                  open={openStep === step.index}
                  onToggle={() => setOpenStep(openStep === step.index ? null : step.index)}
                />
              ))}
            </ol>
          )}

          {log.length > 0 && !run && (
            <ul className="mt-4 space-y-1 border-t border-slate-800 pt-3 font-mono text-[11px] text-slate-500">
              {log.slice(0, 8).map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          )}
        </Panel>

        <div className="space-y-5">
          <Panel title="Controls" subtitle="One call each. Watch the numbers move.">
            <div className="space-y-2">
              {controls.map((control) => (
                <button
                  key={`${control.step}-${control.key}-${control.label}`}
                  onClick={() => press(control.key)}
                  disabled={busy !== null}
                  className="group w-full rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5 text-left transition-colors hover:border-cyan-500/40 hover:bg-cyan-500/5 disabled:opacity-40"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-slate-800 text-[10px] font-bold text-slate-400">
                      {control.step}
                    </span>
                    <span className="text-[13px] font-semibold text-slate-200 group-hover:text-cyan-300">
                      {control.label}
                    </span>
                    <ChevronRight className="ml-auto h-3.5 w-3.5 text-slate-600" />
                  </div>
                  <p className="mt-1 pl-7 text-[11px] leading-snug text-slate-500">
                    {control.narration}
                  </p>
                </button>
              ))}
            </div>
          </Panel>

          {state && (
            <Panel title="Live lifecycle" subtitle="Real application counters.">
              <div className="space-y-2.5">
                {Object.entries(state.metrics).map(([key, value]) => (
                  <div key={key}>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">{key.replace(/_/g, " ")}</span>
                      <span className="font-semibold tabular-nums text-slate-200">{value}</span>
                    </div>
                    <Bar value={Math.min(1, value / 30)} />
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

function StepRow({
  step,
  open,
  onToggle,
}: {
  step: DemoStep;
  open: boolean;
  onToggle: () => void;
}) {
  const payload = (step.payload ?? {}) as Record<string, unknown>;
  return (
    <li className="rounded-lg border border-slate-800 bg-slate-900/40">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
      >
        {step.status === "ok" ? (
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
        ) : (
          <XCircle className="h-4 w-4 shrink-0 text-rose-400" />
        )}
        <span className="w-5 shrink-0 text-[11px] font-bold tabular-nums text-slate-600">
          {step.index}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-semibold text-slate-200">
            {step.title}
          </span>
          <span className="block truncate text-[11px] text-slate-500">
            {step.status === "ok" ? step.narration : (step.error ?? "failed")}
          </span>
        </span>
        <span className="shrink-0 text-[10px] tabular-nums text-slate-600">{step.ms} ms</span>
      </button>
      {open && (
        <div className="border-t border-slate-800 px-3 py-3">
          <StepPayload step={step} payload={payload} />
        </div>
      )}
    </li>
  );
}

function StepPayload({ step, payload }: { step: DemoStep; payload: Record<string, unknown> }) {
  const answer = payload.answer as
    | { headline?: string; sections?: { label: string; points: string[] }[]; outdated_warning?: string | null }
    | undefined;
  const confidence = payload.confidence as { score?: number; band?: string } | undefined;
  const contradictions = payload.contradictions as { memory_title: string }[] | undefined;
  const memories = payload.memories as
    | { id: string; title: string; type: string; status: string; confidence: number }[]
    | undefined;

  return (
    <div className="space-y-3">
      {answer?.headline && (
        <div>
          <div className="label-xs">Answer</div>
          <p className="mt-1 text-sm text-slate-200">{answer.headline}</p>
          {answer.outdated_warning && (
            <p className="mt-1 text-[11px] text-amber-300/90">{answer.outdated_warning}</p>
          )}
          {answer.sections?.map((section) => (
            <div key={section.label} className="mt-2">
              <div className="text-[11px] font-semibold text-cyan-400">{section.label}</div>
              <ul className="mt-0.5 space-y-0.5">
                {section.points.map((p, i) => (
                  <li key={i} className="text-[12px] leading-relaxed text-slate-400">
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {confidence && typeof confidence.score === "number" && (
        <div className="flex items-center gap-2">
          <div className="label-xs">Confidence</div>
          <Chip tone="border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
            {pct(confidence.score)} · {confidence.band}
          </Chip>
        </div>
      )}

      {memories && memories.length > 0 && (
        <div>
          <div className="label-xs">Memories touched</div>
          <ul className="mt-1 space-y-1">
            {memories.slice(0, 6).map((m) => (
              <li key={m.id} className="flex items-center gap-2 text-[12px]">
                <span className="text-slate-300">{m.title}</span>
                <Chip tone={TONE[m.type.toLowerCase()] ?? TONE.fact}>{m.type}</Chip>
                <span className="text-[10px] tabular-nums text-slate-600">{m.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {contradictions && contradictions.length > 0 && (
        <div>
          <div className="label-xs">Contradictions raised</div>
          <ul className="mt-1 space-y-1 text-[12px] text-rose-200">
            {contradictions.slice(0, 6).map((c, i) => (
              <li key={i}>• {c.memory_title}</li>
            ))}
          </ul>
        </div>
      )}

      {!answer && !memories && !contradictions && (
        <pre
          className={clsx(
            "max-h-72 overflow-auto rounded-lg bg-slate-950/70 p-3 text-[11px] leading-relaxed text-slate-400",
          )}
        >
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
      <div className="text-[10px] text-slate-600">step key: {step.key}</div>
    </div>
  );
}
