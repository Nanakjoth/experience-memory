import { NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Gauge,
  History,
  MessageSquareWarning,
  PlayCircle,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import clsx from "clsx";
import { useApp } from "../lib/appState";

const NAV = [
  { to: "/", label: "Overview", icon: Gauge, end: true },
  { to: "/demo", label: "Guided Demo", icon: PlayCircle },
  { to: "/ask", label: "Ask MemoryOS", icon: MessageSquareWarning },
  { to: "/capture", label: "Capture Experience", icon: Upload },
  { to: "/memory", label: "Memory Center", icon: BookOpen },
  { to: "/evolution", label: "Memory Evolution", icon: History },
  { to: "/risk", label: "Knowledge at Risk", icon: Activity },
  { to: "/governance", label: "Governance", icon: ShieldCheck },
  { to: "/audit", label: "Audit", icon: ScrollText },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { actor, setActor, actors, engine, environment } = useApp();
  const location = useLocation();
  const simulated = engine?.status.simulated ?? true;

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950 lg:flex">
        <div className="px-5 py-5">
          <div className="flex items-center gap-2">
            <BrainCircuit className="h-6 w-6 text-cyan-400" />
            <div>
              <div className="text-sm font-bold tracking-tight text-slate-50">MemoryOS</div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500">
                Knowledge Continuity
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                  isActive
                    ? "bg-cyan-500/15 text-cyan-300"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200",
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-3 border-t border-slate-800 px-4 py-4">
          <div>
            <div className="label-xs">Acting as</div>
            <select
              className="input mt-1.5"
              value={actor}
              onChange={(e) => setActor(e.target.value)}
            >
              {actors.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.display_name} — {a.role}
                </option>
              ))}
            </select>
            {actors.find((a) => a.id === actor)?.promotion_note && (
              <p className="mt-1.5 text-[10px] leading-snug text-slate-500">
                {actors.find((a) => a.id === actor)?.promotion_note}
              </p>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2.5">
            <div className="flex items-center gap-1.5">
              <span
                className={clsx(
                  "h-1.5 w-1.5 rounded-full",
                  simulated ? "bg-amber-400" : "bg-emerald-400",
                )}
              />
              <span className="text-[11px] font-semibold text-slate-300">
                {engine?.health.label ?? "CHECKING"}
              </span>
            </div>
            <div className="mt-1 text-[10px] leading-snug text-slate-500">
              Bank {engine?.status.bank_id ?? "…"} · {environment}
            </div>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-slate-800 bg-slate-950/90 px-4 py-3 backdrop-blur lg:px-8">
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold text-slate-50">
              {NAV.find((n) => (n.end ? n.to === location.pathname : location.pathname.startsWith(n.to)))
                ?.label ?? "MemoryOS"}
            </h1>
            <p className="truncate text-[11px] text-slate-500">
              NovaTech · Engineering organizational memory prototype
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-300 sm:flex">
              <Sparkles className="h-3 w-3" />
              Synthetic demo data
            </span>
            <select
              className="input w-auto py-1.5 text-xs lg:hidden"
              value={actor}
              onChange={(e) => setActor(e.target.value)}
            >
              {actors.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.display_name}
                </option>
              ))}
            </select>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 lg:px-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>

        <footer className="border-t border-slate-800 px-4 py-4 lg:px-8">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-slate-600">
            <span className="flex items-center gap-1">
              <ClipboardList className="h-3 w-3" />
              All figures are synthetic prototype metrics, not production statistics.
            </span>
            <span className="flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" />
              Personal memory is never returned through organizational recall.
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}
