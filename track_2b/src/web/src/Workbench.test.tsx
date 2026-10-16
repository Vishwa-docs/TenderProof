import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import App from "./App";
import type { Project } from "./types";

// Controlled UI QA responses based on actual public GPA-070-25 / OP34276 facts.
// These responses are isolated tests, never app data or claimed model inference.
// Source: https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf
const snapshot = "a".repeat(64);
const project = {
  id: "default",
  name: "GPA-070-25 · OP34276",
  customer: "Guam Power Authority",
  equipment: "750 kVA three-phase pad-mounted transformer",
  mode: "live",
  snapshot_hash: snapshot,
  version: 1,
  requirements: [
    {
      id: "qa-rating",
      title: "Rated capacity",
      property: "rated_power",
      operator: "eq",
      value: "750",
      unit: "kVA",
      conditions: {},
      phase: "purchase",
      source_ids: ["qa-po-page4"],
      status: "pending",
      witness_question:
        "Would 300 kVA meet a 750 kVA rated-capacity requirement?",
    },
  ],
  suppliers: [
    {
      id: "qa-eaglerise",
      name: "Eaglerise Electric & Electronic (China) Co.",
      configuration: "ZGSLB-750/13.8-0.208",
      revision: null,
      serial: null,
      family: null,
      price_cents: 3710550,
      currency: "USD",
      delivery_weeks: null,
      facts: [],
      expedite_cents: 0,
      rework_cents: 0,
    },
  ],
  evidence: [],
  documents: [
    {
      id: "qa-order",
      name: "OP34276.pdf",
      revision: "unreviewed",
      sha256:
        "da91f24252a7131e06a9861e56593a66146173bf0e8d0764f2194e6e63b8c551",
      language: "en",
      authority: "public_purchase_order",
      spans: [
        {
          id: "qa-po-page4",
          page: 4,
          text: "750 kVA Pad Mounted Transformer",
          bbox: [],
        },
      ],
    },
  ],
  assessments: [
    {
      requirement_id: "qa-rating",
      supplier_id: "qa-eaglerise",
      status: "unknown",
      reason: "Engineering interpretation has not been approved.",
      source_ids: ["qa-po-page4"],
    },
  ],
  comparisons: [
    {
      supplier_id: "qa-eaglerise",
      status: "conditional",
      total_cents: 3710550,
      delivery_weeks: null,
      delay_weeks: null,
      issues: ["Drawing-approval date has not been established."],
    },
  ],
  evidence_assessments: [],
  decisions: [] as {
    id: string;
    supplier_id: string;
    gate: string;
    snapshot_hash: string;
    status: string;
    approvals: { actor: string; role: string; at: string }[];
    created_at: string;
    artifact: unknown;
  }[],
  events: [],
  proposals: [] as {
    id: string;
    kind: string;
    data: unknown;
    source_ids: string[];
    status: string;
    document_id: string;
  }[],
  required_delivery_week: null,
  schedule_source_id: null,
};
const health = {
  status: "ok",
  mode: "live",
  model: "swiss-ai/Apertus-v1.5-8B",
  model_configured: false,
  workflow: "temporal",
  database: "postgresql",
};
function server(overrides: Partial<Project> = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url).includes("/health"))
      return new Response(JSON.stringify(health));
    if (!init?.method || init.method === "GET")
      return new Response(JSON.stringify({ ...project, ...overrides }));
    return new Response("{}");
  });
}
function priceCorrectionQA() {
  // Actual current OCR from abstract PDF page 3; transport is controlled QA.
  return {
    proposal: {
      id: "qa-benson-pending",
      kind: "supplier",
      status: "pending",
      document_id: "ea238725bcf796aa9df08ba0",
      source_ids: ["ea238725bcf796aa9df08ba0:35"],
      data: {
        name: "Benson Guam Enterprises Inc.",
        price_cents: 2500000,
        currency: "USD",
      },
    },
    document: {
      ...project.documents[0],
      id: "ea238725bcf796aa9df08ba0",
      name: "gpa-07025-bid-abstract.pdf",
      spans: [
        {
          id: "ea238725bcf796aa9df08ba0:35",
          page: 3,
          text: "25,000.00",
        },
      ],
    },
  };
}
beforeEach(() => sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

function previewTransport() {
  // One software-generated pixel for transport/UI lifecycle QA, not source data.
  const bytes = Uint8Array.from(
    atob(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0ioAAAAASUVORK5CYII=",
    ),
    (c) => c.charCodeAt(0),
  );
  const create = vi
    .fn()
    .mockReturnValueOnce("blob:qa-page-4")
    .mockReturnValueOnce("blob:qa-page-6");
  const revoke = vi.fn();
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = create;
      static revokeObjectURL = revoke;
    },
  );
  return {
    create,
    revoke,
    response: () =>
      new Response(bytes, { headers: { "Content-Type": "image/png" } }),
  };
}

const issue = {
  id: "issue-1",
  type: "pending_requirement",
  severity: "blocking",
  title: "Review rated capacity",
  detail: "The extracted capacity needs interpretation review.",
  record_type: "requirement",
  record_id: "qa-rating",
  document_id: "qa-order",
  source_ids: ["qa-po-page4"],
  gates: ["purchase", "shipment"],
  next_action: {
    label: "Review requirement",
    target: "requirements",
    record_id: "qa-rating",
    document_id: "qa-order",
    source_id: "qa-po-page4",
  },
};
const analysis = {
  project_id: "default",
  snapshot_hash: snapshot,
  version: 1,
  summary: {
    document_count: 1,
    span_count: 1,
    requirement_count: 1,
    pending_requirement_count: 1,
    approved_requirement_count: 0,
    pending_offer_count: 0,
    pending_evidence_count: 0,
    supplier_count: 1,
    evidence_count: 0,
    correction_count: 0,
    issue_count: 1,
    blocking_issue_count: 1,
    approval_count: 0,
    release_count: 0,
  },
  release_gates: [
    { gate: "purchase", status: "blocked", issue_ids: ["issue-1"] },
    { gate: "shipment", status: "blocked", issue_ids: ["issue-1"] },
  ],
  issues: [issue],
  documents: [
    {
      document_id: "qa-order",
      name: "OP34276.pdf",
      sha256: project.documents[0].sha256,
      page_count: 9,
      span_count: 1,
      cited_span_count: 1,
      citation_coverage: 1,
      requirement_count: 1,
      proposal_count: 0,
      correction_count: 0,
      extraction_run_count: 1,
      pending_count: 1,
      assurance_status: "incomplete",
    },
  ],
  lineage: {
    nodes: [
      {
        id: "document:qa-order",
        type: "document",
        label: "OP34276.pdf",
        record_id: "qa-order",
        document_id: "qa-order",
        source_ids: [],
      },
      {
        id: "requirement:qa-rating",
        type: "requirement",
        label: "Rated capacity",
        record_id: "qa-rating",
        document_id: null,
        source_ids: ["qa-po-page4"],
      },
    ],
    edges: [
      {
        source: "document:qa-order",
        target: "requirement:qa-rating",
        relation: "supports",
      },
    ],
    truncated: false,
    limit: 200,
  },
};
const searchResponse = {
  project_id: "default",
  snapshot_hash: snapshot,
  query: "750",
  retrieval_method: "BM25 lexical retrieval",
  score_meaning: "Lexical relevance; not confidence.",
  limit: 12,
  total_matches: 1,
  results: [
    {
      source_id: "qa-po-page4",
      document_id: "qa-order",
      document_name: "OP34276.pdf",
      page: 4,
      sha256: project.documents[0].sha256,
      text: project.documents[0].spans[0].text,
      text_start: 0,
      text_end: 34,
      text_truncated: false,
      score: 1.2,
      matched_terms: ["750"],
      context: [],
      duplicate_citations: [],
      duplicate_count: 0,
    },
  ],
};
const previousHash = "b".repeat(64);
function workbenchServer(overrides: Record<string, unknown> = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const key = new URL(String(url), "http://localhost").pathname
      .split("/")
      .at(-1)!;
    const values: Record<string, unknown> = {
      health,
      default: project,
      analysis,
      search: searchResponse,
      snapshots: {
        project_id: "default",
        snapshot_hash: snapshot,
        current_snapshot_hash: snapshot,
        total_count: 2,
        truncated: false,
        limit: 100,
        snapshots: [
          {
            snapshot_hash: snapshot,
            version: 2,
            is_current: true,
            created_at: null,
            summary: {},
          },
          {
            snapshot_hash: previousHash,
            version: 1,
            is_current: false,
            created_at: null,
            summary: {},
          },
        ],
      },
      diff: {
        project_id: "default",
        snapshot_hash: snapshot,
        from_hash: previousHash,
        to_hash: snapshot,
        from_version: 1,
        to_version: 2,
        changed: true,
        summary: { added: 0, removed: 0, modified: 1 },
        changes: [
          {
            collection: "requirements",
            record_id: "qa-rating",
            change: "modified",
            label: "Rated capacity",
            fields: [{ path: "value", before: "300", after: "750" }],
            source_ids: ["qa-po-page4"],
            document_ids: ["qa-order"],
          },
        ],
        impacted_records: [
          { type: "requirement", id: "qa-rating", source_ids: ["qa-po-page4"] },
        ],
        sensitive_content_omitted: true,
      },
      dossier: {
        schema_version: "1.0",
        packet_type: "draft_review_dossier",
        status: "draft",
        meaning: "Review packet; no release approval.",
        project_id: "default",
        snapshot_hash: snapshot,
        version: 1,
        packet_hash: "d".repeat(64),
        summary: analysis.summary,
        release_gates: analysis.release_gates,
        issues: [issue],
        source_catalog: project.documents,
        requirements: project.requirements,
        proposals: [],
        suppliers: project.suppliers,
        evidence: [],
        corrections: [],
        extraction_runs: [],
        lineage: analysis.lineage,
        decisions: [],
      },
      ...overrides,
    };
    return new Response(JSON.stringify(values[key] ?? {}));
  });
}
describe("evidence workbench", () => {
  it("opens an overview and routes a blocking issue to its actual requirement", async () => {
    workbenchServer();
    render(<App />);
    const user = userEvent.setup();
    expect(
      await screen.findByRole("heading", { name: "Package overview" }),
    ).toBeVisible();
    expect(await screen.findByText("Review rated capacity")).toBeVisible();
    await user.click(screen.getByRole("button", { name: /^Review issues/ }));
    const queue = within(screen.getByRole("dialog", { name: "Review issues" }));
    await user.click(queue.getByRole("button", { name: "Review requirement" }));
    expect(
      screen.getByRole("heading", { name: "Requirements review" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Approve requirement" }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("dialog", { name: "Review issues" }),
    ).not.toBeInTheDocument();
  });
  it("retrieves exact source text and opens its cited original-page action", async () => {
    const transport = workbenchServer();
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Evidence 02" }),
    );
    await user.type(screen.getByLabelText("Search source text"), "750");
    await user.click(screen.getByRole("button", { name: "Search sources" }));
    expect(
      await screen.findByText("750 kVA Pad Mounted Transformer"),
    ).toBeVisible();
    expect(screen.getByText("BM25 lexical retrieval")).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Inspect passage on page 4" }),
    );
    const inspector = within(screen.getByLabelText("Source inspector"));
    expect(
      inspector.getByText("750 kVA Pad Mounted Transformer"),
    ).toBeVisible();
    expect(
      inspector.getByRole("button", {
        name: "Preview original page 4 of OP34276.pdf",
      }),
    ).toBeEnabled();
    expect(
      transport.mock.calls.some(([u]) => String(u).includes("/search?q=750")),
    ).toBe(true);
  });
  it("reports no matching spans without inventing an answer", async () => {
    workbenchServer({
      search: { ...searchResponse, total_matches: 0, results: [] },
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Evidence 02" }),
    );
    await user.type(screen.getByLabelText("Search source text"), "unmatched");
    await user.click(screen.getByRole("button", { name: "Search sources" }));
    expect(
      await screen.findByText("No matching source passages"),
    ).toBeVisible();
    expect(
      screen.queryByText("750 kVA Pad Mounted Transformer"),
    ).not.toBeInTheDocument();
  });
  it("traverses actual document lineage into a linked requirement", async () => {
    workbenchServer();
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Evidence 02" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "View lineage for OP34276.pdf",
      }),
    );
    const lineage = within(
      screen.getByRole("region", { name: "Source lineage" }),
    );
    expect(lineage.getByText("supports")).toBeVisible();
    await user.click(
      lineage.getByRole("button", { name: "Open Rated capacity" }),
    );
    expect(
      screen.getByRole("heading", { name: "Requirements review" }),
    ).toBeVisible();
  });
  it("compares stored snapshots and exposes exact field changes", async () => {
    workbenchServer();
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Change history 06" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Compare snapshots" }),
    );
    const changes = within(
      await screen.findByRole("region", { name: "Snapshot changes" }),
    );
    expect(changes.getByText("Rated capacity")).toBeVisible();
    expect(changes.getByText("300")).toBeVisible();
    expect(changes.getByText("750")).toBeVisible();
    expect(
      changes.getByRole("button", { name: "Inspect changed record sources" }),
    ).toBeEnabled();
  });
  it("downloads a clearly labeled Markdown dossier using a read request", async () => {
    const transport = workbenchServer();
    const create = vi.fn().mockReturnValue("blob:dossier");
    vi.stubGlobal(
      "URL",
      class extends URL {
        static createObjectURL = create;
        static revokeObjectURL = vi.fn();
      },
    );
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Export Markdown" }),
    );
    await waitFor(() => expect(click).toHaveBeenCalled());
    expect((create.mock.calls[0][0] as Blob).type).toBe(
      "text/markdown;charset=utf-8",
    );
    expect(
      transport.mock.calls.filter(([u]) => String(u).endsWith("/dossier")),
    ).toHaveLength(1);
    expect(
      transport.mock.calls.every(
        ([, init]) => !init?.method || init.method === "GET",
      ),
    ).toBe(true);
  });
});

describe("snapshot integrity and unavailable reads", () => {
  it("keeps a blocked gate visible when no incomplete run exists", async () => {
    workbenchServer();
    render(<App />);
    expect(
      await screen.findByText("Purchase and shipment blocked"),
    ).toBeVisible();
    expect(
      screen.getByRole("region", { name: "Release status" }),
    ).toHaveTextContent("1 blocking issues");
  });
  it("rejects analysis from another snapshot", async () => {
    workbenchServer({ analysis: { ...analysis, snapshot_hash: previousHash } });
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The package changed",
    );
    expect(screen.queryByText("Review rated capacity")).not.toBeInTheDocument();
  });
  it("rejects search results from another snapshot", async () => {
    workbenchServer({
      search: { ...searchResponse, snapshot_hash: previousHash },
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Evidence 02" }),
    );
    await user.type(screen.getByLabelText("Search source text"), "750");
    await user.click(screen.getByRole("button", { name: "Search sources" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The package changed",
    );
    expect(
      screen.queryByText("750 kVA Pad Mounted Transformer"),
    ).not.toBeInTheDocument();
  });
  it("keeps the newest source query when an older request finishes later", async () => {
    const transport = workbenchServer();
    const original = transport.getMockImplementation()!;
    let completeOlder!: (value: Response) => void;
    transport.mockImplementation((url, init) => {
      if (String(url).includes("/search?q=750"))
        return new Promise<Response>((resolve) => {
          completeOlder = resolve;
        });
      if (String(url).includes("/search?q=unmatched"))
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ...searchResponse,
              query: "unmatched",
              results: [],
              total_matches: 0,
            }),
          ),
        );
      return original(url, init);
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Evidence 02" }),
    );
    const input = screen.getByLabelText("Search source text");
    await user.type(input, "750");
    await user.click(screen.getByRole("button", { name: "Search sources" }));
    await user.clear(input);
    await user.type(input, "unmatched");
    await user.click(screen.getByRole("button", { name: "Search sources" }));
    expect(
      await screen.findByText("No matching source passages"),
    ).toBeVisible();
    await act(async () =>
      completeOlder(new Response(JSON.stringify(searchResponse))),
    );
    expect(screen.getByText("No matching source passages")).toBeVisible();
    expect(
      screen.queryByText("750 kVA Pad Mounted Transformer"),
    ).not.toBeInTheDocument();
  });
  it("shows a failed search without substituting local source results", async () => {
    const transport = workbenchServer();
    const original = transport.getMockImplementation()!;
    transport.mockImplementation((url, init) =>
      String(url).includes("/search?")
        ? Promise.resolve(
            new Response(JSON.stringify({ detail: "Search is unavailable" }), {
              status: 503,
            }),
          )
        : original(url, init),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Evidence 02" }),
    );
    await user.type(screen.getByLabelText("Search source text"), "750");
    await user.click(screen.getByRole("button", { name: "Search sources" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Search is unavailable",
    );
    expect(
      screen.queryByRole("region", { name: "Source search results" }),
    ).not.toBeInTheDocument();
  });
  it("rejects a diff that belongs to another current package", async () => {
    workbenchServer({
      diff: {
        snapshot_hash: previousHash,
        from_hash: previousHash,
        to_hash: snapshot,
        changes: [],
        summary: { added: 0, removed: 0, modified: 0 },
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Change history 06" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Compare snapshots" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The package changed",
    );
    expect(
      screen.queryByRole("region", { name: "Snapshot changes" }),
    ).not.toBeInTheDocument();
  });
});
