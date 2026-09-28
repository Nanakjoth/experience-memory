export type Visibility = "PERSONAL" | "TEAM" | "ORGANIZATION";
export type ConfidenceBand = "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH";
export type MemoryStatus =
  | "CREATED"
  | "ACTIVE"
  | "CONFIRMED"
  | "USED"
  | "SUPPORTED"
  | "OBSERVED"
  | "REVALIDATED"
  | "STALE"
  | "UPDATED"
  | "CONTRADICTED"
  | "ARCHIVED"
  | "REJECTED";

export interface LifecycleAction {
  action: "review" | "reject" | "validate" | "restrict" | "expire" | string;
  target: string | null;
  allowed: boolean;
  reason: string;
}

export interface Lifecycle {
  status: string;
  allowed_transitions: string[];
  actions: LifecycleAction[];
}

export interface MemoryCard {
  id: string;
  type: string;
  title: string;
  summary: string;
  content: string;
  source_type: string;
  source_id: string;
  source_name: string;
  scope: string;
  owner: string;
  domain: string;
  purpose: string;
  evidence_count: number;
  confidence: number;
  status: string;
  visibility: string;
  access_level: string;
  sensitivity: string;
  last_validated_at: string | null;
  observed_at: string | null;
  created_at: string;
  expiry_at: string | null;
  related_entities: string[];
  hindsight_fact_id: string | null;
  version: number;
  excluded_scopes: string[];
  tags: string[];
}

export interface MemoryList {
  total: number;
  count: number;
  offset: number;
  limit: number;
  withheld: { id: string; reason: string }[];
  items: MemoryCard[];
  filters: {
    types: string[];
    scopes: string[];
    sources: string[];
    statuses: string[];
    entities: string[];
    visibilities: string[];
  };
}

export interface ConfidenceFactor {
  key: string;
  label: string;
  weight: number;
  value: number;
  contribution: number;
  explanation: string;
}

export interface ConfidenceBreakdown {
  score: number;
  band: string;
  label: string;
  disclaimer: string;
  factors: ConfidenceFactor[];
  penalties: string[];
}

export interface MemoryEvent {
  id: string;
  memory_id: string;
  at: string;
  from_status: string | null;
  to_status: string | null;
  action: string;
  actor: string;
  note: string;
  payload: Record<string, unknown>;
}

export interface EvidenceLink {
  evidence_type: string;
  evidence_id: string;
  label: string;
  polarity: string;
  detail: string | null;
  created_at: string;
}

export interface Contradiction {
  id: string;
  memory_id: string;
  memory_title: string;
  memory_scope: string;
  conflicting_source_id: string;
  conflicting_source_type: string;
  conflicting_content: string;
  current_environment: string;
  detected_at: string;
  reason: string;
  status: string;
  resolution: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
}

export interface MemoryDetail {
  memory: MemoryCard;
  provenance: {
    source_type: string;
    source_type_label: string;
    source_id: string;
    source_name: string;
    captured_at: string;
    observed_at: string | null;
    reliability_note: string;
    hindsight_fact_id: string | null;
    hindsight_document_id: string | null;
    version: number;
  };
  gate: {
    decision: string;
    reasons: string[];
    purpose: string;
    scope: string;
    sensitivity: string;
    retention_days: number;
    authorization_required: boolean;
    future_useful: boolean;
    needs_persistent_memory: boolean;
    contains_secret: boolean;
    contains_personal_data: boolean;
  } | null;
  lens: LensItem | Record<string, unknown>;
  excluded_scopes: string[];
  evidence: EvidenceLink[];
  events: MemoryEvent[];
  confidence: ConfidenceBreakdown;
  previous_versions: { version: number; content: string }[];
  contradictions: Contradiction[];
  promotable: {
    by: string;
    options: { target: string; allowed: boolean; reason: string }[];
  };
  lifecycle: Lifecycle;
}

export interface TraceStep {
  step: string;
  value: string;
}

export interface AnswerSection {
  label: string;
  kind: "fact" | "experience" | "evidence" | "inference" | "recommendation" | string;
  points: string[];
}

export interface AskConfidenceFactor {
  key: string;
  label: string;
  score: number;
  band: string;
}

export interface AskConfidence {
  score: number;
  band: string;
  label: string;
  disclaimer: string;
  memories_used: number;
  evidence_total: number;
  factors: AskConfidenceFactor[];
  penalties: string[];
}

export interface OutOfScopeMemory {
  id: string;
  scope: string;
  title: string;
}

export interface AnswerScope {
  current_environment: string;
  memory_scopes: string[];
  in_scope: string[];
  out_of_scope: OutOfScopeMemory[];
}

export interface Answer {
  headline: string;
  sections: AnswerSection[];
  conflicts: Contradiction[];
  outdated_warning: string | null;
  reflect_text: string | null;
  reflect_mode: string;
  reflect_latency_ms: number;
  based_on: string[];
  confidence: AskConfidence;
  scope: AnswerScope;
  trace: TraceStep[];
  call_count: number;
}

export interface MemoryUsed {
  id: string;
  type: string;
  title: string;
  content: string;
  summary: string;
  source_type: string;
  source_id: string;
  source_name: string;
  captured_at: string;
  observed_at: string;
  created_at: string;
  last_validated_at: string | null;
  expiry_at: string | null;
  scope: string;
  owner: string;
  domain: string;
  purpose: string;
  evidence_count: number;
  confidence: number;
  status: string;
  sensitivity: string;
  access_level: string;
  visibility: string;
  related_entities: string[];
  related_memories: string[];
  hindsight_fact_id: string | null;
  hindsight_document_id: string | null;
  gate: MemoryDetail["gate"];
  human_confirmed: boolean;
  promoted_by: string | null;
  version: number;
  tags: string[];
  extra: Record<string, unknown> | null;
}

export interface LensSource {
  source_type: string;
  source_type_label: string;
  source_id: string;
  source_name: string;
  captured_at: string;
  observed_at: string | null;
  reliability_note: string;
  hindsight_fact_id: string | null;
  hindsight_document_id: string | null;
  version: number;
}

export interface LensItem {
  memory_id: string;
  title: string;
  content: string;
  type: string;
  source: LensSource;
  scope: string;
  environment_match: boolean;
  environment_note: string | null;
  status: string;
  last_validated_at: string | null;
  observed_at: string | null;
  evidence: EvidenceLink[];
  supporting_observations: number;
  confidence: ConfidenceBreakdown;
  why_relevant: string;
  contradictions: Contradiction[];
  relevance_score: number;
  hindsight_fact_id: string | null;
}

export interface WithheldMemory {
  id: string;
  title: string;
  visibility: string;
  reason: string;
}

export interface PrivacyNotice {
  withheld_count: number;
  items: WithheldMemory[];
}

export interface HindsightFact {
  id: string;
  text: string;
  type: string;
  context: string | null;
  document_id: string | null;
  chunk_id: string | null;
  mentioned_at: string | null;
  occurred_start: string | null;
  entities: string[];
  tags: string[];
  scores: Record<string, number>;
  metadata: Record<string, unknown>;
}

export interface AskRecallStats {
  fact_ids: string[];
  fact_types: string[];
  suppressed_fact_ids: string[];
  latency_ms: number;
  steps: TraceStep[];
  strategy_counts: Record<string, number>;
  recall: { operation: string; simulated: boolean; facts_stored: number; candidates_scored: number; engine: string };
}

export interface AskTrace {
  steps: TraceStep[];
  recall: AskRecallStats;
  reflect: TraceStep[];
  latency_ms: number;
  reflect_latency_ms: number;
  reflect_call_count: number;
  reflect_mode: string;
  engine_mode: string;
  engine_simulated: boolean;
  fact_ids: string[];
  fact_types: string[];
  suppressed_fact_ids: string[];
}

export interface AskResponse {
  question: string;
  asked_by: { id: string; display_name: string; role: string; team: string };
  at: string;
  answer: Answer;
  lens: LensItem[];
  memories_used: MemoryUsed[];
  hindsight_facts: HindsightFact[];
  withheld: WithheldMemory[];
  trace: AskTrace;
  warnings: string[];
  privacy_notice: PrivacyNotice;
  duration_ms: number;
  engine_mode: string;
  engine_simulated: boolean;
  request_id: string;
  fact_count: number;
  suppressed_fact_count: number;
  outdated: boolean;
  confidence: ConfidenceBreakdown;
}

export interface Actor {
  id: string;
  name: string;
  display_name: string;
  role: string;
  team: string;
  is_system: boolean;
  visibility_ceiling: string;
  can_read: Record<string, boolean>;
  can_promote: Record<string, boolean>;
  promotion_note?: string;
}

export interface ActorsResponse {
  default: string;
  current_environment: string;
  actors: Actor[];
}

export interface Metric {
  label: string;
  value: number;
  detail: string;
  synthetic: boolean;
  synthetic_label: string;
}

export interface LearningEvent {
  id: string;
  at: string;
  kind: string;
  message: string;
  detail: string;
  memory_id?: string;
  synthetic: boolean;
}

export interface RiskRow {
  system: string;
  system_id: string;
  owner: string;
  team: string;
  criticality: string;
  risk: "High" | "Medium" | "Low";
  knowledge_items: number;
  validated: number;
  personal_only: number;
  replacement_coverage: string;
  coverage_ratio: number;
  successor_ready: boolean;
  note?: string;
}

export interface Dashboard {
  statement: string;
  synthetic: boolean;
  synthetic_banner: string;
  synthetic_label: string;
  generated_at: string;
  metrics: Record<string, Metric>;
  recent_intelligence: LearningEvent[];
  knowledge_at_risk: RiskRow[];
  continuity: Record<string, unknown>;
  engine: Record<string, unknown>;
  narrative?: string;
}

export interface CapturePrompt {
  id: string;
  prompt: string;
}

export interface EvolutionPayload {
  contradictions: Contradiction[];
  memories: Record<string, unknown>[];
  timeline: Record<string, unknown>[];
  changes: Record<string, unknown>[];
  scope_drift: Record<string, unknown>[];
  graph: { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] };
}

export interface DemoStep {
  index: number;
  key: string;
  title: string;
  narration: string;
  status: "ok" | "error";
  error?: string;
  payload: unknown;
  ms: number;
}

export interface DemoRun {
  id: string;
  mode: string;
  status: string;
  started_at: string;
  finished_at: string;
  steps: DemoStep[];
  progress_percent: number;
  duration_ms: number;
}

export interface DemoState {
  memories: number;
  by_visibility: Record<string, number>;
  by_status: Record<string, number>;
  incidents: number;
  architecture_changes: {
    id: string;
    title: string;
    system: string;
    component: string;
    effective_at: string;
    summary: string;
    invalidates_scope: string | null;
  }[];
  open_contradictions: number;
  resolved_contradictions: number;
  current_environment: string;
  metrics: Record<string, number>;
  learning_events: LearningEvent[];
}

export interface AuditEvent {
  id: string;
  at: string;
  time: string;
  event_type: string;
  label: string;
  actor: string;
  actor_role: string;
  subject: string;
  memory_id: string | null;
  request_id: string | null;
  detail: string | null;
  payload: Record<string, unknown> | null;
}

export interface AuditResponse {
  events: AuditEvent[];
  count: number;
  event_types: string[];
  labels: Record<string, string>;
}

export interface GovernanceSummary {
  by_visibility: Record<string, number>;
  by_status: Record<string, number>;
  by_confidence: Record<string, number>;
  open_contradictions: number;
  resolved_contradictions: number;
  resolution_actions: Record<
    string,
    { label: string; description: string; resulting_status: string }
  >;
  policies: Record<
    string,
    {
      visibility: string;
      default_access_level: string;
      default_sensitivity: string;
      retention_days: number;
      requires_review: boolean;
      description: string;
    }
  >;
  promotion_rule?: string;
  retention_rule?: string;
}

export interface EngineInfo {
  health: {
    available: boolean;
    mode: string;
    label: string;
    bank_id: string;
    detail: string;
    version: string;
    simulated: boolean;
  };
  status: {
    memory_engine: string;
    bank_id: string;
    mode: string;
    simulated: boolean;
    degraded_reason: string | null;
    checked_at: string;
  };
  bank: {
    mission: string;
    directives: string[];
    disposition: Record<string, number>;
  };
  config: Record<string, unknown>;
}

export interface OutcomeResponse {
  outcome_id: string;
  memory_id: string;
  status: string;
  confidence: number;
  band: string;
  confidence_before: number;
  confidence_delta: number;
  evidence_count: number;
  contradiction: Contradiction | null;
  successful: boolean | null;
  verdict: { successful: boolean | null; source: string; rationale: string; cues: string[] };
  message: string;
  engine_mode: string;
  engine_simulated: boolean;
  linked_memories: string[];
  linked_detail: { id: string; title: string }[];
  reinforced: {
    id: string;
    title: string;
    status: string;
    confidence_before: number;
    confidence_after: number;
    confidence_delta: number;
    evidence_count: number;
  }[];
}

export interface CaptureResponse {
  source_id: string;
  retained: boolean;
  engine_mode: string;
  engine_simulated: boolean;
  memories: {
    id: string;
    title: string;
    type: string;
    visibility: string;
    status: string;
    confidence: number;
    content: string;
  }[];
  rejected: { reason: string; text: string; detail?: string }[];
  hindsight_fact_ids: string[];
  duration_ms: number;
}
