import { useCallback, useEffect, useState } from "react";
import { Mic, Send } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../lib/appState";
import type { CapturePrompt, CaptureResponse } from "../lib/types";
import { Chip, ErrorNote, Panel, Spinner } from "../components/ui";
import { pct, visibilityTone } from "../lib/format";

const SAMPLE = `I have run 40+ queue restarts. Before restarting Payment API, check the dead-letter
queue depth. If it is above 80% wait for it to drain. If the consumer count is stuck, check
the settlement partner first — most of the time the partner is unhealthy, not us. I have
personally seen the settlement retry storm turn a routine restart into a duplicate payment
incident. My working rule: never change the consumer count during a settlement batch.`;

export function Capture() {
  const { actor, refreshShell } = useApp();
  const [text, setText] = useState("");
  const [prompts, setPrompts] = useState<CapturePrompt[]>([]);
  const [guide, setGuide] = useState<{ heading?: string; note?: string; visibility?: string }>({});
  const [result, setResult] = useState<CaptureResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    void api
      .get<{ heading?: string; note?: string; visibility_note?: string; prompts: CapturePrompt[] }>(
        "/api/capture/prompts",
      )
      .then((body) => {
        setPrompts(body.prompts ?? []);
        setGuide({ heading: body.heading, note: body.note, visibility: body.visibility_note });
      })
      .catch(() => setPrompts([]));
  }, []);

  const capture = useCallback(
    async (freeText: string) => {
      const answer = freeText.trim();
      if (!answer) return;
      setBusy(true);
      setError(null);
      try {
        setResult(
          await api.post<CaptureResponse>("/api/capture", {
            expert: actor === "arun" ? "Arun" : actor,
            scope: "Payment Queue v1",
            system: "Payment Platform",
            turns: [
              {
                prompt: "What do you check first, and what should a new engineer not do?",
                answer,
              },
            ],
          }),
        );
        await refreshShell();
      } catch (err) {
        setError(err);
      } finally {
        setBusy(false);
      }
    },
    [actor, refreshShell],
  );

  return (
    <div className="space-y-5">
      <Panel
        title="Capture an expert interview"
        subtitle="The Memory Gate runs first. Only approved claims reach Hindsight — rejected content is never retained."
      >
        <textarea
          className="input min-h-[170px] resize-y font-mono text-[12px]"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste what the expert said. First-person operational experience, exceptions to the runbook, escalation knowledge…"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className="btn-primary" onClick={() => capture(text)} disabled={busy}>
            <Send className="h-4 w-4" />
            {busy ? "Capturing…" : "Capture experience"}
          </button>
          <button className="btn-ghost" onClick={() => setText(SAMPLE)}>
            Use the sample interview
          </button>
          <span className="text-[11px] text-slate-600">
            Capturing as {actor} · new knowledge starts PERSONAL
          </span>
        </div>
        <div className="mt-3">
          <ErrorNote error={error} />
        </div>
      </Panel>

      {prompts.length > 0 && (
        <Panel
          title={guide.heading ?? "Prompts that extract what the runbook leaves out"}
          subtitle={guide.note}
        >
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {prompts.map((p) => (
              <li key={p.id} className="flex items-start gap-2 text-[12px] text-slate-400">
                <Mic className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-500/70" />
                {p.prompt}
              </li>
            ))}
          </ul>
          {guide.visibility && (
            <p className="mt-3 border-t border-slate-800 pt-2.5 text-[11px] text-amber-300/90">
              {guide.visibility}
            </p>
          )}
        </Panel>
      )}

      {busy && <Spinner label="Running the memory gate and retaining" />}

      {result && (
        <div className="space-y-5">
          <Panel
            title={
              result.retained
                ? `${result.memories.length} memory item(s) created from source ${result.source_id}`
                : "Nothing was retained"
            }
            subtitle={`engine ${result.engine_mode} · ${result.duration_ms} ms · ${result.hindsight_fact_ids.length} fact(s) in Hindsight`}
            actions={
              <Chip
                tone={
                  result.engine_simulated
                    ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                    : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                }
              >
                {result.engine_simulated ? "simulated" : "hindsight"}
              </Chip>
            }
          >
            {result.memories.length === 0 ? (
              <p className="text-sm text-slate-500">
                The gate rejected everything. Nothing was written to the memory engine — that is
                the intended behaviour, not a failure.
              </p>
            ) : (
              <ul className="space-y-2">
                {result.memories.map((m) => (
                  <li key={m.id} className="panel-tight px-3 py-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] font-semibold text-slate-200">{m.title}</span>
                      <Chip tone={visibilityTone(m.visibility)}>{m.visibility}</Chip>
                      <Chip>{m.type}</Chip>
                      <Chip>{m.status}</Chip>
                      <Chip>{pct(m.confidence)}</Chip>
                    </div>
                    <p className="mt-1 text-[12px] leading-relaxed text-slate-400">{m.content}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          {result.rejected.length > 0 && (
            <Panel
              title={`Rejected by the gate (${result.rejected.length})`}
              subtitle="This text was never retained into Hindsight."
            >
              <ul className="space-y-1.5">
                {result.rejected.map((r, i) => (
                  <li key={i} className="text-[12px]">
                    <span className="text-rose-300">{r.reason}</span>
                    <p className="text-slate-500">{r.text}</p>
                  </li>
                ))}
              </ul>
            </Panel>
          )}

          <Panel
            title="Hindsight fact ids"
            subtitle="Proof that only approved claims reached the memory engine."
          >
            <div className="flex flex-wrap gap-1.5">
              {result.hindsight_fact_ids.map((id) => (
                <Chip key={id}>{id}</Chip>
              ))}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
