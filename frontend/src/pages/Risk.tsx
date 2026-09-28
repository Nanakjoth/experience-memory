import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Dashboard, MemoryList } from "../lib/types";
import { Bar, Chip, Empty, ErrorNote, Panel, Spinner } from "../components/ui";
import { pct, shortTime } from "../lib/format";
import { useApp } from "../lib/appState";

export function Risk() {
  const { actor } = useApp();
  const [data, setData] = useState<Dashboard | null>(null);
  const [memories, setMemories] = useState<MemoryList | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [dashboard, list] = await Promise.all([
        api.get<Dashboard>("/api/dashboard"),
        api.get<MemoryList>("/api/memories", { actor, limit: 200 }),
      ]);
      setData(dashboard);
      setMemories(list);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [actor]);

  useEffect(() => {
    void load();
  }, [load]);

  const rows = data?.knowledge_at_risk ?? [];
  const items = memories?.items ?? [];
  const personal = items.filter((m) => m.visibility === "PERSONAL");
  const lowConfidence = items
    .filter((m) => m.confidence < 0.65)
    .sort((a, b) => a.confidence - b.confidence)
    .slice(0, 10);
  const expiring = items
    .filter((m) => m.expiry_at)
    .sort((a, b) => (a.expiry_at ?? "").localeCompare(b.expiry_at ?? ""))
    .slice(0, 10);
  const byOwner = Object.entries(
    items
      .filter((m) => m.visibility === "ORGANIZATION")
      .reduce<Record<string, number>>((acc, m) => {
        const key = m.owner || "Unknown";
        acc[key] = (acc[key] ?? 0) + 1;
        return acc;
      }, {}),
  ).sort((a, b) => b[1] - a[1]);
  const maxOwner = Math.max(1, byOwner[0]?.[1] ?? 1);

  return (
    <div className="space-y-5">
      <Panel
        title="Where organizational memory is fragile"
        subtitle="Bus factor, low confidence, expiry, and knowledge that never leaves one person."
        actions={
          <button className="btn-ghost" onClick={load} disabled={busy}>
            {busy ? "Refreshing…" : "Refresh"}
          </button>
        }
      >
        <div className="mb-3">
          <ErrorNote error={error} />
        </div>
        {busy && !data && <Spinner label="Loading risk" />}
        {rows.length === 0 && !busy ? (
          <Empty>No risk rows yet. Capture an expert interview to populate this view.</Empty>
        ) : (
          <ul className="space-y-2">
            {rows.map((row) => (
              <li key={row.system_id} className="panel-tight px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[13px] font-semibold text-slate-100">{row.system}</span>
                  <Chip>{row.team}</Chip>
                  <Chip>{row.criticality} criticality</Chip>
                  <Chip
                    tone={
                      row.risk === "High"
                        ? "border-rose-500/40 bg-rose-500/10 text-rose-300"
                        : row.risk === "Medium"
                          ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                          : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    }
                  >
                    {row.risk} risk
                  </Chip>
                  <Chip>{row.replacement_coverage} successor coverage</Chip>
                </div>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span>Validated {row.validated} / {row.knowledge_items}</span>
                      <span className="tabular-nums">{pct(row.coverage_ratio)}</span>
                    </div>
                    <Bar
                      value={row.coverage_ratio}
                      tone={row.coverage_ratio >= 0.8 ? "bg-emerald-400" : "bg-amber-400"}
                    />
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Critical knowledge owner: <span className="text-slate-200">{row.owner}</span>
                    {row.personal_only > 0 && (
                      <span className="text-amber-300">
                        {" "}
                        · {row.personal_only} item(s) still personal-only
                      </span>
                    )}
                    {row.note && <p className="mt-0.5 text-slate-500">{row.note}</p>}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-[10px] uppercase tracking-wide text-amber-500/80">
          Synthetic prototype metric
        </p>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Low confidence"
          subtitle="Answers will hedge on these. Confidence is a heuristic, not a truth probability."
        >
          {lowConfidence.length === 0 ? (
            <Empty>Nothing below 65% confidence.</Empty>
          ) : (
            <ul className="space-y-2">
              {lowConfidence.map((m) => (
                <li key={m.id} className="panel-tight px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[12px] text-slate-200">{m.title}</span>
                    <span className="shrink-0 text-[11px] tabular-nums text-amber-300">
                      {pct(m.confidence)}
                    </span>
                  </div>
                  <div className="mt-1">
                    <Bar value={m.confidence} tone="bg-amber-400" />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Personal knowledge still private"
          subtitle="Not yet promoted to the organization."
        >
          {personal.length === 0 ? (
            <Empty>No personal memories.</Empty>
          ) : (
            <ul className="space-y-2">
              {personal.map((m) => (
                <li key={m.id} className="panel-tight px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[12px] text-slate-200">{m.title}</span>
                    <Chip tone="border-amber-500/40 bg-amber-500/10 text-amber-300">
                      {m.visibility}
                    </Chip>
                  </div>
                  <div className="mt-0.5 text-[10px] text-slate-600">
                    {m.owner} · {m.evidence_count} evidence · captured {shortTime(m.created_at)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Concentration of organizational knowledge">
          {byOwner.length === 0 ? (
            <Empty>No organizational memories yet.</Empty>
          ) : (
            <ul className="space-y-2">
              {byOwner.slice(0, 8).map(([owner, count]) => (
                <li key={owner}>
                  <div className="flex items-center justify-between text-[12px]">
                    <span className="text-slate-300">{owner}</span>
                    <span className="tabular-nums text-slate-400">{count}</span>
                  </div>
                  <Bar value={count / maxOwner} tone="bg-violet-400" />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Retention clock" subtitle="Expiry marks a memory stale; nothing is deleted.">
          {expiring.length === 0 ? (
            <Empty>No retention clocks yet.</Empty>
          ) : (
            <ul className="space-y-2">
              {expiring.map((m) => (
                <li key={m.id} className="flex items-center justify-between gap-2 text-[12px]">
                  <span className="truncate text-slate-300">{m.title}</span>
                  <span className="shrink-0 text-[10px] tabular-nums text-slate-500">
                    {shortTime(m.expiry_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
