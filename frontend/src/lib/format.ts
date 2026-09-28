export function confidenceTone(band?: string): string {
  switch (band) {
    case "VERY_HIGH":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
    case "HIGH":
      return "border-cyan-500/40 bg-cyan-500/10 text-cyan-300";
    case "MEDIUM":
      return "border-amber-500/40 bg-amber-500/10 text-amber-300";
    default:
      return "border-rose-500/40 bg-rose-500/10 text-rose-300";
  }
}

export function visibilityTone(visibility?: string): string {
  switch (visibility) {
    case "ORGANIZATION":
      return "border-cyan-500/40 bg-cyan-500/10 text-cyan-300";
    case "TEAM":
      return "border-violet-500/40 bg-violet-500/10 text-violet-300";
    case "PERSONAL":
      return "border-amber-500/40 bg-amber-500/10 text-amber-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-400";
  }
}

export function statusTone(status?: string): string {
  switch (status) {
    case "USED":
    case "ACTIVE":
    case "REVALIDATED":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
    case "SUPPORTED":
    case "CONFIRMED":
      return "border-cyan-500/40 bg-cyan-500/10 text-cyan-300";
    case "STALE":
    case "RESTRICTED":
    case "EXPIRED":
      return "border-amber-500/40 bg-amber-500/10 text-amber-300";
    case "CONTRADICTED":
    case "REJECTED":
      return "border-rose-500/40 bg-rose-500/10 text-rose-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-400";
  }
}

export function bandFor(score: number): string {
  if (score >= 0.85) return "VERY_HIGH";
  if (score >= 0.65) return "HIGH";
  if (score >= 0.45) return "MEDIUM";
  return "LOW";
}

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function shortTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeOnly(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function titleCase(value?: string | null): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split(/[\s_]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function sentence(value?: string | null): string {
  if (!value) return "—";
  const text = value.replace(/_/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}
