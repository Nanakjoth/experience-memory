import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { Actor, ActorsResponse, EngineInfo } from "./types";

interface AppState {
  actor: string;
  setActor: (id: string) => void;
  actors: Actor[];
  engine: EngineInfo | null;
  environment: string;
  refreshShell: () => Promise<void>;
}

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [actor, setActor] = useState("maya");
  const [actors, setActors] = useState<Actor[]>([]);
  const [engine, setEngine] = useState<EngineInfo | null>(null);
  const [environment, setEnvironment] = useState("—");
  const chosen = useRef(false);

  const refreshShell = useCallback(async () => {
    try {
      const [actorsBody, engineBody] = await Promise.all([
        api.get<ActorsResponse>("/api/actors"),
        api.get<EngineInfo>("/api/engine"),
      ]);
      setActors(actorsBody.actors);
      setEnvironment(actorsBody.current_environment);
      setEngine(engineBody);
      if (actorsBody.default && !chosen.current) setActor(actorsBody.default);
    } catch {
      /* the shell stays usable when the API is down */
    }
  }, []);

  const selectActor = useCallback((id: string) => {
    chosen.current = true;
    setActor(id);
  }, []);

  useEffect(() => {
    void refreshShell();
  }, [refreshShell]);

  const value = useMemo(
    () => ({ actor, setActor: selectActor, actors, engine, environment, refreshShell }),
    [actor, selectActor, actors, engine, environment, refreshShell],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const value = useContext(Ctx);
  if (!value) throw new Error("useApp must be used inside AppProvider");
  return value;
}
