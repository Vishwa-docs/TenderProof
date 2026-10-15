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

describe("live engineering workspace", () => {
  it.each(["unit", "lot_total", null])("shows currency and explicit price basis %s with a neutral heading", async (basis) => {
    server({suppliers:[{...project.suppliers[0],price_basis:basis}]});
    const user=userEvent.setup();render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button",{name:"Supplier comparison 02"}));
    const row=screen.getByRole("row",{name:/Documented price/});
    expect(row).toHaveTextContent("USD");
    expect(row).toHaveTextContent(basis==="unit"?"Per unit":basis==="lot_total"?"Lot total":"Price basis not stated");
    expect(screen.queryByRole("columnheader",{name:"Documented unit price"})).not.toBeInTheDocument();
  });
  it("keeps source-specific extraction assurance visible beside review and gate controls", async () => {
    server({requirements:project.requirements.map(r=>({...r,status:"approved"})), extraction_runs:[{
      id:"qa-incomplete-run",document_id:"qa-order",kind:"requirements",status:"incomplete",
      conditions:["Audit failed: adversarial challenger (window 1).","1 model row rejected."],
      trace:{audit_failures:[{trace_id:"qa-failed-audit"}],coverage:{all_original_spans_present:true},issues:[]}
    }]});
    const user=userEvent.setup();render(<App />);await screen.findByText("Rated capacity");
    for (const workspace of [null,"Supplier comparison 02","Acceptance & release 03"]) {
      if(workspace) await user.click(screen.getByRole("button",{name:workspace}));
      const assurance=screen.getByRole("region",{name:"Extraction assurance"});
      expect(assurance).toHaveTextContent("OP34276.pdf");
      expect(assurance).toHaveTextContent("qa-incomplete-run");
      expect(assurance).toHaveTextContent("Audit failed: adversarial challenger (window 1).");
      expect(assurance).toHaveTextContent("1 model row rejected.");
    }
    expect(screen.getByRole("button",{name:"New gate review"})).toBeDisabled();
  });

  it("has no demonstration roles or fabricated project controls", async () => {
    const request = server();
    render(<App />);
    await screen.findByText("Rated capacity");
    expect(screen.queryByLabelText("Demo role")).not.toBeInTheDocument();
    expect(screen.queryByText("Reset demo")).not.toBeInTheDocument();
    expect(screen.queryByText(/Synthetic case/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect token" })).toBeVisible();
    expect(
      request.mock.calls.every(
        ([, init]) =>
          !JSON.stringify(init?.headers || {}).includes("X-Demo-Role"),
      ),
    ).toBe(true);
  });
  it("requires an explicit witness answer and binds approval to the current snapshot", async () => {
    const request = server();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Review requirement Rated capacity" }),
    );
    expect(
      screen.getByRole("button", { name: "Approve requirement" }),
    ).toBeDisabled();
    await user.click(screen.getByLabelText("No"));
    await user.click(
      screen.getByRole("button", { name: "Approve requirement" }),
    );
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default/requirements/qa-rating/review",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            snapshot_hash: snapshot,
            accepted: true,
            witness_answer: false,
          }),
        }),
      ),
    );
  });
  it("opens the exact source and actual page reference", async () => {
    server();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", {
        name: "Inspect sources for Rated capacity",
      }),
    );
    expect(
      within(screen.getByLabelText("Source inspector")).getByText(
        "750 kVA Pad Mounted Transformer",
      ),
    ).toBeVisible();
    expect(screen.getByText("Page 4")).toBeVisible();
  });
  it("distinguishes an actual Docling image notice from source text and exposes original provenance", async () => {
    // Exact unavailable-image span observed in the real 57-page GPA source.
    const marker =
      "<!-- 🖼️❌ Image not available. Please use `PdfPipelineOptions(generate_picture_images=True)` -->";
    const sourceUrl =
      "https://www.ppa.org.fj/wp-content/uploads/2025/08/220825GPA-GPA-070-25-with-Amendment-I.pdf";
    const document = {
      ...project.documents[0],
      id: "a101432f314d0839c3d11477",
      name: "gpa-07025-full-ifb-amendment-i.pdf",
      sha256:
        "a101432f314d0839c3d114779f42b03e7b08766476a78eb817074ea7d1f01d10",
      source_url: sourceUrl,
      parsing: { page_count: 57 },
      spans: [
        { id: "a101432f314d0839c3d11477:1", page: 1, text: marker },
        ...project.documents[0].spans,
      ],
    };
    server({
      documents: [document],
      requirements: [
        {
          ...project.requirements[0],
          source_ids: ["a101432f314d0839c3d11477:1"],
        },
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", {
        name: /gpa-07025-full-ifb-amendment-i.pdf.*Rev/,
      }),
    );
    const inspector = within(screen.getByLabelText("Source inspector"));
    const notice = inspector.getByText(
      "Image content was not extracted. Inspect the original document.",
    );
    expect(notice).toBeVisible();
    expect(notice.closest("blockquote")).toBeNull();
    expect(inspector.queryByText(marker)).not.toBeInTheDocument();
    expect(inspector.getByText("57")).toBeVisible();
    expect(inspector.getByText("Pages")).toBeVisible();
    expect(inspector.getByRole("link", { name: sourceUrl })).toHaveAttribute(
      "href",
      sourceUrl,
    );
    expect(
      inspector.getByRole("button", { name: "Download original" }),
    ).toBeEnabled();
    expect(inspector.getByText("750 kVA Pad Mounted Transformer").tagName).toBe(
      "BLOCKQUOTE",
    );
    expect(inspector.getByText("a101432f314d0839c3d11477:1")).toBeVisible();
    await user.click(
      screen.getByRole("button", {
        name: "Inspect sources for Rated capacity",
      }),
    );
    expect(
      inspector.getByText(
        "Image content was not extracted. Inspect the original document.",
      ),
    ).toBeVisible();
    expect(inspector.getByText("Extraction notice")).toBeVisible();
    expect(inspector.queryByText("Exact source text")).not.toBeInTheDocument();
    expect(document.spans[0].text).toBe(marker);
  });
  it("does not infer an original URL or page count from available source spans", async () => {
    server();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: /OP34276.pdf.*Rev/ }));
    const inspector = within(screen.getByLabelText("Source inspector"));
    expect(inspector.queryByText("Pages")).not.toBeInTheDocument();
    expect(inspector.queryByText("Source URL")).not.toBeInTheDocument();
    expect(inspector.getByText("Page 4")).toBeVisible();
  });
  it("lazily loads the cited original PDF page with auth and releases images when switching or closing", async () => {
    sessionStorage.setItem("tenderproof-token", "qa-preview-token");
    const transport = previewTransport();
    const request = server({
      documents: [{ ...project.documents[0], parsing: { page_count: 9 } }],
    });
    const original = request.getMockImplementation()!;
    request.mockImplementation(async (url, init) =>
      String(url).includes("/preview")
        ? transport.response()
        : original(url, init),
    );
    const user = userEvent.setup();
    const app = render(<App />);
    await screen.findByText("Rated capacity");
    expect(
      request.mock.calls.filter(([url]) => String(url).includes("/preview")),
    ).toHaveLength(0);
    await user.click(
      screen.getByRole("button", {
        name: "Inspect sources for Rated capacity",
      }),
    );
    expect(
      request.mock.calls.filter(([url]) => String(url).includes("/preview")),
    ).toHaveLength(0);
    await user.click(
      screen.getByRole("button", {
        name: "Preview original page 4 of OP34276.pdf",
      }),
    );
    expect(
      await screen.findByRole("img", {
        name: "Original PDF page 4 of OP34276.pdf",
      }),
    ).toHaveAttribute("src", "blob:qa-page-4");
    expect(request).toHaveBeenCalledWith(
      "/api/projects/default/documents/qa-order/pages/4/preview?max_dimension=1800",
      expect.objectContaining({
        headers: { Authorization: "Bearer qa-preview-token" },
        signal: expect.any(AbortSignal),
      }),
    );
    await user.click(screen.getByRole("button", { name: "Zoom 2×" }));
    expect(screen.getByRole("button", { name: "Fit width" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const page = screen.getByLabelText("Original PDF page");
    await user.clear(page);
    await user.type(page, "6");
    await user.click(screen.getByRole("button", { name: "View page" }));
    expect(
      await screen.findByRole("img", {
        name: "Original PDF page 6 of OP34276.pdf",
      }),
    ).toHaveAttribute("src", "blob:qa-page-6");
    expect(transport.revoke).toHaveBeenCalledWith("blob:qa-page-4");
    expect(
      request.mock.calls.filter(([url]) => String(url).includes("/preview")),
    ).toHaveLength(2);
    await user.click(
      screen.getByRole("button", { name: "Close source inspector" }),
    );
    expect(transport.revoke).toHaveBeenCalledWith("blob:qa-page-6");
    app.unmount();
  });
  it("aborts an unfinished page preview and ignores its late response after closing", async () => {
    const transport = previewTransport();
    let complete!: (response: Response) => void;
    const request = server();
    const original = request.getMockImplementation()!;
    request.mockImplementation(async (url, init) =>
      String(url).includes("/preview")
        ? new Promise<Response>((resolve) => {
            complete = resolve;
          })
        : original(url, init),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: /OP34276.pdf.*Rev/ }));
    await user.click(
      screen.getByRole("button", {
        name: "Preview original page 1 of OP34276.pdf",
      }),
    );
    expect(
      screen.getByRole("status", { name: "Page preview loading" }),
    ).toBeVisible();
    const call = request.mock.calls.find(([url]) =>
      String(url).includes("/preview"),
    )!;
    await user.click(
      screen.getByRole("button", { name: "Close page preview" }),
    );
    expect(call[1]?.signal?.aborted).toBe(true);
    await act(async () => complete(transport.response()));
    expect(transport.create).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("img", { name: /Original PDF page/ }),
    ).not.toBeInTheDocument();
  });
  it("shows missing-original preview failure without substituting extracted text as an image", async () => {
    const transport = previewTransport();
    const request = server();
    const original = request.getMockImplementation()!;
    request.mockImplementation(async (url, init) =>
      String(url).includes("/preview")
        ? new Response(
            JSON.stringify({ detail: "The original PDF is unavailable." }),
            { status: 404 },
          )
        : original(url, init),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: /OP34276.pdf.*Rev/ }));
    await user.click(
      screen.getByRole("button", {
        name: "Preview original page 1 of OP34276.pdf",
      }),
    );
    const preview = within(
      screen.getByRole("region", { name: "Original PDF page preview" }),
    );
    expect(await preview.findByRole("alert")).toHaveTextContent(
      "The original PDF is unavailable.",
    );
    expect(preview.queryByRole("img")).not.toBeInTheDocument();
    expect(transport.create).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Download original" }),
    ).toBeEnabled();
    expect(
      within(screen.getByLabelText("Source inspector")).getByText(
        "750 kVA Pad Mounted Transformer",
      ),
    ).toBeVisible();
  });
  it("shows an API failure without replacing it with any case data", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async () =>
        new Response(JSON.stringify({ detail: "Project is unavailable" }), {
          status: 503,
        }),
    );
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Project is unavailable",
    );
    expect(screen.queryByText("Rated capacity")).not.toBeInTheDocument();
  });
  it("requires explicit project scope before approval or extraction", async () => {
    server({ equipment: "" });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    expect(
      screen.getByText(/Set project details before extraction or approval/),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Review requirement Rated capacity" }),
    );
    await user.click(screen.getByLabelText("No"));
    expect(
      screen.getByRole("button", { name: "Approve requirement" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /OP34276.pdf.*Rev/ }));
    expect(
      screen.getByRole("button", { name: "Extract with Apertus" }),
    ).toBeDisabled();
  });
  it("saves real project metadata with PATCH and the displayed snapshot", async () => {
    const request = server({ name: "", customer: "", equipment: "" });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: "Project details" }));
    expect(
      screen.getByRole("button", { name: "Save project details" }),
    ).toBeDisabled();
    await user.type(
      screen.getByLabelText("Project name"),
      "GPA-070-25 · OP34276",
    );
    await user.type(screen.getByLabelText("Customer"), "Guam Power Authority");
    await user.type(
      screen.getByLabelText("Equipment scope"),
      "750 kVA three-phase pad-mounted transformer",
    );
    await user.click(
      screen.getByRole("button", { name: "Save project details" }),
    );
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            snapshot_hash: snapshot,
            name: "GPA-070-25 · OP34276",
            customer: "Guam Power Authority",
            equipment: "750 kVA three-phase pad-mounted transformer",
          }),
        }),
      ),
    );
  });
  it("uses bearer authentication and never sends a role header", async () => {
    const request = server();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: "Connect token" }));
    await user.type(screen.getByLabelText("Access token"), "qa-auth-token");
    await user.click(screen.getByRole("button", { name: "Connect" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default",
        expect.objectContaining({
          headers: { Authorization: "Bearer qa-auth-token" },
        }),
      ),
    );
    expect(
      request.mock.calls.every(
        ([, init]) =>
          !JSON.stringify(init?.headers || {}).includes("X-Demo-Role"),
      ),
    ).toBe(true);
  });
  it("sends extraction kind and the selected supplier with the current scope snapshot", async () => {
    const request = server();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: /OP34276.pdf.*Rev/ }));
    await user.selectOptions(
      screen.getByLabelText("Extraction purpose"),
      "evidence",
    );
    await user.selectOptions(
      screen.getByLabelText("Evidence supplier"),
      "qa-eaglerise",
    );
    await user.click(
      screen.getByRole("button", { name: "Extract with Apertus" }),
    );
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default/documents/qa-order/extract",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            snapshot_hash: snapshot,
            kind: "evidence",
            supplier_id: "qa-eaglerise",
          }),
        }),
      ),
    );
  });
  it("preserves a released immutable record when the current decision is stale", async () => {
    server({
      decisions: [
        {
          id: "qa-decision",
          supplier_id: "qa-eaglerise",
          gate: "purchase",
          snapshot_hash: "c".repeat(64),
          status: "stale",
          approvals: [],
          created_at: "2025-10-13T00:00:00Z",
          artifact: { source: "OP34276" },
        },
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Acceptance & release 03" }),
    );
    expect(screen.getByText("Prototype release · ERP simulator")).toBeVisible();
    expect(
      screen.getByText(
        "Checks cover reviewed encoded numeric requirements; unencoded obligations require engineering review.",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Download record" }),
    ).toBeEnabled();
    expect(
      screen.queryByRole("button", { name: "Release record" }),
    ).not.toBeInTheDocument();
  });
  it("reads original content through the authenticated API and surfaces failures", async () => {
    const request = server();
    const original = request.getMockImplementation()!;
    request.mockImplementation(async (url, init) =>
      String(url).endsWith("/content")
        ? new Response(
            JSON.stringify({ detail: "Original document unavailable" }),
            { status: 404 },
          )
        : original(url, init),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button", { name: /OP34276.pdf.*Rev/ }));
    await user.click(screen.getByRole("button", { name: "Download original" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Original document unavailable",
    );
    expect(request).toHaveBeenCalledWith(
      "/api/projects/default/documents/qa-order/content",
      expect.objectContaining({ headers: {} }),
    );
  });
  it("shows actual empty workspaces until uploaded sources exist", async () => {
    server({
      requirements: [],
      suppliers: [],
      documents: [],
      assessments: [],
      comparisons: [],
      name: "",
      customer: "",
      equipment: "",
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("No requirements yet");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    expect(screen.getByText("No supplier configurations yet")).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Acceptance & release 03" }),
    );
    expect(
      screen.getByRole("button", { name: "New gate review" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Change history 04" }));
    expect(
      screen.queryByRole("button", { name: /amendment|reset|correction/i }),
    ).not.toBeInTheDocument();
  });
  it("keeps another review locked until a snapshot mutation finishes", async () => {
    const request = server({
      requirements: [
        ...project.requirements,
        {
          ...project.requirements[0],
          id: "qa-voltage",
          title: "Primary voltage",
          witness_question: "",
        },
      ],
    });
    const original = request.getMockImplementation()!;
    let complete: ((value: Response) => void) | undefined;
    request.mockImplementation(async (url, init) =>
      String(url).includes("/review")
        ? new Promise<Response>((resolve) => {
            complete = resolve;
          })
        : original(url, init),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Review requirement Rated capacity" }),
    );
    await user.click(screen.getByLabelText("No"));
    await user.click(
      screen.getByRole("button", { name: "Approve requirement" }),
    );
    expect(
      screen.getByRole("button", {
        name: "Review requirement Primary voltage",
      }),
    ).toBeDisabled();
    complete?.(new Response("{}"));
    await waitFor(() =>
      expect(
        screen.getByRole("button", {
          name: "Review requirement Primary voltage",
        }),
      ).toBeEnabled(),
    );
  });
  it("counts source-linked supplier proposals and leaves each offer for separate review", async () => {
    const pending = [
      {
        id: "qa-bid-rd",
        kind: "supplier",
        data: {
          name: "R&D Marketing",
          price_cents: 3710550,
          revision: null,
          serial: null,
        },
        source_ids: ["qa-bid-page1"],
        status: "pending",
        document_id: "qa-bid-abstract",
      },
      {
        id: "qa-bid-benson",
        kind: "supplier",
        data: {
          name: "Benson Guam Enterprises Inc.",
          price_cents: 2560000,
          revision: null,
          serial: null,
        },
        source_ids: ["qa-bid-page3"],
        status: "pending",
        document_id: "qa-bid-abstract",
      },
    ];
    // QA transport controls only. Actual bidder prices come from the public
    // bid abstract (PDF pages 1 and 3); no inference claim is made by this test.
    const bidDoc = {
      ...project.documents[0],
      id: "qa-bid-abstract",
      name: "GPA-070-25 Bid Abstract.pdf",
      spans: [
        {
          id: "qa-bid-page1",
          page: 1,
          text: "R&D Marketing; line item 2 unit cost 37,105.50",
          bbox: [],
        },
        {
          id: "qa-bid-page3",
          page: 3,
          text: "Benson Guam Enterprises Inc.; line item 2 unit cost 25,600.00",
          bbox: [],
        },
      ],
    };
    let extracted = false;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
      if (String(url).includes("/health"))
        return new Response(JSON.stringify(health));
      if (String(url).endsWith("/extract")) {
        extracted = true;
        return new Response(JSON.stringify({ proposals: pending, trace: {} }));
      }
      if (String(url).endsWith("/approve")) {
        const selected = pending.find((item) => String(url).includes(item.id));
        if (selected) selected.status = "approved";
        return new Response("{}");
      }
      return new Response(
        JSON.stringify({
          ...project,
          documents: [bidDoc],
          proposals: extracted ? pending : [],
        }),
      );
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: /GPA-070-25 Bid Abstract.pdf.*Rev/ }),
    );
    await user.selectOptions(
      screen.getByLabelText("Extraction purpose"),
      "supplier",
    );
    expect(
      screen.getByRole("option", { name: "Supplier bids / configurations" }),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Extract with Apertus" }),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Apertus extraction result",
    });
    expect(
      within(dialog).getByText(
        "2 supplier proposals ready for individual review.",
      ),
    ).toBeVisible();
    await user.click(
      within(dialog).getByRole("button", { name: "Review proposals" }),
    );
    expect(
      screen.getByRole("heading", { name: "R&D Marketing" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Benson Guam Enterprises Inc." }),
    ).toBeVisible();
    const approvals = screen.getAllByRole("button", {
      name: "Approve supplier proposal",
    });
    expect(approvals).toHaveLength(2);
    await user.click(approvals[0]);
    await waitFor(() =>
      expect(
        screen.getAllByRole("button", { name: "Approve supplier proposal" }),
      ).toHaveLength(1),
    );
    expect(
      screen.getByRole("heading", { name: "Benson Guam Enterprises Inc." }),
    ).toBeVisible();
  });
  it("saves a sourced manual price correction while retaining original data and separate approval", async () => {
    const qa = priceCorrectionQA();
    let updated: unknown = qa.proposal;
    const request = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (url, init) => {
        if (String(url).includes("/health"))
          return new Response(JSON.stringify(health));
        if (String(url).endsWith("/correct-price")) {
          updated = {
            ...qa.proposal,
            original_data: qa.proposal.data,
            data: { ...qa.proposal.data, price_cents: 2560000 },
            price_corrections: [
              {
                id: "qa-correction",
                at: "2026-10-15T10:00:00Z",
                actor: "engineer",
                document_id: qa.document.id,
                source_id: "ea238725bcf796aa9df08ba0:35",
                page: 3,
                reason:
                  "Original PDF page 3 basic unit-cost cell reads 25,600.00.",
                before: { price_cents: 2500000, currency: "USD" },
                after: { price_cents: 2560000, currency: "USD" },
              },
            ],
          };
          return new Response(JSON.stringify(updated));
        }
        return new Response(
          JSON.stringify({
            ...project,
            documents: [...project.documents, qa.document],
            proposals: [updated],
          }),
        );
      });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    await user.click(screen.getByRole("button", { name: "Correct price" }));
    const form = within(
      screen.getByRole("form", { name: "Correct supplier proposal price" }),
    );
    expect(
      form.getByRole("button", { name: "Save correction" }),
    ).toBeDisabled();
    expect(
      form.queryByRole("option", { name: /OP34276/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Approve supplier proposal" }),
    ).toBeDisabled();
    await user.clear(form.getByLabelText("Unit price (decimal)"));
    await user.type(form.getByLabelText("Unit price (decimal)"), "25600.00");
    await user.selectOptions(
      form.getByLabelText("Correction source passage"),
      "ea238725bcf796aa9df08ba0:35",
    );
    await user.type(
      form.getByLabelText("Correction reason"),
      "Original PDF page 3 basic unit-cost cell reads 25,600.00.",
    );
    await user.click(
      form.getByRole("button", { name: "Inspect correction source" }),
    );
    expect(
      within(screen.getByLabelText("Source inspector")).getByText("25,000.00"),
    ).toBeVisible();
    await user.click(form.getByRole("button", { name: "Save correction" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default/proposals/qa-benson-pending/correct-price",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            snapshot_hash: snapshot,
            price_cents: 2560000,
            currency: "USD",
            source_id: "ea238725bcf796aa9df08ba0:35",
            reason: "Original PDF page 3 basic unit-cost cell reads 25,600.00.",
          }),
        }),
      ),
    );
    const history = within(
      await screen.findByRole("region", {
        name: "Manual price correction history",
      }),
    );
    expect(
      history.getByText(/25.?000(?:\.00)?.*→.*25.?600(?:\.00)?/),
    ).toBeVisible();
    expect(
      history.getByText(
        "Original PDF page 3 basic unit-cost cell reads 25,600.00.",
      ),
    ).toBeVisible();
    expect(history.getByText(/engineer/)).toBeVisible();
    expect(history.getByText(/Page 3/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Approve supplier proposal" }),
    ).toBeEnabled();
    expect(
      request.mock.calls.some(([url]) => String(url).endsWith("/approve")),
    ).toBe(false);
  });
  it("validates decimal cents and preserves a blank corrected price as unknown", async () => {
    const qa = priceCorrectionQA();
    const request = server({
      proposals: [qa.proposal],
      documents: [qa.document],
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    await user.click(screen.getByRole("button", { name: "Correct price" }));
    const form = within(
      screen.getByRole("form", { name: "Correct supplier proposal price" }),
    );
    await user.selectOptions(
      form.getByLabelText("Correction source passage"),
      "ea238725bcf796aa9df08ba0:35",
    );
    await user.type(
      form.getByLabelText("Correction reason"),
      "Amount requires original-page review; preserve unknown.",
    );
    const amount = form.getByLabelText("Unit price (decimal)");
    for (const invalid of [
      "25,600.00",
      "25600.001",
      "-1",
      "1e3",
      "90071992547409.92",
    ]) {
      await user.clear(amount);
      await user.type(amount, invalid);
      expect(
        form.getByRole("button", { name: "Save correction" }),
      ).toBeDisabled();
    }
    await user.clear(amount);
    await user.selectOptions(form.getByLabelText("Price currency"), "");
    await user.click(form.getByRole("button", { name: "Save correction" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default/proposals/qa-benson-pending/correct-price",
        expect.objectContaining({
          body: JSON.stringify({
            snapshot_hash: snapshot,
            price_cents: null,
            currency: null,
            source_id: "ea238725bcf796aa9df08ba0:35",
            reason: "Amount requires original-page review; preserve unknown.",
          }),
        }),
      ),
    );
  });
  it("converts decimal input to exact integer cents without a floating-point multiplication", async () => {
    // Numeric validation boundary only, not a claimed price in the source PDF.
    const qa = priceCorrectionQA();
    const request = server({
      proposals: [qa.proposal],
      documents: [qa.document],
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    await user.click(screen.getByRole("button", { name: "Correct price" }));
    const form = within(
      screen.getByRole("form", { name: "Correct supplier proposal price" }),
    );
    await user.clear(form.getByLabelText("Unit price (decimal)"));
    await user.type(form.getByLabelText("Unit price (decimal)"), "0.29");
    await user.selectOptions(
      form.getByLabelText("Correction source passage"),
      "ea238725bcf796aa9df08ba0:35",
    );
    await user.type(
      form.getByLabelText("Correction reason"),
      "QA decimal-cent arithmetic boundary.",
    );
    await user.click(form.getByRole("button", { name: "Save correction" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/api/projects/default/proposals/qa-benson-pending/correct-price",
        expect.objectContaining({
          body: JSON.stringify({
            snapshot_hash: snapshot,
            price_cents: 29,
            currency: "USD",
            source_id: "ea238725bcf796aa9df08ba0:35",
            reason: "QA decimal-cent arithmetic boundary.",
          }),
        }),
      ),
    );
  });
  it("retains a correction draft and pending review when the server rejects its snapshot", async () => {
    const qa = priceCorrectionQA();
    const request = server({
      proposals: [qa.proposal],
      documents: [qa.document],
    });
    const original = request.getMockImplementation()!;
    request.mockImplementation(async (url, init) =>
      String(url).endsWith("/correct-price")
        ? new Response(JSON.stringify({ detail: "Snapshot is stale" }), {
            status: 409,
          })
        : original(url, init),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    await user.click(screen.getByRole("button", { name: "Correct price" }));
    const form = within(
      screen.getByRole("form", { name: "Correct supplier proposal price" }),
    );
    await user.selectOptions(
      form.getByLabelText("Correction source passage"),
      "ea238725bcf796aa9df08ba0:35",
    );
    await user.type(
      form.getByLabelText("Correction reason"),
      "Check original price before approval.",
    );
    await user.click(form.getByRole("button", { name: "Save correction" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Snapshot is stale",
    );
    expect(form.getByLabelText("Correction reason")).toHaveValue(
      "Check original price before approval.",
    );
    expect(
      screen.getByRole("button", { name: "Approve supplier proposal" }),
    ).toBeDisabled();
    expect(
      request.mock.calls.some(([url]) => String(url).endsWith("/approve")),
    ).toBe(false);
  });
  it("keeps manual price provenance visible on an approved supplier", async () => {
    const qa = priceCorrectionQA();
    server({
      documents: [qa.document],
      suppliers: [
        {
          ...project.suppliers[0],
          name: qa.proposal.data.name,
          price_cents: 2560000,
          original_data: qa.proposal.data,
          price_corrections: [
            {
              id: "qa-correction",
              at: "2026-10-15T10:00:00Z",
              actor: "engineer",
              document_id: qa.document.id,
              source_id: "ea238725bcf796aa9df08ba0:35",
              page: 3,
              reason:
                "Original PDF page 3 basic unit-cost cell reads 25,600.00.",
              before: { price_cents: 2500000, currency: "USD" },
              after: { price_cents: 2560000, currency: "USD" },
            },
          ],
        },
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    expect(
      screen.getByRole("region", { name: "Manual price correction history" }),
    ).toHaveTextContent("Original model price");
    expect(
      screen.getByRole("button", { name: "Inspect manual correction source" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Correct price" }),
    ).not.toBeInTheDocument();
  });
  it("shows known currency when a corrected amount remains unknown", async () => {
    const qa = priceCorrectionQA();
    server({
      proposals: [
        {
          ...qa.proposal,
          data: { ...qa.proposal.data, price_cents: null },
          original_data: qa.proposal.data,
          price_corrections: [
            {
              id: "qa-unknown-price",
              at: "2026-10-15T10:00:00Z",
              actor: "engineer",
              document_id: qa.document.id,
              source_id: "ea238725bcf796aa9df08ba0:35",
              page: 3,
              reason:
                "Handwritten amount remains unreadable; preserve unknown.",
              before: { price_cents: 2500000, currency: "USD" },
              after: { price_cents: null, currency: "USD" },
            },
          ],
        },
      ],
      documents: [qa.document],
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    const history = within(
      screen.getByRole("region", { name: "Manual price correction history" }),
    );
    expect(history.getByText(/→.*USD.*Amount unknown/)).toBeVisible();
  });
  it.each(["USD", null])(
    "preserves unknown commercial and identity fields with currency %s",
    async (currency) => {
      server({
        suppliers: [
          {
            ...project.suppliers[0],
            price_cents: null,
            currency,
            revision: null,
            delivery_weeks: null,
          },
        ],
        comparisons: [
          {
            ...project.comparisons[0],
            total_cents: null,
            delivery_weeks: null,
            delay_weeks: null,
          },
        ],
      });
      const user = userEvent.setup();
      render(<App />);
      await screen.findByText("Rated capacity");
      await user.click(
        screen.getByRole("button", { name: "Supplier comparison 02" }),
      );
      expect(
        within(
          screen.getByRole("row", { name: /Documented price/ }),
        ).getByText("Not provided"),
      ).toBeVisible();
      expect(
        within(
          screen.getByRole("row", { name: /Documented subtotal/ }),
        ).getByText("Not provided"),
      ).toBeVisible();
      expect(screen.getByText(/Revision unknown/)).toBeVisible();
      expect(screen.getByText("Delivery not established")).toBeVisible();
    },
  );
  it("keeps missing supplier configuration explicit in comparison and gate selection", async () => {
    server({
      suppliers: [{ ...project.suppliers[0], configuration: null }],
      requirements: project.requirements.map((r) => ({
        ...r,
        status: "approved",
      })),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    expect(screen.getByText(/Configuration unknown/)).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Acceptance & release 03" }),
    );
    await user.click(screen.getByRole("button", { name: "New gate review" }));
    expect(
      screen.getByRole("option", { name: /Eaglerise.*Configuration unknown/ }),
    ).toBeInTheDocument();
  });
  it("shows explicit zero ancillary costs as currency amounts", async () => {
    server();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    await user.click(
      screen.getByRole("button", { name: "Supplier comparison 02" }),
    );
    expect(
      screen.getByRole("row", { name: /Recorded expedite \/ rework/ }),
    ).toHaveTextContent(/USD\s*0\s*\/\s*USD\s*0/);
    expect(screen.getByText(/Undocumented costs remain unknown/)).toBeVisible();
    expect(
      screen.getByRole("columnheader", { name: "Documented subtotal" }),
    ).toBeVisible();
  });
  it.each([
    { expedite: null, rework: 0, expected: /Unknown\s*\/\s*USD\s*0/ },
    { expedite: 0, rework: null, expected: /USD\s*0\s*\/\s*Unknown/ },
    { expedite: null, rework: null, expected: /Unknown\s*\/\s*Unknown/ },
  ])(
    "shows unknown ancillary costs separately from explicit amounts: $expedite / $rework",
    async ({ expedite, rework, expected }) => {
      server({
        suppliers: [
          {
            ...project.suppliers[0],
            expedite_cents: expedite,
            rework_cents: rework,
          },
        ],
      });
      const user = userEvent.setup();
      render(<App />);
      await screen.findByText("Rated capacity");
      await user.click(
        screen.getByRole("button", { name: "Supplier comparison 02" }),
      );
      expect(
        screen.getByRole("row", { name: /Recorded expedite \/ rework/ }),
      ).toHaveTextContent(expected);
    },
  );
  it("awaits source requirements and keeps release controls locked when none exist", async () => {
    server({
      requirements: [],
      assessments: [],
      decisions: [
        {
          id: "qa-empty-gate",
          supplier_id: "qa-eaglerise",
          gate: "purchase",
          snapshot_hash: snapshot,
          status: "approved",
          approvals: [],
          created_at: "2025-10-13T00:00:00Z",
          artifact: null,
        },
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("Awaiting requirements")).toBeVisible();
    expect(
      screen.queryByText("Encoded review complete"),
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Acceptance & release 03" }),
    );
    expect(
      screen.getByRole("button", { name: "New gate review" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Release record" }),
    ).toBeDisabled();
  });
  it("uses the project name in the sidebar while retaining full equipment scope", async () => {
    const scope =
      "750 kVA three-phase pad-mounted transformer; primary 13.8 kV, secondary 120/208 V; Eaglerise ZGSLB-750/13.8-0.208; OP34276 item 2";
    server({ equipment: scope });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Rated capacity");
    const sidebar = screen.getByLabelText("Active project");
    expect(within(sidebar).getByText(project.name)).toBeVisible();
    expect(within(sidebar).queryByText(scope)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Project details" }));
    expect(screen.getByLabelText("Equipment scope")).toHaveValue(scope);
    expect(screen.getByLabelText("Equipment scope")).toHaveAttribute(
      "title",
      scope,
    );
  });
});

describe("extraction assurance and commercial display", () => {
  afterEach(() => vi.restoreAllMocks());
  it("keeps incomplete-run context visible across review workspaces and disables gates", async () => {
    server({ extraction_runs: [{id:"qa-run", document_id:"qa-order", kind:"requirements", status:"incomplete", conditions:["Audit failed: adversarial challenger."], trace:{}}],
      requirements:project.requirements.map(r=>({...r,status:"approved"})),
      comparisons:project.comparisons.map(c=>({...c,status:"feasible"})) });
    const user=userEvent.setup();render(<App />);
    expect(await screen.findByText("Extraction assurance requires review")).toBeVisible();
    await user.click(screen.getByText("OP34276.pdf · requirements"));
    expect(screen.getByText(/Audit failed: adversarial challenger/)).toBeVisible();
    await user.click(screen.getByRole("button",{name:"Supplier comparison 02"}));
    expect(screen.getByText("Extraction assurance requires review")).toBeVisible();
    await user.click(screen.getByRole("button",{name:"Acceptance & release 03"}));
    expect(screen.getByText("Extraction assurance requires review")).toBeVisible();
    expect(screen.getByRole("button",{name:"New gate review"})).toBeDisabled();
  });
  it("labels a lot total honestly and formats the proposed amount as currency", async () => {
    server({suppliers:project.suppliers.map(s=>({...s,price_basis:"lot_total"})),proposals:[{id:"qa-price",kind:"supplier",document_id:"qa-order",status:"pending",source_ids:["qa-po-page4"],data:{name:"Recorded supplier",price_cents:11131650,currency:"USD",price_basis:"lot_total"}}]});
    const user=userEvent.setup();render(<App />);await screen.findByText("Rated capacity");
    await user.click(screen.getByRole("button",{name:"Supplier comparison 02"}));
    expect(screen.getByRole("columnheader",{name:"Documented price"})).toBeVisible();
    expect(screen.getByText(/USD.*111.*316.50/)).toBeVisible();
    expect(screen.getAllByText(/Lot total/).length).toBeGreaterThan(0);
    expect(screen.queryByText("11131650")).not.toBeInTheDocument();
  });
});
