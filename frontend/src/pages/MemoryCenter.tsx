import { useCallback, useEffect, useState } from "react";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../lib/appState";
import type { MemoryCard, MemoryDetail, MemoryList } from "../lib/types";
import { Bar, Chip, Empty, ErrorNote, Panel, Spinner } from "../components/ui";
import {
  confidenceTone,
  pct,
  shortTime,
  statusTone,
  visibilityTone,
} from "../lib/format";

export function MemoryCenter() {
  const { actor } = useApp();
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [data, setData] = useState<MemoryList | null>(null);
  const [selected, setSelected] = useState<MemoryDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setData(
        await api.get<MemoryList>("/api/memories", {
          actor,
          q: query || undefined,
          limit: 60,
          ...filters,
        }),
      );
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [actor, query, filters]);

  useEffect(() => {
    void load();
  }, [load]);

  const open = useCallback(
    async (id: string) => {
      setError(null);
      try {
        setSelected(await api.get<MemoryDetail>(`/api/memories/${id}`, { actor }));
      } catch (err) {
        setError(err);
      }
    },
    [actor],
  );

  const withheld = data?.withheld ?? [];

  return (
    <div className="space-y-5">
      <Panel
        title="Every memory the system holds"
        subtitle="What you see is already filtered by the permission resolver. Withheld items are listed, never shown."
      >
        <div className="flex flex-col gap-2 lg:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-600" />
            <input
              className="input pl-9"
              placeholder="Search titles, content, entities…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <FilterSelect
              label="Type"
              value={filters.type ?? ""}
              options={data?.filters.types ?? []}
              onChange={(v) => setFilters((f) => ({ ...f, type: v || undefined }))}
            />
            <FilterSelect
              label="Scope"
              value={filters.scope ?? ""}
              options={data?.filters.scopes ?? []}
              onChange={(v) => setFilters((f) => ({ ...f, scope: v || undefined }))}
            />
            <FilterSelect
              label="Visibility"
              value={filters.visibility ?? ""}
              options={data?.filters.visibilities ?? []}
              onChange={(v) => setFilters((f) => ({ ...f, visibility: v || undefined }))}
            />
            <FilterSelect
              label="Status"
              value={filters.status ?? ""}
              options={data?.filters.statuses ?? []}
              onChange={(v) => setFilters((f) => ({ ...f, status: v || undefined }))}
            />
          </div>
        </div>

        {withheld.length > 0 && (
          <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2">
            <div className="text-[11px] font-semibold text-amber-300">
              {withheld.length} memory item(s) withheld from {actor} by the permission resolver
            </div>
            <ul className="mt-1 space-y-0.5 text-[11px] text-amber-100/70">
              {withheld.slice(0, 5).map((w) => (
                <li key={w.id}>
                  {w.id} — {w.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-3 flex items-center gap-3 text-[11px] text-slate-500">
          <span>
            {data?.total ?? 0} memories total
            {data ? ` · showing ${data.items.length}` : ""}
          </span>
          {busy && <Spinner label="Filtering" />}
        </div>
        <div className="mt-2">
          <ErrorNote error={error} />
        </div>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
        <Panel
          title="Memories"
          subtitle="Click a memory to see provenance, the memory gate, evidence and full history."
        >
          {!data || data.items.length === 0 ? (
            <Empty>
              No memory matches. Run the guided demo or capture an expert interview first.
            </Empty>
          ) : (
            <ul className="space-y-2">
              {data.items.map((mem) => (
                <li key={mem.id}>
                  <button
                    onClick={() => open(mem.id)}
                    className="panel-tight w-full px-3 py-2.5 text-left transition-colors hover:border-cyan-500/40"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] font-semibold text-slate-200">
                        {mem.title}
                      </span>
                      <Chip tone={visibilityTone(mem.visibility)}>{mem.visibility}</Chip>
                      <Chip tone={statusTone(mem.status)}>{mem.status}</Chip>
                      <Chip tone={confidenceTone(bandOf(mem.confidence))}>
                        {pct(mem.confidence)}
                      </Chip>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[12px] text-slate-400">{mem.summary}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-600">
                      <span>{mem.scope}</span>
                      <span>{mem.source_name || mem.source_type}</span>
                      <span>{mem.owner}</span>
                      <span>
                        {mem.evidence_count} evidence · v{mem.version}
                      </span>
                      {mem.excluded_scopes.length > 0 && (
                        <span className="text-amber-500/80">
                          not applicable to {mem.excluded_scopes.join(", ")}
                        </span>
                      )}
                    </div>
                    <div className="mt-1.5">
                      <Bar value={mem.confidence} />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <MemoryDetailPanel detail={selected} onRefresh={load} />
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <select
      className="input py-1.5 text-xs"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
      title={label}
    >
      <option value="">{label}: any</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

function bandOf(score: number): string {
  if (score >= 0.85) return "VERY_HIGH";
  if (score >= 0.65) return "HIGH";
  if (score >= 0.45) return "MEDIUM";
  return "LOW";
}

function MemoryDetailPanel({
  detail,
  onRefresh,
}: {
  detail: MemoryDetail | null;
  onRefresh: () => Promise<void>;
}) {
  const { actor, refreshShell } = useApp();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  if (!detail) {
    return (
      <Panel title="Memory detail">
        <Empty>Select a memory to inspect how it was captured, gated and used.</Empty>
      </Panel>
    );
  }

  const mem = detail.memory;
  const provenance = detail.provenance;

  async function act(path: string, label: string, body: Record<string, unknown> = {}) {
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<{ message?: string }>(path, { actor, ...body });
      setMessage(result.message ?? label);
      await onRefresh();
      await refreshShell();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title={mem.title}
      subtitle={`${mem.id} · v${mem.version}`}
      actions={
        <Chip tone={visibilityTone(mem.visibility)}>{mem.visibility}</Chip>
      }
    >
      <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
        <div className="space-y-2">
          <p className="text-[13px] leading-relaxed text-slate-300">{mem.content}</p>
          <div className="flex flex-wrap gap-1.5">
            <Chip tone={statusTone(mem.status)}>{mem.status}</Chip>
            <Chip tone={confidenceTone(detail.confidence.band)}>
              {pct(detail.confidence.score)} · {detail.confidence.band}
            </Chip>
            {mem.tags.map((t) => (
              <Chip key={t}>{t}</Chip>
            ))}
          </div>
        </div>

        <Block title="Provenance" subtitle="Where this came from and how much to trust it.">
          <dl className="space-y-1.5 text-[11px]">
            <Line label="source type" value={provenance?.source_type_label ?? "Unknown"} />
            <Line label="source" value={provenance?.source_name ?? mem.source_id} mono />
            <Line label="captured" value={shortTime(provenance?.captured_at ?? mem.created_at)} />
            <Line label="observed" value={shortTime(provenance?.observed_at ?? mem.observed_at)} />
            <Line label="hindsight fact" value={mem.hindsight_fact_id ?? "not retained"} mono />
          </dl>
          {provenance?.reliability_note && (
            <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
              {provenance.reliability_note}
            </p>
          )}
        </Block>

        {detail.lens && typeof detail.lens === "object" && "why_relevant" in detail.lens && (
          <Block title="Recall lens" subtitle="Why the retrieval engine surfaced this memory.">
            <p className="text-[12px] leading-relaxed text-slate-400">
              {(detail.lens as { why_relevant: string }).why_relevant}
            </p>
          </Block>
        )}

        {detail.gate && (
          <Block title="Memory gate" subtitle="Evaluated before anything was retained.">
            <div className="flex flex-wrap gap-1.5">
              <Chip
                tone={
                  detail.gate.decision === "STORE"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    : "border-rose-500/40 bg-rose-500/10 text-rose-300"
                }
              >
                {detail.gate.decision}
              </Chip>
              <Chip>{detail.gate.scope}</Chip>
              <Chip>{detail.gate.sensitivity}</Chip>
              <Chip>{detail.gate.retention_days}d retention</Chip>
            </div>
            <ul className="mt-2 space-y-0.5 text-[11px] text-slate-500">
              {detail.gate.reasons.map((r, i) => (
                <li key={i}>• {r}</li>
              ))}
            </ul>
          </Block>
        )}

        <Block title="Provenance">
          <dl className="space-y-1 text-[11px]">
            <Line label="source" value={`${mem.source_name} (${mem.source_type})`} />
            <Line label="owner" value={mem.owner} />
            <Line label="scope" value={mem.scope} />
            <Line label="observed" value={shortTime(mem.observed_at)} />
            <Line label="expires" value={shortTime(mem.expiry_at)} />
            <Line
              label="hindsight fact"
              value={mem.hindsight_fact_id ?? "—"}
              mono
            />
          </dl>
        </Block>

        {detail.excluded_scopes.length > 0 && (
          <Block title="Scope restrictions">
            <p className="text-[12px] text-amber-200">
              Not applicable to {detail.excluded_scopes.join(", ")}. The original text and history
              are preserved.
            </p>
          </Block>
        )}

        {detail.evidence.length > 0 && (
          <Block title={`Evidence (${detail.evidence.length})`}>
            <ul className="space-y-1.5">
              {detail.evidence.map((e, i) => (
                <li key={i} className="text-[11px]">
                  <span
                    className={
                      e.polarity === "supports"
                        ? "text-emerald-300"
                        : e.polarity === "contradicts"
                          ? "text-rose-300"
                          : "text-slate-500"
                    }
                  >
                    {e.polarity}
                  </span>{" "}
                  <span className="text-slate-400">{e.label}</span>
                  {e.detail && <p className="text-slate-600">{e.detail}</p>}
                </li>
              ))}
            </ul>
          </Block>
        )}

        {detail.contradictions.length > 0 && (
          <Block title="Contradictions">
            <ul className="space-y-1.5">
              {detail.contradictions.map((c) => (
                <li key={c.id} className="text-[11px] text-rose-200">
                  <div className="font-semibold">{c.status}</div>
                  <p className="text-slate-400">{c.reason}</p>
                </li>
              ))}
            </ul>
          </Block>
        )}

        <Block title="Confidence" subtitle={detail.confidence.disclaimer}>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-2xl font-semibold tabular-nums text-slate-50">
              {pct(detail.confidence.score)}
            </span>
            <Chip tone={confidenceTone(detail.confidence.band)}>
              {detail.confidence.band}
            </Chip>
          </div>
          <ul className="space-y-1.5">
            {detail.confidence.factors.map((f) => (
              <li key={f.key}>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">{f.label}</span>
                  <span className="tabular-nums text-slate-500">{pct(f.value)}</span>
                </div>
                <Bar value={f.value} />
              </li>
            ))}
          </ul>
        </Block>

        <Block title="History" subtitle="Every lifecycle change is kept.">
          <ol className="space-y-1.5">
            {detail.events.map((e) => (
              <li key={e.id} className="flex gap-2 text-[11px]">
                <span className="shrink-0 tabular-nums text-slate-600">
                  {shortTime(e.at)}
                </span>
                <span className="text-slate-300">{e.action.replace(/_/g, " ")}</span>
                {e.from_status && e.to_status && e.from_status !== e.to_status && (
                  <span className="text-slate-600">
                    {e.from_status} → {e.to_status}
                  </span>
                )}
                <span className="ml-auto shrink-0 text-slate-600">{e.actor}</span>
              </li>
            ))}
          </ol>
        </Block>

        <Block
          title="Actions"
          subtitle={`Promotion is never automatic. Only legal transitions from ${detail.lifecycle.status} are offered.`}
        >
          <div className="flex flex-wrap gap-2">
            {detail.promotable.options.map((option) => (
              <button
                key={option.target}
                className={option.allowed ? "btn-ghost" : "btn-subtle"}
                disabled={!option.allowed || busy}
                title={option.reason}
                onClick={() => {
                  void act(`/api/memories/${mem.id}/promote`, `promote to ${option.target}`, {
                    target: option.target,
                  });
                }}
              >
                Promote to {option.target}
              </button>
            ))}
            {detail.lifecycle.actions
              .filter((a) => !["review", "reject"].includes(a.action))
              .map((a) => (
                <button
                  key={a.action}
                  className={a.allowed ? "btn-ghost" : "btn-subtle"}
                  disabled={!a.allowed || busy}
                  title={a.reason}
                  onClick={() =>
                    void act(`/api/memories/${mem.id}/${a.action}`, a.action, {})
                  }
                >
                  {LABELS[a.action] ?? a.action}
                </button>
              ))}
          </div>
          <ul className="mt-2 space-y-0.5 text-[10px] text-slate-600">
            {detail.lifecycle.actions.map((a) => (
              <li key={a.action}>
                <span className={a.allowed ? "text-slate-500" : "text-slate-700 line-through"}>
                  {LABELS[a.action] ?? a.action}
                </span>{" "}
                — {a.reason}
              </li>
            ))}
            {detail.promotable.options.map((o) => (
              <li key={o.target}>
                <span className={o.allowed ? "text-slate-500" : "text-slate-700 line-through"}>
                  Promote to {o.target}
                </span>{" "}
                — {o.reason}
              </li>
            ))}
          </ul>
          {message && (
            <p className="mt-2 text-[11px] text-emerald-300">{message}</p>
          )}
          <div className="mt-2">
            <ErrorNote error={error} />
          </div>
        </Block>
      </div>
    </Panel>
  );
}

function Block({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2.5">
      <div className="label-xs">{title}</div>
      {subtitle && <div className="mb-1.5 mt-0.5 text-[10px] text-slate-600">{subtitle}</div>}
      <div className="mt-1">{children}</div>
    </section>
  );
}

function Line({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className={mono ? "truncate font-mono text-[10px] text-slate-400" : "text-slate-300"}>
        {value}
      </dd>
    </div>
  );
}

const LABELS: Record<string, string> = {
  review: "Confirm for review",
  reject: "Reject",
  validate: "Mark validated",
  restrict: "Restrict scope",
  expire: "Expire",
};

export type { MemoryCard };
