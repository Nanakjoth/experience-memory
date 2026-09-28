import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AuditResponse } from "../lib/types";
import { Chip, Empty, ErrorNote, Panel, Spinner } from "../components/ui";
import { shortTime } from "../lib/format";

const TONE: Record<string, string> = {
  memory_promoted: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300",
  memory_contradicted: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  memory_restricted: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  memory_rejected: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  memory_expired: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  outcome_recorded: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  permission_denied: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  environment_changed: "border-violet-500/40 bg-violet-500/10 text-violet-300",
  architecture_change: "border-violet-500/40 bg-violet-500/10 text-violet-300",
};

export function Audit() {
  const [data, setData] = useState<AuditResponse | null>(null);
  const [eventType, setEventType] = useState("");
  const [actor, setActor] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setData(
        await api.get<AuditResponse>("/api/audit", {
          event_type: eventType || undefined,
          actor: actor || undefined,
          limit: 300,
        }),
      );
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [eventType, actor]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Panel
      title="Audit trail"
      subtitle="Every lifecycle action, who took it, and against which memory."
      actions={
        <div className="flex flex-wrap gap-2">
          <select
            className="input w-52 py-1.5 text-xs"
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            aria-label="Event type"
          >
            <option value="">All event types</option>
            {(data?.event_types ?? []).map((t) => (
              <option key={t} value={t}>
                {data?.labels[t] ?? t}
              </option>
            ))}
          </select>
          <input
            className="input w-36 py-1.5 text-xs"
            placeholder="actor"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
          />
        </div>
      }
    >
      <div className="mb-3 flex items-center gap-3">
        <span className="text-[11px] text-slate-500">
          {data?.count ?? 0} events
          {busy ? " · loading…" : ""}
        </span>
        <ErrorNote error={error} />
      </div>

      {busy && !data ? (
        <Spinner label="Loading audit" />
      ) : !data || data.events.length === 0 ? (
        <Empty>No audit events match this filter.</Empty>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-[12px]">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] uppercase tracking-wider text-slate-500">
                <th className="py-2 pr-3 font-semibold">When</th>
                <th className="py-2 pr-3 font-semibold">Event</th>
                <th className="py-2 pr-3 font-semibold">Actor</th>
                <th className="py-2 pr-3 font-semibold">Subject</th>
                <th className="py-2 font-semibold">Detail</th>
              </tr>
            </thead>
            <tbody>
              {data.events.map((event) => (
                <tr
                  key={event.id}
                  onClick={() => setOpen(open === event.id ? null : event.id)}
                  className="cursor-pointer border-b border-slate-800/60 align-top hover:bg-slate-800/30"
                >
                  <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-slate-500">
                    {shortTime(event.at)}
                  </td>
                  <td className="py-2 pr-3">
                    <Chip tone={TONE[event.event_type]}>{event.label}</Chip>
                  </td>
                  <td className="py-2 pr-3 text-slate-400">
                    {event.actor}
                    {event.actor_role && (
                      <div className="text-[10px] text-slate-600">{event.actor_role}</div>
                    )}
                  </td>
                  <td className="py-2 pr-3 text-slate-300">
                    <div className="max-w-[220px] truncate">{event.subject}</div>
                    {event.memory_id && (
                      <div className="font-mono text-[10px] text-slate-600">
                        {event.memory_id}
                      </div>
                    )}
                  </td>
                  <td className="py-2 text-slate-400">
                    <div className="max-w-[420px] truncate">{event.detail ?? "—"}</div>
                    {open === event.id && event.payload && (
                      <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-950/80 p-2 text-[10px] text-slate-500">
                        {JSON.stringify(event.payload, null, 2)}
                      </pre>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
