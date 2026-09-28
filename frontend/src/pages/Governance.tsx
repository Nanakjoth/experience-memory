import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/appState";
import type { Contradiction, GovernanceSummary } from "../lib/types";
import { Chip, Empty, ErrorNote, Panel, Spinner } from "../components/ui";
import { shortTime } from "../lib/format";

export function Governance() {
  const { actor, refreshShell } = useApp();
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [s, c, p] = await Promise.all([
        api.get<GovernanceSummary>("/api/governance/summary"),
        api.get<{ contradictions: Contradiction[] }>("/api/contradictions"),
        api.get<{ promotion_rule?: string; retention_rule?: string }>(
          "/api/governance/policies",
        ),
      ]);
      setSummary({ ...s, promotion_rule: p.promotion_rule, retention_rule: p.retention_rule });
      setContradictions(c.contradictions);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(id: string, action: string) {
    setBusy(true);
    setError(null);
    try {
      const body = await api.post<{ detail?: string }>(
        `/api/contradictions/${id}/resolve`,
        { actor, action, note },
      );
      setMessage(
        body.detail
          ? `Resolved with "${action}": ${body.detail}`
          : `Contradiction resolved with "${action}". History preserved.`,
      );
      setNote("");
      await load();
      await refreshShell();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const open = contradictions.filter((c) => c.status === "REVIEW_REQUIRED");
  const resolved = contradictions.filter((c) => c.status !== "REVIEW_REQUIRED");

  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Panel
          title="Contradiction review queue"
          subtitle="Nothing is resolved automatically. A human picks how history is handled."
          actions={
            <input
              className="input w-56 py-1.5 text-xs"
              placeholder="Resolution note (optional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          }
        >
          <div className="mb-3">
            <ErrorNote error={error} />
          </div>
          {message && (
            <p className="mb-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-[12px] text-emerald-200">
              {message}
            </p>
          )}
          {busy && !summary && <Spinner label="Loading" />}
          {open.length === 0 ? (
            <Empty>Nothing awaiting review. The queue is clear.</Empty>
          ) : (
            <ul className="space-y-2.5">
              {open.map((c) => (
                <li key={c.id} className="panel-tight px-3 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13px] font-semibold text-slate-100">
                      {c.memory_title}
                    </span>
                    <Chip tone="border-rose-500/40 bg-rose-500/10 text-rose-300">
                      {c.status}
                    </Chip>
                    <Chip>{c.conflicting_source_type}</Chip>
                  </div>
                  <p className="mt-1.5 text-[12px] leading-snug text-slate-300">{c.reason}</p>
                  <div className="mt-1 text-[10px] text-slate-600">
                    {c.memory_scope} → {c.current_environment} · {shortTime(c.detected_at)}
                  </div>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {Object.entries(summary?.resolution_actions ?? {}).map(([action, spec]) => (
                      <button
                        key={action}
                        className="btn-ghost"
                        disabled={busy}
                        title={spec.description}
                        onClick={() => resolve(c.id, action)}
                      >
                        {spec.label}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div className="space-y-5">
          <Panel title="Retention policies">
            {!summary ? (
              <Spinner label="Loading" />
            ) : (
              <>
                {(summary.promotion_rule || summary.retention_rule) && (
                  <div className="mb-3 space-y-1.5 border-b border-slate-800 pb-3">
                    {summary.promotion_rule && (
                      <p className="text-[11px] leading-relaxed text-slate-400">
                        <span className="font-semibold text-cyan-400">Promotion: </span>
                        {summary.promotion_rule}
                      </p>
                    )}
                    {summary.retention_rule && (
                      <p className="text-[11px] leading-relaxed text-slate-400">
                        <span className="font-semibold text-cyan-400">Retention: </span>
                        {summary.retention_rule}
                      </p>
                    )}
                  </div>
                )}
                <ul className="space-y-2.5">
                {Object.values(summary.policies).map((policy) => (
                  <li key={policy.visibility} className="panel-tight px-3 py-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[12px] font-semibold text-slate-200">
                        {policy.visibility}
                      </span>
                      <Chip>{policy.default_access_level}</Chip>
                      <Chip>{policy.retention_days}d</Chip>
                      {policy.requires_review && (
                        <Chip tone="border-amber-500/40 bg-amber-500/10 text-amber-300">
                          review required
                        </Chip>
                      )}
                    </div>
                    <p className="mt-1 text-[11px] leading-snug text-slate-500">
                      {policy.description}
                    </p>
                  </li>
                ))}
                </ul>
              </>
            )}
          </Panel>

          <Panel title="Current distribution">
            {summary ? (
              <div className="space-y-3">
                <Distribution title="By visibility" data={summary.by_visibility} />
                <Distribution title="By status" data={summary.by_status} />
                <Distribution title="By confidence" data={summary.by_confidence} />
              </div>
            ) : (
              <Spinner label="Loading" />
            )}
          </Panel>

          {resolved.length > 0 && (
            <Panel title="Recently resolved" subtitle="History preserved, never deleted.">
              <ul className="space-y-2">
                {resolved.slice(0, 6).map((c) => (
                  <li key={c.id} className="text-[11px]">
                    <span className="text-slate-300">{c.memory_title}</span>
                    <span className="ml-2 text-emerald-300">{c.resolution}</span>
                    <div className="text-slate-600">
                      {c.resolved_by} · {shortTime(c.resolved_at)}
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

function Distribution({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <div>
      <div className="label-xs">{title}</div>
      <ul className="mt-1.5 space-y-1.5">
        {entries.map(([key, value]) => (
          <li key={key}>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400">{key}</span>
              <span className="tabular-nums text-slate-300">{value}</span>
            </div>
            <div className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-cyan-400/80"
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
