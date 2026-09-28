import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Contradiction, Dashboard, DemoState } from "../lib/types";
import { Chip, Empty, ErrorNote, Panel, Spinner } from "../components/ui";
import { shortTime } from "../lib/format";

interface EvolutionPayload {
  stages: Record<string, unknown>[];
  contradictions: Contradiction[];
  open: number;
  resolved: number;
}

interface DemoEnvelope<T> {
  ok: boolean;
  message: string;
  payload: T;
}

export function Evolution() {
  const [data, setData] = useState<EvolutionPayload | null>(null);
  const [state, setState] = useState<DemoState | null>(null);
  const [continuity, setContinuity] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [evolution, demoState, dashboard] = await Promise.all([
        api.post<DemoEnvelope<EvolutionPayload>>("/api/demo/evolution"),
        api.get<DemoState>("/api/demo/state"),
        api.get<Dashboard>("/api/dashboard"),
      ]);
      setData(evolution.payload);
      setState(demoState);
      setContinuity(dashboard.continuity);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stages = data?.stages ?? [];
  const timeline = Array.isArray(continuity?.timeline) ? (continuity?.timeline as Record<string, unknown>[]) : [];

  return (
    <div className="space-y-5">
      <Panel
        title="Memory Evolution"
        subtitle="What changed, what stopped applying, and what history was preserved. Nothing is deleted."
        actions={
          <button className="btn-ghost" onClick={load} disabled={busy}>
            {busy ? "Refreshing…" : "Refresh"}
          </button>
        }
      >
        <div className="mb-3">
          <ErrorNote error={error} />
        </div>
        {busy && !data && <Spinner label="Loading evolution" />}
        {data && (
          <div className="flex flex-wrap items-center gap-2 text-[12px] text-slate-400">
            <Chip tone="border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
              Environment: {state?.current_environment ?? "—"}
            </Chip>
            <Chip>{data.open} open contradictions</Chip>
            <Chip>{data.resolved} resolved</Chip>
            <Chip>{state?.architecture_changes.length ?? 0} architecture changes</Chip>
            {stages.length > 0 && <Chip>{stages.length} evolution stages</Chip>}
          </div>
        )}
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Contradictions"
          subtitle="Old knowledge that a change made unsafe to apply."
        >
          {!data ? (
            <Empty>No data yet.</Empty>
          ) : data.contradictions.length === 0 ? (
            <Empty>No contradiction. Introduce Queue v2 from the guided demo to raise one.</Empty>
          ) : (
            <ul className="space-y-2">
              {data.contradictions.slice(0, 12).map((c) => (
                <li key={c.id} className="panel-tight px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13px] font-semibold text-slate-200">
                      {c.memory_title}
                    </span>
                    <Chip
                      tone={
                        c.status === "REVIEW_REQUIRED"
                          ? "border-rose-500/40 bg-rose-500/10 text-rose-300"
                          : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      }
                    >
                      {c.status}
                    </Chip>
                    {c.resolution && <Chip>{c.resolution}</Chip>}
                  </div>
                  <p className="mt-1 text-[11px] leading-snug text-slate-400">{c.reason}</p>
                  <div className="mt-1 text-[10px] text-slate-600">
                    {c.memory_scope} → {c.current_environment} · detected {shortTime(c.detected_at)}
                    {c.resolved_by ? ` · resolved by ${c.resolved_by}` : ""}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Architecture changes" subtitle="The events that invalidate old assumptions.">
          {!state || state.architecture_changes.length === 0 ? (
            <Empty>No architecture change recorded.</Empty>
          ) : (
            <ol className="space-y-2.5">
              {state.architecture_changes.map((change) => (
                <li key={change.id} className="panel-tight px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13px] font-semibold text-slate-200">{change.title}</span>
                    <Chip>{change.system}</Chip>
                    <Chip tone="border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
                      {change.component}
                    </Chip>
                  </div>
                  <p className="mt-1 text-[11px] leading-snug text-slate-400">{change.summary}</p>
                  {change.invalidates_scope && (
                    <p className="mt-1 text-[10px] text-amber-400/80">
                      Invalidates scope: {change.invalidates_scope}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </Panel>

        <Panel title="Evolution stages" subtitle="How the bank moved as the environment changed.">
          {stages.length === 0 ? (
            <Empty>No stage data yet.</Empty>
          ) : (
            <ol className="space-y-2">
              {stages.map((stage, i) => (
                <li key={i} className="panel-tight px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded bg-slate-800 text-[10px] font-bold text-slate-400">
                      {i + 1}
                    </span>
                    <span className="text-[12px] font-semibold text-slate-200">
                      {String(stage.stage ?? stage.title ?? stage.label ?? `Stage ${i + 1}`)}
                    </span>
                    <Chip>{String(stage.scope ?? stage.environment ?? "—")}</Chip>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {String(stage.detail ?? stage.description ?? stage.note ?? "")}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </Panel>

        <Panel title="Continuity timeline" subtitle="Synthetic prototype metric.">
          {timeline.length === 0 ? (
            <Empty>No timeline yet. Run the guided demo to build history.</Empty>
          ) : (
            <ol className="space-y-2">
              {timeline.slice(0, 12).map((row, i) => (
                <li key={i} className="flex gap-3 text-[12px]">
                  <span className="w-24 shrink-0 tabular-nums text-slate-600">
                    {shortTime(String(row.at ?? row.date ?? ""))}
                  </span>
                  <span className="text-slate-300">
                    {String(row.event ?? row.message ?? row.label ?? "")}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>
    </div>
  );
}
