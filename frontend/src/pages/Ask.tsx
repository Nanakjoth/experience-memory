import { useCallback, useEffect, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../lib/appState";
import type { AskResponse } from "../lib/types";
import { Bar, Chip, ErrorNote, Panel, Spinner } from "../components/ui";
import { confidenceTone, pct, shortTime } from "../lib/format";

export function Ask() {
  const { actor, environment } = useApp();
  const [question, setQuestion] = useState(
    "Payment API is showing connection reset alerts. What should I do?",
  );
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    void api
      .get<{ questions: string[] }>("/api/ask/suggestions")
      .then((body) => setSuggestions(body.questions))
      .catch(() => setSuggestions([]));
  }, []);

  const ask = useCallback(
    async (text?: string) => {
      const q = (text ?? question).trim();
      if (!q) return;
      setBusy(true);
      setError(null);
      try {
        const body = await api.post<AskResponse>("/api/ask", {
          question: q,
          actor,
        });
        setAnswer(body);
      } catch (err) {
        setError(err);
      } finally {
        setBusy(false);
      }
    },
    [actor, question],
  );

  return (
    <div className="space-y-5">
      <Panel
        title="Ask as a successor engineer"
        subtitle="Answers are assembled from Hindsight recall. Personal memory is never returned through an organizational question."
      >
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input flex-1"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void ask();
            }}
            placeholder="Ask a question…"
          />
          <button className="btn-primary shrink-0" onClick={() => ask()} disabled={busy}>
            <Send className="h-4 w-4" />
            {busy ? "Thinking…" : "Ask"}
          </button>
        </div>
        {suggestions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuestion(s);
                  void ask(s);
                }}
                className="rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-[11px] text-slate-300 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <div className="mt-3">
          <ErrorNote error={error} />
        </div>
      </Panel>

      {!answer && !busy && (
        <Panel>
          <p className="text-sm text-slate-500">
            Ask a question to see how MemoryOS answers: the headline, the reasoning, the memories
            it actually used, the confidence breakdown, and anything it deliberately refused to
            apply because the environment changed.
          </p>
        </Panel>
      )}

      {busy && <Spinner label="Recalling organizational memory" />}

      {answer && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-5">
            <Panel
              title={answer.answer.headline}
              subtitle={`Asked by ${answer.asked_by.display_name} · ${answer.asked_by.team} · ${shortTime(answer.at)}`}
              actions={
                <div className="flex items-center gap-2">
                  {answer.outdated && (
                    <Chip tone="border-amber-500/40 bg-amber-500/10 text-amber-300">OUTDATED</Chip>
                  )}
                  <Chip
                    tone={
                      answer.engine_simulated
                        ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                        : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    }
                  >
                    {answer.engine_mode}
                  </Chip>
                </div>
              }
            >
              {answer.answer.outdated_warning && (
                <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-[13px] text-amber-200">
                  {answer.answer.outdated_warning}
                </div>
              )}

              <div className="space-y-4">
                {answer.answer.sections.map((section, i) => (
                  <div key={`${section.kind}-${i}`}>
                    <h3 className="label-xs text-cyan-400">{section.label}</h3>
                    <ul className="mt-1.5 space-y-1.5">
                      {section.points.map((p, j) => (
                        <li key={j} className="text-[13px] leading-relaxed text-slate-300">
                          {p}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              {answer.answer.reflect_text && (
                <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900/60 px-3.5 py-3">
                  <div className="label-xs flex items-center gap-1.5 text-slate-400">
                    <Sparkles className="h-3 w-3" />
                    Hindsight reflect · {answer.answer.reflect_mode} ·{" "}
                    {answer.answer.reflect_latency_ms} ms
                  </div>
                  <p className="mt-1.5 whitespace-pre-line text-[12px] leading-relaxed text-slate-400">
                    {answer.answer.reflect_text}
                  </p>
                </div>
              )}
            </Panel>

            {answer.answer.conflicts.length > 0 && (
              <Panel
                title="Contradictions held open in this answer"
                subtitle="The answer is evidence-backed and still refuses to be applied blindly."
              >
                <ul className="space-y-2">
                  {answer.answer.conflicts.map((c) => (
                    <li key={c.id} className="panel-tight px-3 py-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13px] font-semibold text-slate-200">{c.memory_title}</span>
                        <Chip tone="border-amber-500/40 bg-amber-500/10 text-amber-300">
                          {c.status.replace(/_/g, " ")}
                        </Chip>
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-slate-400">{c.reason}</p>
                      <div className="mt-1 text-[10px] text-slate-600">
                        scope {c.memory_scope} · running {c.current_environment} · from{" "}
                        {c.conflicting_source_id}
                      </div>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            <Panel
              title="Scope decision"
              subtitle={`Running environment: ${answer.answer.scope.current_environment}`}
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="label-xs text-emerald-400">In scope ({answer.answer.scope.in_scope.length})</div>
                  <p className="mt-1 text-[12px] text-slate-400">
                    {answer.answer.scope.in_scope.length === 0
                      ? "No memory is fully scoped to the running environment."
                      : answer.answer.scope.in_scope.length + " memories match the running environment."}
                  </p>
                </div>
                <div>
                  <div className="label-xs text-amber-400">
                    Scoped to a previous environment ({answer.answer.scope.out_of_scope.length})
                  </div>
                  <p className="mt-1 text-[12px] text-slate-400">
                    {answer.answer.scope.out_of_scope
                      .slice(0, 3)
                      .map((m) => m.title)
                      .join(" · ") || "None"}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel
              title="Memories used"
              subtitle={`${answer.memories_used.length} readable memories supported this answer`}
            >
              {answer.memories_used.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No organizational memory was used. The system said so instead of guessing.
                </p>
              ) : (
                <ul className="space-y-2.5">
                  {answer.memories_used.map((m) => (
                    <li key={m.id} className="panel-tight px-3 py-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13px] font-semibold text-slate-200">{m.title}</span>
                        <Chip tone="border-slate-700 bg-slate-800 text-slate-400">{m.source_id}</Chip>
                        <span className="text-[10px] tabular-nums text-slate-500">
                          confidence {pct(m.confidence)}
                        </span>
                        <span className="text-[10px] tabular-nums text-slate-500">
                          {m.evidence_count} evidence
                        </span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-[12px] text-slate-400">{m.content}</p>
                      <div className="mt-1 text-[10px] text-slate-600">
                        scope {m.scope} · {m.status} · {m.visibility} · {shortTime(m.observed_at)}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel
              title="Retrieval lens"
              subtitle="Why each memory was recalled, with provenance and reliability."
              actions={<Chip tone="border-slate-700 bg-slate-800 text-slate-400">{answer.lens.length} lenses</Chip>}
            >
              {answer.lens.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing passed the Memory Gate for this question.</p>
              ) : (
                <ul className="space-y-2.5">
                  {answer.lens.map((l) => (
                    <li key={l.memory_id} className="panel-tight px-3 py-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13px] font-semibold text-slate-200">{l.title}</span>
                        <Chip
                          tone={
                            l.environment_match
                              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                              : "border-amber-500/40 bg-amber-500/10 text-amber-300"
                          }
                        >
                          {l.environment_match ? "SCOPE MATCH" : "ENVIRONMENT DRIFT"}
                        </Chip>
                        <Chip tone={confidenceTone(l.confidence.band)}>
                          {l.confidence.band} {pct(l.confidence.score)}
                        </Chip>
                        <span className="text-[10px] tabular-nums text-slate-500">
                          score {l.relevance_score.toFixed(2)}
                        </span>
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-slate-400">{l.why_relevant}</p>
                      {l.environment_note && (
                        <p className="mt-1 text-[11px] text-amber-400/90">{l.environment_note}</p>
                      )}
                      <div className="mt-1 text-[10px] text-slate-600">
                        {l.source.source_type_label} · {l.source.source_id} · {l.source.reliability_note} ·{" "}
                        {l.supporting_observations} linked observation(s) · v{l.source.version}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>

          <div className="space-y-5">
            <Panel title="Answer confidence" subtitle={answer.answer.confidence.disclaimer}>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-semibold tabular-nums text-slate-50">
                  {pct(answer.answer.confidence.score)}
                </span>
                <Chip tone={confidenceTone(answer.answer.confidence.band)}>
                  {answer.answer.confidence.band}
                </Chip>
              </div>
              <dl className="mt-3 space-y-1 text-[11px]">
                <Row label="memories used" value={String(answer.answer.confidence.memories_used)} />
                <Row label="evidence total" value={String(answer.answer.confidence.evidence_total)} />
              </dl>
              <div className="mt-3 space-y-2">
                {answer.answer.confidence.factors.map((f) => (
                  <div key={f.key}>
                    <div className="flex items-center justify-between gap-2 text-[11px]">
                      <span className="truncate text-slate-400">{f.label}</span>
                      <span className="shrink-0 tabular-nums text-slate-500">{pct(f.score)}</span>
                    </div>
                    <Bar value={f.score} />
                  </div>
                ))}
              </div>
              {answer.answer.confidence.penalties.length > 0 && (
                <ul className="mt-3 space-y-1 border-t border-slate-800 pt-3 text-[11px] text-rose-300">
                  {answer.answer.confidence.penalties.map((p, i) => (
                    <li key={i}>• {p}</li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="How the answer was assembled" subtitle="The reasoning trace for this request.">
              <ol className="space-y-1.5">
                {answer.trace.steps.map((s, i) => (
                  <li key={i} className="flex gap-2 text-[12px]">
                    <span className="shrink-0 font-semibold text-cyan-400">{s.step}</span>
                    <span className="text-slate-400">{s.value}</span>
                  </li>
                ))}
              </ol>
            </Panel>

            <Panel
              title="Memory Gate"
              subtitle="Recalled by the engine, withheld from this answer."
            >
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-semibold text-slate-100">
                  {answer.suppressed_fact_count}
                </span>
                <span className="text-[11px] text-slate-500">
                  of {answer.fact_count} recalled facts suppressed
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {answer.trace.suppressed_fact_ids.slice(0, 10).map((id) => (
                  <span
                    key={id}
                    className="rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[10px] text-slate-500"
                  >
                    {id}
                  </span>
                ))}
              </div>
            </Panel>

            {answer.privacy_notice.withheld_count > 0 && (
              <Panel
                title="Withheld by the permission boundary"
                subtitle={`${answer.privacy_notice.withheld_count} memories are never visible here`}
              >
                <ul className="space-y-1.5">
                  {answer.privacy_notice.items.map((w) => (
                    <li key={w.id} className="text-[11px]">
                      <span className="font-semibold text-slate-300">{w.title}</span>{" "}
                      <span className="text-slate-500">({w.visibility})</span>
                      <p className="text-slate-500">{w.reason}</p>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            {answer.warnings.length > 0 && (
              <Panel title="Warnings">
                <ul className="space-y-1.5">
                  {answer.warnings.map((w, i) => (
                    <li key={i} className="text-[11px] leading-relaxed text-amber-300/90">
                      • {w}
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            <Panel title="Run metadata">
              <dl className="space-y-1.5 text-[11px]">
                <Row label="request id" value={answer.request_id} />
                <Row label="duration" value={`${answer.duration_ms} ms`} />
                <Row label="recall" value={`${answer.trace.latency_ms} ms`} />
                <Row label="reflect" value={`${answer.trace.reflect_latency_ms} ms`} />
                <Row label="reflect calls" value={String(answer.trace.reflect_call_count)} />
                <Row label="engine" value={answer.trace.engine_mode} />
                <Row label="environment" value={environment} />
              </dl>
            </Panel>
          </div>
        </div>
      )}

      {answer?.engine_simulated && (
        <p className="flex items-center gap-1.5 text-[11px] text-amber-500/80">
          <Sparkles className="h-3 w-3" />
          Answers are produced by the simulated Hindsight engine because no Hindsight server is
          running. The retain/recall/reflect contract is identical.
        </p>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="truncate font-mono text-[10px] text-slate-400">{value}</dd>
    </div>
  );
}
