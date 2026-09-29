import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Activity,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Gauge,
  History,
  MessageSquareWarning,
  Moon,
  PlayCircle,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Sun,
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

type Actor = { id: string; display_name: string; role: string; promotion_note?: string | null };

function ActorPicker({
  actor,
  setActor,
  actors,
}: {
  actor: string;
  setActor: (id: string) => void;
  actors: Actor[];
}) {
  const current = actors.find((a) => a.id === actor);
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2.5">
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
      {current?.promotion_note && (
        <p className="mt-1.5 text-[10px] leading-snug text-slate-500">
          {current.promotion_note}
        </p>
      )}
    </div>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const { actor, setActor, actors, engine } = useApp();
  const location = useLocation();
  const simulated = engine?.status.simulated ?? true;
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const current =
      document.documentElement.getAttribute("data-theme") === "dark"
        ? "dark"
        : "light";
    setTheme(current);
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("memoryos.theme", next);
    } catch {
      /* storage unavailable; theme still applies for this session */
    }
    setTheme(next);
  };
  const subtitle =
    typeof engine?.config?.app_subtitle === "string"
      ? engine.config.app_subtitle
      : "Knowledge Continuity for Organizations";

  return (
    <div className="flex min-h-full">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-hidden border-r border-slate-800 bg-slate-950 lg:flex">
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

        {/* Acting-as is the primary control of the whole demo (it drives
            permission filtering), so it is reachable from the top as well as
            the bottom of the sidebar. Both copies share one piece of state. */}
        <div className="px-4 pb-4">
          <ActorPicker actor={actor} setActor={setActor} actors={actors} />
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
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
          <ActorPicker actor={actor} setActor={setActor} actors={actors} />

          {/* Live/simulated indicator. Section 3 requires the UI to state which
              engine is active, so the dot and label are kept. Bank id and
              current scope were removed on request. */}
          <div className="flex items-center gap-1.5 px-1">
            <span
              className={clsx(
                "h-1.5 w-1.5 shrink-0 rounded-full",
                simulated ? "bg-amber-400" : "bg-emerald-400",
              )}
            />
            <span className="text-[11px] font-semibold text-slate-300">
              {engine?.health.label ?? "CHECKING"}
            </span>
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
            <p className="truncate text-[11px] text-slate-500">{subtitle}</p>
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
            <button
              type="button"
              onClick={toggleTheme}
              className="btn-ghost h-8 w-8 !px-0"
              title={
                theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
              }
              aria-label={
                theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
              }
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </button>
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
