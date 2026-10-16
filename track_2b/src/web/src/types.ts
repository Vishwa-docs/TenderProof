export type Conditions = Record<string, unknown> | string[] | string;
export interface Requirement {
  id: string;
  title: string;
  property: string;
  operator: string;
  value: string;
  unit: string;
  conditions: Conditions;
  phase: string;
  source_ids: string[];
  status: string;
  witness_question?: string;
  reviewer?: string;
}
export interface Fact {
  property: string;
  operator: string;
  value: string;
  unit: string;
  conditions: Conditions;
  source_ids: string[];
}
export interface Supplier {
  id: string;
  name: string;
  configuration: string | null;
  revision: string | null;
  serial: string | null;
  family: string | null;
  price_cents: number | null;
  currency: string | null;
  delivery_weeks: number | null;
  delivery_basis?: string | null;
  price_basis?: string | null;
  facts: Fact[];
  expedite_cents: number | null;
  rework_cents: number | null;
  original_data?: Record<string, unknown>;
  price_corrections?: PriceCorrection[];
}
export interface Assessment {
  requirement_id: string;
  supplier_id: string;
  status: string;
  reason: string;
  counterexample?: unknown;
  source_ids: string[];
}
export interface Evidence {
  id: string;
  title: string;
  supplier_id: string;
  kind: string;
  serial: string | null;
  family: string | null;
  configuration: string | null;
  revision: string | null;
  conditions: Conditions;
  measurements: unknown;
  source_ids: string[];
}
export interface SourceDocument {
  id: string;
  name: string;
  revision: string;
  sha256: string;
  language: string;
  authority: string;
  source_url?: string | null;
  parsing?: { page_count?: number | null } | null;
  spans: { id: string; page: number; text: string; bbox?: number[] }[];
}
export interface Decision {
  id: string;
  supplier_id: string;
  gate: "purchase" | "shipment";
  snapshot_hash: string;
  status: string;
  approvals: { actor: string; role: string; at: string }[];
  created_at: string;
  artifact: unknown;
}
export interface Proposal {
  id: string;
  kind: string;
  data: Record<string, unknown>;
  source_ids: string[];
  status: string;
  document_id: string;
  supplier_id?: string;
  original_data?: Record<string, unknown>;
  price_corrections?: PriceCorrection[];
}
export interface PriceCorrection {
  id: string;
  at: string;
  actor: string;
  document_id: string;
  source_id: string;
  page: number;
  reason: string;
  before: { price_cents: number | null; currency: string | null };
  after: { price_cents: number | null; currency: string | null };
}
export interface Project {
  id: string;
  name: string;
  customer: string;
  equipment: string;
  mode: string;
  proposals?: Proposal[];
  extraction_runs?: {
    id: string;
    document_id: string | null;
    kind: string | null;
    status: string;
    conditions: string[];
    trace: Record<string, unknown>;
  }[];
  required_delivery_week?: number | null;
  schedule_source_id?: string | null;
  snapshot_hash: string;
  version: number;
  requirements: Requirement[];
  suppliers: Supplier[];
  evidence: Evidence[];
  documents: SourceDocument[];
  assessments: Assessment[];
  comparisons: {
    supplier_id: string;
    status: string;
    total_cents: number | null;
    delivery_weeks: number | null;
    delivery_basis?: string | null;
    price_basis?: string | null;
    delay_weeks: number | null;
    issues: unknown[];
  }[];
  evidence_assessments: {
    evidence_id: string;
    supplier_id: string;
    status: string;
    reason: string;
    source_ids: string[];
  }[];
  decisions: Decision[];
  events: {
    id: string;
    at: string;
    actor: string;
    type: string;
    summary: string;
    details: unknown;
  }[];
}
export interface Health {
  status: string;
  mode: string;
  model: string;
  model_configured: boolean;
  workflow: string;
  database: string;
}

export type WorkbenchTarget =
  "requirements" | "suppliers" | "evidence" | "sources" | "workflow";
export interface ReviewIssue {
  id: string;
  type: string;
  severity: "blocking" | "review" | "info";
  title: string;
  detail: string;
  record_type: string;
  record_id: string;
  document_id: string | null;
  source_ids: string[];
  gates: string[];
  next_action: {
    label: string;
    target: WorkbenchTarget;
    record_id: string | null;
    document_id: string | null;
    source_id: string | null;
  };
}
export interface LineageNode {
  id: string;
  type: string;
  label: string;
  record_id: string;
  document_id: string | null;
  source_ids: string[];
}
export interface PackageAnalysis {
  project_id: string;
  snapshot_hash: string;
  version: number;
  summary: {
    document_count: number;
    span_count: number;
    requirement_count: number;
    pending_requirement_count: number;
    approved_requirement_count: number;
    pending_offer_count: number;
    pending_evidence_count: number;
    supplier_count: number;
    evidence_count: number;
    correction_count: number;
    issue_count: number;
    blocking_issue_count: number;
    approval_count: number;
    release_count: number;
  };
  release_gates: {
    gate: "purchase" | "shipment";
    status: "blocked" | "review_required";
    issue_ids: string[];
  }[];
  issues: ReviewIssue[];
  documents: {
    document_id: string;
    name: string;
    sha256: string;
    page_count: number | null;
    span_count: number;
    cited_span_count: number;
    citation_coverage: number;
    requirement_count: number;
    proposal_count: number;
    correction_count: number;
    extraction_run_count: number;
    pending_count: number;
    assurance_status: "recorded" | "incomplete" | "not_extracted";
  }[];
  lineage: {
    nodes: LineageNode[];
    edges: { source: string; target: string; relation: string }[];
    truncated: boolean;
    limit: number;
  };
}
export interface SourceSearchResponse {
  project_id: string;
  snapshot_hash: string;
  query: string;
  retrieval_method: string;
  score_meaning: string;
  limit: number;
  total_matches: number;
  results: {
    source_id: string;
    document_id: string;
    document_name: string;
    page: number;
    sha256: string;
    text: string;
    text_start: number;
    text_end: number;
    text_truncated: boolean;
    score: number;
    matched_terms: string[];
    context: {
      source_id: string;
      page: number;
      text: string;
      text_start: number;
      text_end: number;
      text_truncated: boolean;
    }[];
    duplicate_citations: {
      source_id: string;
      document_id: string;
      document_name: string;
      page: number;
      sha256: string;
    }[];
    duplicate_count: number;
  }[];
}
export interface SnapshotList {
  project_id: string;
  snapshot_hash: string;
  current_snapshot_hash: string;
  total_count: number;
  truncated: boolean;
  limit: number;
  snapshots: {
    snapshot_hash: string;
    version: number;
    is_current: boolean;
    created_at: string | null;
    summary: Record<string, number>;
  }[];
}
export interface SnapshotDiff {
  project_id: string;
  snapshot_hash: string;
  from_hash: string;
  to_hash: string;
  from_version: number;
  to_version: number;
  changed: boolean;
  summary: { added: number; removed: number; modified: number };
  changes: {
    collection: string;
    record_id: string;
    change: "added" | "removed" | "modified";
    label: string;
    fields: { path: string; before: unknown; after: unknown }[];
    source_ids: string[];
    document_ids: string[];
  }[];
  impacted_records: { type: string; id: string; source_ids: string[] }[];
  sensitive_content_omitted: boolean;
}
export interface ReviewDossier {
  schema_version: string;
  packet_type: "draft_review_dossier";
  status: "draft";
  meaning: string;
  project_id: string;
  snapshot_hash: string;
  version: number;
  packet_hash: string;
  summary: PackageAnalysis["summary"];
  release_gates: PackageAnalysis["release_gates"];
  issues: ReviewIssue[];
  source_catalog: Record<string, unknown>[];
  requirements: Record<string, unknown>[];
  proposals: Record<string, unknown>[];
  suppliers: Record<string, unknown>[];
  evidence: Record<string, unknown>[];
  corrections: Record<string, unknown>[];
  extraction_runs: Record<string, unknown>[];
  lineage: PackageAnalysis["lineage"];
  decisions: Record<string, unknown>[];
}
