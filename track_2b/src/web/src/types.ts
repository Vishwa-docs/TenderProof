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
  extraction_runs?: {id:string; document_id:string|null; kind:string|null; status:string; conditions:string[]; trace:Record<string,unknown>}[];
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
