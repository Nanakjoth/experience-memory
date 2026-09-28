import type { ReactNode } from "react";
import clsx from "clsx";

export function Panel({
  title,
  subtitle,
  actions,
  children,
  className,
  bodyClass,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClass?: string;
}) {
  return (
    <section className={clsx("panel flex flex-col", className)}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-4 border-b border-slate-800 px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold text-slate-100">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={clsx("px-4 py-4", bodyClass)}>{children}</div>
    </section>
  );
}

export function Chip({
  children,
  tone = "border-slate-700 bg-slate-800 text-slate-400",
  title,
}: {
  children: ReactNode;
  tone?: string;
  title?: string;
}) {
  return (
    <span className={clsx("chip", tone)} title={title}>
      {children}
    </span>
  );
}

export function Stat({
  label,
  value,
  detail,
  tone = "text-slate-100",
  synthetic,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
  tone?: string;
  synthetic?: boolean;
}) {
  return (
    <div className="panel-tight px-3.5 py-3">
      <div className="label-xs">{label}</div>
      <div className={clsx("mt-1 text-2xl font-semibold tabular-nums", tone)}>{value}</div>
      {detail && <div className="mt-1 text-[11px] leading-snug text-slate-500">{detail}</div>}
      {synthetic && (
        <div className="mt-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-500/80">
          Synthetic prototype metric
        </div>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 px-4 py-8 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
      {message}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-600 border-t-cyan-400" />
      {label}…
    </div>
  );
}

export function Bar({ value, tone = "bg-cyan-400" }: { value: number; tone?: string }) {
  const safe = Math.max(0, Math.min(1, value));
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className={clsx("h-full rounded-full transition-all", tone)}
        style={{ width: `${safe * 100}%` }}
      />
    </div>
  );
}
