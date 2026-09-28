import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Dashboard, RiskRow } from "../lib/types";
import { Chip, ErrorNote, Panel, Spinner, Stat } from "../components/ui";
import { shortTime } from "../lib/format";
import { useNavigate } from "react-router-dom";

export function Overview() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<unknown>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api.get<Dashboard>("/api/dashboard"));
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <Panel title="Overview">
        <ErrorNote error={error} />
      </Panel>
    );
  }
  if (!data) {
    return <Spinner label="Loading dashboard" />;
  }

  return (
    <div className="space-y-5">
      <Panel
        title={data.statement}
        subtitle={data.narrative}
        actions={
          <button className="btn-primary" onClick={() => navigate("/demo")}>
            Open the guided demo
          </button>
        }
      >
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {Object.values(data.metrics).map((metric) => (
            <Stat
              key={metric.label}
              label={metric.label}
              value={metric.value}
              detail={metric.detail}
              synthetic={metric.synthetic}
            />
          ))}
        </div>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Recent intelligence"
          subtitle="Real events recorded by the application, newest first."
        >
          {data.recent_intelligence.length === 0 ? (
            <p className="text-sm text-slate-500">
              Nothing yet. Run the guided demo, capture an interview, or ask a question.
            </p>
          ) : (
            <ol className="space-y-2.5">
              {data.recent_intelligence.slice(0, 14).map((event) => (
                <li key={event.id} className="flex gap-3">
                  <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] text-slate-200">{event.message}</span>
                      <Chip tone="border-slate-700 bg-slate-800 text-slate-500">
                        {event.kind.replace(/_/g, " ")}
                      </Chip>
                      <span className="text-[10px] text-slate-600">
                        {shortTime(event.at)}
                      </span>
                    </div>
                    {event.detail && (
                      <p className="mt-0.5 text-[11px] leading-snug text-slate-500">
                        {event.detail}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Panel>

        <Panel
          title="Knowledge at risk"
          subtitle="Systems whose operational knowledge still depends on a person."
          actions={
            <button className="btn-subtle" onClick={() => navigate("/risk")}>
              Open →
            </button>
          }
        >
          <RiskList rows={data.knowledge_at_risk ?? []} />
        </Panel>
      </div>
    </div>
  );
}

function RiskList({ rows }: { rows: RiskRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No risk data yet — capture an expert interview to see bus-factor analysis.
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li key={row.system_id} className="panel-tight px-3 py-2.5">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[13px] font-semibold text-slate-200">{row.system}</span>
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
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            {row.knowledge_items} knowledge items · {row.validated} validated · {row.personal_only}{" "}
            still personal to {row.owner}
          </p>
        </li>
      ))}
    </ul>
  );
}
