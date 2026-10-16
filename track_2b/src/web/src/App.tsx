import { useEffect, useRef, useState } from "react";
import PdfPagePreview from "./PdfPagePreview";
import {
  EvidenceWorkspace,
  Overview,
  ReleaseStatus,
  ReviewQueue,
  SnapshotComparison,
} from "./WorkbenchPanels";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  Clock3,
  FileText,
  GitBranch,
  History,
  Layers3,
  LayoutDashboard,
  FileSearch,
  LoaderCircle,
  LockKeyhole,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import type {
  Conditions,
  Decision,
  Health,
  PriceCorrection,
  PackageAnalysis,
  Project,
  Requirement,
  SourceDocument,
} from "./types";

type Workspace =
  | "overview"
  | "evidence"
  | "requirements"
  | "comparison"
  | "acceptance"
  | "history";
const workspaces = [
  {
    id: "overview" as const,
    label: "Overview",
    icon: LayoutDashboard,
    number: "01",
  },
  {
    id: "evidence" as const,
    label: "Evidence",
    icon: FileSearch,
    number: "02",
  },
  {
    id: "requirements" as const,
    label: "Requirements",
    icon: ClipboardCheck,
    number: "03",
  },
  {
    id: "comparison" as const,
    label: "Supplier comparison",
    icon: SlidersHorizontal,
    number: "04",
  },
  {
    id: "acceptance" as const,
    label: "Acceptance & release",
    icon: ShieldCheck,
    number: "05",
  },
  {
    id: "history" as const,
    label: "Change history",
    icon: History,
    number: "06",
  },
];
const workspaceCopy: Record<Workspace, { title: string; description: string }> =
  {
    overview: {
      title: "Package overview",
      description:
        "See the review state, resolve blockers, and prepare the evidence handoff.",
    },
    evidence: {
      title: "Evidence workspace",
      description:
        "Search source passages and trace the records that depend on each document.",
    },
    requirements: {
      title: "Requirements review",
      description:
        "Check each interpretation against its source before approval.",
    },
    comparison: {
      title: "Supplier comparison",
      description:
        "Review technical fit, price bases, and delivery conditions against approved requirements.",
    },
    acceptance: {
      title: "Acceptance & release",
      description:
        "Check evidence applicability and collect the approvals required for each release gate.",
    },
    history: {
      title: "Change history",
      description: "Compare package revisions and trace each recorded action.",
    },
  };
function readable(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function conditions(value: Conditions): string {
  if (!value) return "No conditions specified";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.join(" · ");
  return (
    Object.entries(value)
      .map(([key, item]) => `${key.replaceAll("_", " ")}: ${readable(item)}`)
      .join(" · ") || "No conditions specified"
  );
}
function operator(value: string) {
  return (
    (
      { ge: "≥", le: "≤", eq: "=", gt: ">", lt: "<", ne: "≠" } as Record<
        string,
        string
      >
    )[value] || value
  );
}
function decimalCents(value: string): number | null | undefined {
  const text = value.trim();
  if (!text) return null;
  if (!/^\d+(?:\.\d{1,2})?$/.test(text)) return undefined;
  const [whole, fraction = ""] = text.split(".");
  const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
  return cents <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(cents) : undefined;
}
function priceDecimal(value: unknown): string {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0)
    return "";
  const cents = BigInt(value);
  return `${cents / 100n}.${String(cents % 100n).padStart(2, "0")}`;
}
function correctionPrice(price: {
  price_cents: unknown;
  currency: unknown;
}): string {
  const currency =
    typeof price.currency === "string" && price.currency
      ? price.currency
      : "Currency unknown";
  return `${currency} · ${priceDecimal(price.price_cents) || "Amount unknown"}`;
}
function money(
  cents: number | null | undefined,
  currency: string | null | undefined,
) {
  if (cents == null || !Number.isFinite(cents) || !currency)
    return "Not provided";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    currencyDisplay: "code",
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}
function date(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
}
function Badge({ status }: { status: string }) {
  return (
    <span className={`badge ${status.toLowerCase().replaceAll(" ", "-")}`}>
      <span />
      {status.replaceAll("_", " ")}
    </span>
  );
}
function Empty({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-state">
      <Layers3 size={25} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function supplierProposalCount(result: unknown): number | null {
  if (!result || typeof result !== "object") return null;
  if ("proposals" in result && Array.isArray(result.proposals))
    return result.proposals.length;
  if ("id" in result && typeof result.id === "string") return 1;
  return null;
}

const DELIVERY_BASIS_LABELS: Record<string, string> = {
  project_start: "from project start",
  after_order: "after order",
  after_drawing_approval: "after drawing approval",
  other: "from another stated event",
};
function deliveryBasisLabel(basis?: string | null): string {
  return DELIVERY_BASIS_LABELS[basis ?? ""] ?? "(counting event not stated)";
}

function priceBasisLabel(basis: unknown) {
  return basis === "unit"
    ? "Per unit"
    : basis === "lot_total"
      ? "Lot total (combined)"
      : "Price basis not stated";
}

export default function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<PackageAnalysis | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [showIssues, setShowIssues] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [workspace, setWorkspace] = useState<Workspace>("overview");
  useEffect(() => {
    if (window.scrollY > 0) window.scrollTo({ top: 0, behavior: "auto" });
  }, [workspace]);
  const [token, setToken] = useState(
    () => sessionStorage.getItem("tenderproof-token") || "",
  );
  const [tokenDraft, setTokenDraft] = useState(token);
  const [credentials, setCredentials] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [busyElapsed, setBusyElapsed] = useState(0);
  useEffect(() => {
    setBusyElapsed(0);
    if (!busy) return;
    const started = Date.now();
    const timer = window.setInterval(
      () => setBusyElapsed(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [busy]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [review, setReview] = useState<string | null>(null);
  const [answer, setAnswer] = useState<boolean | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [sourceTitle, setSourceTitle] = useState("Source library");
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [pagePreview, setPagePreview] = useState<{
    doc: SourceDocument;
    page: number;
  } | null>(null);
  useEffect(
    () => setPagePreview(null),
    [selectedDoc, sourceIds, inspectorOpen, token],
  );
  const [proposal, setProposal] = useState<unknown>(null);
  const [extractionKind, setExtractionKind] = useState("requirements");
  const [extractionSupplier, setExtractionSupplier] = useState("");
  const [scheduleWeek, setScheduleWeek] = useState("");
  const [scheduleSource, setScheduleSource] = useState("");
  const [proposalReviews, setProposalReviews] = useState<
    Record<string, { family?: boolean; supersedes?: string }>
  >({});
  const [priceCorrection, setPriceCorrection] = useState<{
    proposalId: string;
    price: string;
    currency: string;
    sourceId: string;
    reason: string;
  } | null>(null);
  const [originalPreview, setOriginalPreview] = useState<{
    url: string;
    name: string;
    documentId: string;
  } | null>(null);
  useEffect(
    () => () => {
      if (originalPreview) URL.revokeObjectURL(originalPreview.url);
    },
    [originalPreview],
  );
  const [decisionSupplier, setDecisionSupplier] = useState("");
  const [gate, setGate] = useState<"purchase" | "shipment">("purchase");
  const [showDecision, setShowDecision] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const modalOpener = useRef<HTMLElement | null>(null);
  const headers = (json = false): Record<string, string> => ({
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  });
  const [showMetadata, setShowMetadata] = useState(false);
  const [metadataDraft, setMetadataDraft] = useState({
    name: "",
    customer: "",
    equipment: "",
  });
  const scopeReady =
    !!project?.name?.trim() &&
    !!project?.customer?.trim() &&
    !!project?.equipment?.trim();
  function editMetadata() {
    setMetadataDraft({
      name: project?.name || "",
      customer: project?.customer || "",
      equipment: project?.equipment || "",
    });
    setShowMetadata(true);
  }
  async function request(path: string, init: RequestInit = {}) {
    let response: Response;
    try {
      response = await fetch(path, {
        ...init,
        headers: { ...headers(), ...init.headers },
      });
    } catch {
      throw new Error(
        "Cannot reach the TenderProof API. Check that the server is running, then retry.",
      );
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail =
        typeof body.detail === "string"
          ? body.detail
          : readable(body.detail || `Request failed (${response.status})`);
      throw new Error(
        response.status === 409
          ? `${detail} Refresh the snapshot and review the current state before trying again.`
          : detail,
      );
    }
    return body;
  }
  async function refresh(initial = false) {
    if (initial) setLoading(true);
    setError("");
    try {
      const [h, p] = await Promise.allSettled([
        request("/api/health"),
        request("/api/projects/default"),
      ]);
      if (h.status === "fulfilled") setHealth(h.value);
      if (p.status === "fulfilled") setProject(p.value);
      if (p.status === "rejected") throw p.reason;
      if (h.status === "rejected") throw h.reason;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh(true);
  }, [token]); // Authentication changes reload the server-owned state.
  useEffect(() => {
    let active = true;
    setAnalysis(null);
    setAnalysisError("");
    if (!project) return;
    void request("/api/projects/default/analysis")
      .then((value: PackageAnalysis) => {
        if (
          !value.summary ||
          !Array.isArray(value.issues) ||
          !Array.isArray(value.documents) ||
          !value.lineage
        )
          throw new Error(
            "Package analysis is unavailable. Refresh to retry the review summary.",
          );
        if (value.snapshot_hash !== project.snapshot_hash)
          throw new Error(
            "The package changed. Refresh to load its current analysis.",
          );
        if (active) setAnalysis(value);
      })
      .catch((problem) => {
        if (active) setAnalysisError((problem as Error).message);
      });
    return () => {
      active = false;
    };
  }, [project?.snapshot_hash, token]);
  useEffect(() => {
    if (!showMetadata && !credentials && !showDecision && proposal === null)
      return;
    modalOpener.current = document.activeElement as HTMLElement;
    const firstField =
      dialogRef.current?.querySelector<HTMLElement>("input,select");
    (
      firstField || dialogRef.current?.querySelector<HTMLElement>("button")
    )?.focus();
    return () => modalOpener.current?.focus();
  }, [showMetadata, credentials, showDecision, proposal]);
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setShowMetadata(false);
        setCredentials(false);
        setShowDecision(false);
        setProposal(null);
      }
      if (event.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>(
            "button:not(:disabled),input,select,a",
          ),
        );
        const first = focusable[0],
          last = focusable.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  async function mutate(
    path: string,
    payload: Record<string, unknown>,
    label: string,
    method: "POST" | "PATCH" = "POST",
  ) {
    if (!project || busy) return;
    setBusy(label);
    setError("");
    setNotice("");
    try {
      const result = await request(`/api/projects/default${path}`, {
        method,
        headers: headers(true),
        body: JSON.stringify({
          snapshot_hash: project.snapshot_hash,
          ...payload,
        }),
      });
      await refresh();
      setNotice(label);
      return result;
    } catch (e) {
      setError((e as Error).message);
      await refreshAfterConflict();
    } finally {
      setBusy("");
    }
  }
  async function refreshAfterConflict() {
    try {
      setProject(await request("/api/projects/default"));
    } catch {
      /* Preserve the original actionable error. */
    }
  }
  async function reviewRequirement(req: Requirement, accepted: boolean) {
    const payload: Record<string, unknown> = { accepted };
    if (accepted && req.witness_question) {
      if (answer === null) return;
      payload.witness_answer = answer;
    }
    const result = await mutate(
      `/requirements/${encodeURIComponent(req.id)}/review`,
      payload,
      accepted ? "Requirement approved" : "Requirement rejected",
    );
    if (result !== undefined) {
      setReview(null);
      setAnswer(null);
    }
  }
  function inspect(ids: string[], title: string) {
    setSourceIds(ids || []);
    setSelectedDoc(null);
    setSourceTitle(title);
    setInspectorOpen(true);
    requestAnimationFrame(() => {
      const inspector = document.getElementById("source-inspector");
      if (inspector) inspector.scrollTop = 0;
      if (window.innerWidth <= 980)
        inspector?.scrollIntoView?.({
          behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")
            .matches
            ? "auto"
            : "smooth",
          block: "start",
        });
    });
  }
  async function upload(file?: File) {
    if (!file || !project || busy) return;
    setBusy("Uploading document");
    setError("");
    setNotice("");
    const form = new FormData();
    form.append("file", file);
    form.append("snapshot_hash", project.snapshot_hash);
    try {
      const doc = await request("/api/projects/default/documents", {
        method: "POST",
        body: form,
      });
      await refresh();
      setSelectedDoc(doc.id);
      setSourceTitle(file.name);
      setSourceIds([]);
      setInspectorOpen(true);
      setNotice(
        "Document uploaded. Extract proposals for human review when the model is configured.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
      if (uploadRef.current) uploadRef.current.value = "";
    }
  }
  async function release(decision: Decision) {
    const storageKey = `tenderproof-release-${decision.id}-${project?.snapshot_hash}`;
    let key = sessionStorage.getItem(storageKey);
    if (!key) {
      key = crypto.randomUUID();
      sessionStorage.setItem(storageKey, key);
    }
    const artifact = await mutate(
      `/decisions/${encodeURIComponent(decision.id)}/release`,
      { idempotency_key: key },
      "Release record downloaded",
    );
    if (artifact !== undefined)
      download(artifact, `tenderproof-${decision.gate}-${decision.id}.json`);
  }
  async function getArtifact(decision: Decision) {
    setBusy("Loading release record");
    setError("");
    try {
      const artifact = await request(
        `/api/projects/default/decisions/${encodeURIComponent(decision.id)}/artifact`,
      );
      download(artifact, `tenderproof-${decision.gate}-${decision.id}.json`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const p = project;
  const approved =
    p?.requirements.filter((r) => r.status === "approved").length || 0;
  const pending =
    p?.requirements.filter((r) => r.status === "pending").length || 0;
  const incompleteRuns = (p?.extraction_runs || []).filter(
    (run) => run.status !== "recorded" || run.conditions.length > 0,
  );
  const requirementsReady =
    !!p?.requirements.length &&
    approved === p.requirements.length &&
    incompleteRuns.length === 0;
  const current = workspaceCopy[workspace];
  const displayedRequirements =
    p?.requirements.filter(
      (r) =>
        (filter === "all" || r.status === filter) &&
        `${r.title} ${r.property} ${r.value} ${r.unit}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    ) || [];
  const selectedDocument = p?.documents.find((d) => d.id === selectedDoc);
  const sourceMatches =
    p?.documents.flatMap((doc) =>
      doc.spans
        .filter(
          (span) => sourceIds.includes(span.id) || sourceIds.includes(doc.id),
        )
        .map((span) => ({ doc, span })),
    ) || [];
  function sourceButton(ids: string[], title: string, label?: string) {
    return (
      <button
        className="source-link"
        aria-label={label || `Inspect sources for ${title}`}
        onClick={() => inspect(ids, title)}
      >
        <FileText size={13} />
        {ids.length} source{ids.length === 1 ? "" : "s"}
        <ArrowUpRight size={12} />
      </button>
    );
  }
  function pagePreviewButton(doc: SourceDocument, page: number) {
    if (!/\.pdf$/i.test(doc.name)) return null;
    return (
      <button
        className="source-link"
        aria-label={`Preview original page ${page} of ${doc.name}`}
        onClick={() => setPagePreview({ doc, page })}
      >
        <Search size={13} />
        View original page
      </button>
    );
  }
  function proposalList(kind: string) {
    const list = (p?.proposals || []).filter(
      (item) => item.kind === kind && item.status === "pending",
    );
    if (!list.length) return null;
    return (
      <section className="proposals-section">
        <div className="section-heading">
          <div>
            <h2>
              Model proposals <span>{list.length}</span>
            </h2>
            <p>
              Review structured data and source applicability before approval.
            </p>
          </div>
          <Badge status="pending" />
        </div>
        {list.map((item) => {
          const choice = proposalReviews[item.id] || {};
          const isEvidence = kind === "evidence";
          const correction =
            priceCorrection?.proposalId === item.id ? priceCorrection : null;
          const correctionDocument = p?.documents.find(
            (d) => d.id === item.document_id,
          );
          const correctedCents = correction
            ? decimalCents(correction.price)
            : undefined;
          const correctionReady =
            !!correction &&
            correctedCents !== undefined &&
            !!correction.reason.trim() &&
            correction.reason.length <= 2000 &&
            !!correctionDocument?.spans.some(
              (s) => s.id === correction.sourceId,
            );
          const previous = (p?.evidence || []).filter(
            (e) =>
              e.supplier_id === (item.supplier_id || item.data.supplier_id) &&
              e.kind === item.data.kind,
          );
          return (
            <article
              className="proposal-row"
              key={item.id}
              id={`proposal-${item.id}`}
            >
              <div className="title-row">
                <h3>
                  {readable(
                    item.data.name || item.data.title || `${kind} proposal`,
                  )}
                </h3>
                <span className="phase-tag">{kind}</span>
              </div>
              <dl className="proposal-fields">
                {Object.entries(item.data).map(([key, value]) => (
                  <div key={key}>
                    <dt>
                      {key === "price_cents"
                        ? "Documented price"
                        : key.replaceAll("_", " ")}
                    </dt>
                    <dd>
                      {key === "price_cents"
                        ? money(
                            typeof value === "number" ? value : null,
                            typeof item.data.currency === "string"
                              ? item.data.currency
                              : null,
                          )
                        : key === "price_basis"
                          ? priceBasisLabel(value)
                          : readable(value)}
                    </dd>
                  </div>
                ))}
              </dl>
              {priceHistory(item)}
              {correction && (
                <form
                  className="price-correction-form"
                  aria-label="Correct supplier proposal price"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    if (!correctionReady || busy || !scopeReady) return;
                    const result = await mutate(
                      `/proposals/${encodeURIComponent(item.id)}/correct-price`,
                      {
                        price_cents: correctedCents,
                        currency: correction.currency || null,
                        source_id: correction.sourceId,
                        reason: correction.reason.trim(),
                      },
                      "Manual price correction saved — proposal still awaits approval",
                    );
                    if (result !== undefined) setPriceCorrection(null);
                  }}
                >
                  <h4>Correct the documented unit price</h4>
                  <p className="inline-note">
                    An engineer must inspect the original PDF for handwritten
                    amounts. This saves a manual correction and preserves the
                    model output; approval is a separate action.
                  </p>
                  <fieldset disabled={!!busy || !scopeReady}>
                    <div className="price-correction-fields">
                      <label className="form-label">
                        Unit price (decimal)
                        <input
                          aria-label="Unit price (decimal)"
                          inputMode="decimal"
                          maxLength={64}
                          value={correction.price}
                          placeholder="Blank = unknown"
                          onChange={(e) =>
                            setPriceCorrection({
                              ...correction,
                              price: e.target.value,
                            })
                          }
                        />
                      </label>
                      <label className="form-label">
                        Price currency
                        <select
                          aria-label="Price currency"
                          value={correction.currency}
                          onChange={(e) =>
                            setPriceCorrection({
                              ...correction,
                              currency: e.target.value,
                            })
                          }
                        >
                          <option value="">Unknown</option>
                          <option value="USD">USD</option>
                          <option value="CHF">CHF</option>
                          <option value="EUR">EUR</option>
                        </select>
                      </label>
                      <label className="form-label correction-wide">
                        Correction source passage
                        <select
                          aria-label="Correction source passage"
                          value={correction.sourceId}
                          onChange={(e) =>
                            setPriceCorrection({
                              ...correction,
                              sourceId: e.target.value,
                            })
                          }
                        >
                          <option value="">
                            Select a passage from this document
                          </option>
                          {correctionDocument?.spans.map((span) => (
                            <option key={span.id} value={span.id}>
                              {correctionDocument.name} · Page {span.page} ·{" "}
                              {span.id}:{" "}
                              {span.text === doclingImageNotice
                                ? "Extraction notice"
                                : span.text.slice(0, 85)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="form-label correction-wide">
                        Correction reason
                        <textarea
                          aria-label="Correction reason"
                          maxLength={2000}
                          value={correction.reason}
                          onChange={(e) =>
                            setPriceCorrection({
                              ...correction,
                              reason: e.target.value,
                            })
                          }
                          placeholder="Describe the source reading or why the amount remains unknown."
                        />
                      </label>
                    </div>
                    {correctedCents === undefined && (
                      <p className="price-input-error">
                        Use a nonnegative decimal with up to two fractional
                        digits, without separators or exponent notation, within
                        the supported integer-cent range.
                      </p>
                    )}
                    <div className="correction-source-actions">
                      <button
                        className="source-link"
                        type="button"
                        disabled={!correction.sourceId}
                        onClick={() =>
                          inspect(
                            [correction.sourceId],
                            "Price correction source",
                          )
                        }
                      >
                        Inspect correction source
                      </button>
                      <button
                        className="source-link"
                        type="button"
                        disabled={!correctionDocument}
                        onClick={() =>
                          correctionDocument &&
                          void originalDocument(correctionDocument)
                        }
                      >
                        Download original PDF
                      </button>
                    </div>
                    <div className="proposal-actions">
                      <button
                        type="button"
                        className="button small"
                        onClick={() => setPriceCorrection(null)}
                      >
                        Cancel correction
                      </button>
                      <button
                        type="submit"
                        className="button primary small"
                        disabled={!correctionReady}
                      >
                        Save correction
                      </button>
                    </div>
                  </fieldset>
                </form>
              )}
              {isEvidence && (
                <div className="evidence-review-options">
                  {item.data.kind === "type" && (
                    <label className="coverage-checkbox">
                      <input
                        type="checkbox"
                        disabled={!!busy || !scopeReady}
                        checked={!!choice.family}
                        onChange={(e) =>
                          setProposalReviews({
                            ...proposalReviews,
                            [item.id]: { ...choice, family: e.target.checked },
                          })
                        }
                      />
                      <span>
                        I confirm this type test covers the selected family,
                        configuration, and revision.
                        <small>
                          Leave unchecked if family coverage has not been
                          established.
                        </small>
                      </span>
                    </label>
                  )}
                  <label className="form-label">
                    Superseded evidence report
                    <select
                      aria-label="Superseded evidence report"
                      disabled={!!busy || !scopeReady}
                      value={choice.supersedes || ""}
                      onChange={(e) =>
                        setProposalReviews({
                          ...proposalReviews,
                          [item.id]: { ...choice, supersedes: e.target.value },
                        })
                      }
                    >
                      <option value="">
                        Keep all existing evidence active
                      </option>
                      {previous.map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.title} · Rev {e.revision}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p className="inline-note">
                    A replacement must belong to the same supplier and evidence
                    kind. The original source remains in history.
                  </p>
                </div>
              )}
              <div className="proposal-actions">
                {sourceButton(
                  item.source_ids,
                  `${kind} proposal`,
                  `Inspect ${kind} proposal source`,
                )}
                {!isEvidence && (
                  <button
                    className="button small"
                    disabled={!!busy || !scopeReady || !!correction}
                    onClick={() =>
                      setPriceCorrection({
                        proposalId: item.id,
                        price: priceDecimal(item.data.price_cents),
                        currency: ["USD", "CHF", "EUR"].includes(
                          String(item.data.currency),
                        )
                          ? String(item.data.currency)
                          : "",
                        sourceId: "",
                        reason: "",
                      })
                    }
                  >
                    Correct price
                  </button>
                )}
                <button
                  className="button primary small"
                  disabled={!!busy || !scopeReady || !!correction}
                  onClick={() => {
                    const payload: Record<string, unknown> = {};
                    if (isEvidence) {
                      payload.family_coverage_confirmed = !!choice.family;
                      if (choice.supersedes)
                        payload.supersedes_evidence_id = choice.supersedes;
                    }
                    void mutate(
                      `/proposals/${encodeURIComponent(item.id)}/approve`,
                      payload,
                      `${kind} proposal approved`,
                    );
                  }}
                >
                  <Check size={13} />
                  Approve {kind} proposal
                </button>
              </div>
            </article>
          );
        })}
      </section>
    );
  }
  function priceHistory(item: {
    original_data?: Record<string, unknown>;
    price_corrections?: PriceCorrection[];
  }) {
    if (!item.price_corrections?.length) return null;
    return (
      <section
        className="price-correction-history"
        aria-label="Manual price correction history"
      >
        <h4>Manual price correction history</h4>
        {item.original_data && (
          <p>
            Original model price:{" "}
            {correctionPrice({
              price_cents: item.original_data.price_cents,
              currency: item.original_data.currency,
            })}
          </p>
        )}
        <ol>
          {item.price_corrections.map((entry) => (
            <li key={entry.id}>
              <strong>
                {correctionPrice(entry.before)} → {correctionPrice(entry.after)}
              </strong>
              <span>
                {entry.actor} · {entry.at} · Page {entry.page}
              </span>
              <p>{entry.reason}</p>
              {sourceButton(
                [entry.source_id],
                "Manual price correction",
                "Inspect manual correction source",
              )}
            </li>
          ))}
        </ol>
      </section>
    );
  }
  async function originalDocument(doc: SourceDocument, preview = false) {
    if (busy) return;
    setBusy(preview ? "Loading original image" : "Downloading original");
    setError("");
    try {
      const response = await fetch(
        `/api/projects/default/documents/${encodeURIComponent(doc.id)}/content`,
        { headers: headers() },
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Original document request failed (${response.status})`,
        );
      }
      const bytes = await response.blob();
      const extension = doc.name.split(".").pop()?.toLowerCase();
      const imageTypes: Record<string, string> = {
        png: "image/png",
        jpg: "image/jpeg",
        jpeg: "image/jpeg",
        gif: "image/gif",
        webp: "image/webp",
        bmp: "image/bmp",
      };
      const blob = preview
        ? new Blob([bytes], { type: imageTypes[extension || ""] || bytes.type })
        : bytes;
      const url = URL.createObjectURL(blob);
      if (preview)
        setOriginalPreview({ url, name: doc.name, documentId: doc.id });
      else {
        const a = document.createElement("a");
        a.href = url;
        a.download = doc.name;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (e) {
      setError((e as Error).message || "Cannot load the original document.");
    } finally {
      setBusy("");
    }
  }
  function openDocument(id: string) {
    const document = project?.documents.find((item) => item.id === id);
    setSelectedDoc(id);
    setSourceIds([]);
    setSourceTitle(document?.name || "Source document");
    setInspectorOpen(true);
  }
  function navigateRecord(
    type: string,
    id: string,
    documentId: string | null,
    ids: string[],
  ) {
    if (type === "requirements" || type === "requirement") {
      setWorkspace("requirements");
      setReview(id);
      setAnswer(null);
      requestAnimationFrame(() =>
        document
          .getElementById(`requirement-${id}`)
          ?.scrollIntoView?.({ block: "center" }),
      );
    } else if (
      ["suppliers", "supplier", "proposal", "correction"].includes(type)
    ) {
      const proposalKind = project?.proposals?.find(
        (item) => item.id === id,
      )?.kind;
      setWorkspace(proposalKind === "evidence" ? "acceptance" : "comparison");
      requestAnimationFrame(() =>
        document
          .getElementById(`proposal-${id}`)
          ?.scrollIntoView?.({ block: "center" }),
      );
    } else if (type === "evidence") {
      setWorkspace("acceptance");
    } else {
      setWorkspace("evidence");
      if (ids.length) inspect(ids, "Linked source evidence");
      else if (documentId) openDocument(documentId);
    }
  }
  function modalClose() {
    setShowMetadata(false);
    setCredentials(false);
    setShowDecision(false);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setWorkspace("overview");
          }}
          aria-label="TenderProof home"
        >
          <span className="brand-mark">
            <ShieldCheck size={24} />
          </span>
          <span>
            Tender<span className="brand-light">Proof</span>
            <small>Evidence workbench</small>
          </span>
        </a>
        <div className="project-label">Current package</div>
        <div className="side-project" aria-label="Active project">
          <span className="project-icon">
            <GitBranch size={18} />
          </span>
          <div>
            <strong title={p?.name || "Engineering package"}>
              {p?.name || "Engineering package"}
            </strong>
            <span>{p?.customer || "Connecting to project…"}</span>
          </div>
        </div>
        <div className="nav-label">Review workflow</div>
        <nav aria-label="Workspaces">
          {workspaces.map(({ id, label, icon: Icon, number }) => (
            <button
              key={id}
              className={`nav-item ${workspace === id ? "active" : ""}`}
              aria-current={workspace === id ? "page" : undefined}
              onClick={() => setWorkspace(id)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === "requirements" && pending > 0 ? (
                <span className="nav-count">{pending}</span>
              ) : (
                <small>{number}</small>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="side-note">
            <LockKeyhole size={16} />
            <p>
              Every release has a record.
              <br />
              <span>Every record has its evidence.</span>
            </p>
          </div>
          <div className="side-system">
            <span className={`connection-dot ${p ? "connected" : ""}`} />
            <span>
              {health ? `${health.workflow} workflow` : "Awaiting API"}
            </span>
            <span className="version">v1.0</span>
          </div>
        </div>
      </aside>
      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Projects <ChevronRight size={13} />
            <span>{p?.name || "Tender review"}</span>
          </div>
          <div className="top-actions">
            <span className={`environment ${"live"}`}>
              <span />
              {health ? "LIVE WORKSPACE" : "CONNECTING"}
            </span>
            {
              <button
                className="button quiet small"
                onClick={() => {
                  setTokenDraft(token);
                  setCredentials(true);
                }}
              >
                <LockKeyhole size={13} />
                {token ? "Authentication" : "Connect token"}
              </button>
            }
            <span className="avatar" title={"Authenticated user"}>
              {"TP"}
            </span>
          </div>
        </header>
        <div className="workspace-header">
          <div>
            <div className="eyebrow">
              Evidence workbench <span>/</span>{" "}
              {workspaces.find((w) => w.id === workspace)?.number}
            </div>
            <h1>{current.title}</h1>
            <p>{current.description}</p>
            {workspace !== "overview" && p?.equipment && (
              <p className="scope-line">
                <span>Scope</span> {p.equipment}
              </p>
            )}
          </div>
          <div className="header-tool-buttons">
            <button
              className="button quiet"
              disabled={!project || !!busy}
              onClick={editMetadata}
            >
              <GitBranch size={15} />
              Project details
            </button>
            <button
              aria-label="Toggle source inspector"
              aria-expanded={inspectorOpen}
              className="button quiet inspector-toggle"
              onClick={() => setInspectorOpen(!inspectorOpen)}
            >
              {inspectorOpen ? (
                <PanelRightClose size={17} />
              ) : (
                <PanelRightOpen size={17} />
              )}
              <span>Sources</span>
            </button>
          </div>
        </div>
        <div className="snapshot-strip">
          <div>
            <span className="snapshot-symbol">
              <GitBranch size={13} />
            </span>
            <span>Snapshot</span>
            <code title={p?.snapshot_hash}>
              {p ? p.snapshot_hash.slice(0, 10) : "—"}
            </code>
            <span className="strip-divider" />
            <span>Revision {p?.version || "—"}</span>
          </div>
          <button
            className="text-button"
            disabled={loading || !!busy}
            onClick={() => void refresh()}
          >
            <RefreshCw size={12} className={loading ? "spin" : ""} />
            Refresh
          </button>
        </div>

        {p && (
          <ReleaseStatus
            project={p}
            analysis={analysis}
            onReview={() => setShowIssues(true)}
          />
        )}
        {project && !scopeReady && (
          <div className="scope-banner">
            <CircleHelp size={16} />
            <span>
              Set project details before extraction or approval. Identify the
              customer and equipment configuration from the actual source
              documents.
            </span>
            <button className="button small" onClick={editMetadata}>
              Set project details
            </button>
          </div>
        )}
        {error && (
          <div className="feedback error" role="alert">
            <CircleHelp size={17} />
            <span>{error}</span>
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {notice && (
          <div className="feedback success" role="status">
            <Check size={16} />
            <span>{notice}</span>
            <button
              aria-label="Dismiss notification"
              onClick={() => setNotice("")}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {busy && (
          <div className="working-indicator" role="status">
            <LoaderCircle size={15} className="spin" />
            {busy}… {busyElapsed >= 5 && <span>{busyElapsed}s elapsed</span>}
          </div>
        )}
        {loading && !p ? (
          <div className="loading-view">
            <LoaderCircle size={26} className="spin" />
            <h2>Opening engineering workspace</h2>
            <p>Loading requirements, evidence, and the current snapshot.</p>
          </div>
        ) : !p ? (
          <div className="loading-view">
            <CircleHelp size={28} />
            <h2>Workspace unavailable</h2>
            <p>Connect to the API to load the project.</p>
            <div className="button-row">
              <button
                className="button primary"
                onClick={() => void refresh(true)}
              >
                Retry connection
              </button>
              <button className="button" onClick={() => setCredentials(true)}>
                Enter access token
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`desk-layout ${inspectorOpen ? "" : "inspector-hidden"} workspace-${workspace}`}
          >
            <section
              className="workspace-content"
              key={workspace}
              aria-label={current.title}
            >
              {workspace === "overview" && (
                <Overview
                  project={p}
                  analysis={analysis}
                  analysisError={analysisError}
                  read={request}
                  onReview={() => setShowIssues(true)}
                  onNavigate={navigateRecord}
                  onEvidence={() => setWorkspace("evidence")}
                  onRequirements={() => setWorkspace("requirements")}
                  onOffers={() => setWorkspace("comparison")}
                  onRelease={() => setWorkspace("acceptance")}
                />
              )}
              {workspace === "evidence" && (
                <EvidenceWorkspace
                  key={p.snapshot_hash}
                  project={p}
                  analysis={analysis}
                  analysisError={analysisError}
                  read={request}
                  onInspect={inspect}
                  onNavigate={navigateRecord}
                  onDocument={openDocument}
                />
              )}
              {workspace === "requirements" && (
                <>
                  <div className="workspace-summary">
                    <div>
                      <strong>
                        {approved}
                        <span> / {p.requirements.length}</span>
                      </strong>
                      <span>requirements approved</span>
                    </div>
                    <div
                      className="progress-track"
                      title={`${approved} of ${p.requirements.length} approved`}
                    >
                      <span
                        style={{
                          width: `${p.requirements.length ? (approved / p.requirements.length) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <span className="pending-label">
                      {!p.requirements.length
                        ? "Awaiting requirements"
                        : pending
                          ? `${pending} awaiting review`
                          : "Encoded review complete"}
                    </span>
                  </div>
                  <div className="section-heading">
                    <div>
                      <h2>
                        Tender requirements{" "}
                        <span>
                          {p.requirements.length.toString().padStart(2, "0")}
                        </span>
                      </h2>
                      <p>
                        Human approval establishes the interpretation used at
                        each gate.
                      </p>
                    </div>
                    <span className="section-caption">
                      SOURCE → INTERPRETATION → REVIEW
                    </span>
                  </div>
                  <div className="table-toolbar">
                    <label className="search-field">
                      <Search size={15} />
                      <input
                        aria-label="Search requirements"
                        placeholder="Search requirements"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                    <select
                      aria-label="Filter requirement status"
                      className="filter-select"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    >
                      <option value="all">All statuses</option>
                      <option value="pending">Pending review</option>
                      <option value="approved">Approved</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                  <div className="requirements-list">
                    <div className="list-header">
                      <span>REQUIREMENT / APPLICABILITY</span>
                      <span>REVIEW STATUS</span>
                    </div>
                    {displayedRequirements.map((req, index) => (
                      <article
                        className={`requirement-row ${review === req.id ? "reviewing" : ""}`}
                        key={req.id}
                        id={`requirement-${req.id}`}
                      >
                        <div className="requirement-overview">
                          <span className="row-number">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <div className="requirement-main">
                            <div className="title-row">
                              <h3>{req.title}</h3>
                              <span className="phase-tag">{req.phase}</span>
                            </div>
                            <div className="requirement-value">
                              <span className="operator">
                                {operator(req.operator)}
                              </span>{" "}
                              {req.value} <span>{req.unit}</span>
                            </div>
                            <p className="conditions">
                              {conditions(req.conditions)}
                            </p>
                            <div className="requirement-meta">
                              {sourceButton(req.source_ids, req.title)}
                              <code>{req.id}</code>
                            </div>
                          </div>
                          <div className="review-column">
                            <Badge status={req.status} />
                            {req.reviewer && <small>by {req.reviewer}</small>}
                            <button
                              className="review-link"
                              disabled={!!busy}
                              aria-label={`Review requirement ${req.title}`}
                              onClick={() => {
                                setReview(review === req.id ? null : req.id);
                                setAnswer(null);
                              }}
                            >
                              {review === req.id ? "Close review" : "Review"}
                              <ChevronRight size={14} />
                            </button>
                          </div>
                        </div>
                        {review === req.id && (
                          <div className="review-panel">
                            <div className="review-panel-label">
                              <CircleHelp size={16} />
                              <span>CONFIRM THE INTERPRETATION</span>
                            </div>
                            <p>
                              Review this encoded numeric requirement against
                              its source. Unencoded obligations still require
                              engineering review.
                            </p>
                            {req.witness_question ? (
                              <fieldset disabled={!!busy}>
                                <legend>{req.witness_question}</legend>
                                <p>
                                  Answer this check yourself before approving
                                  the extracted requirement.
                                </p>
                                <div className="answer-options">
                                  <label
                                    className={
                                      answer === true ? "selected" : ""
                                    }
                                  >
                                    <input
                                      type="radio"
                                      name={`answer-${req.id}`}
                                      checked={answer === true}
                                      onChange={() => setAnswer(true)}
                                    />
                                    Yes
                                  </label>
                                  <label
                                    className={
                                      answer === false ? "selected" : ""
                                    }
                                  >
                                    <input
                                      type="radio"
                                      name={`answer-${req.id}`}
                                      checked={answer === false}
                                      onChange={() => setAnswer(false)}
                                    />
                                    No
                                  </label>
                                </div>
                              </fieldset>
                            ) : (
                              <p>
                                Confirm that the value, operator, conditions,
                                and cited source match the tender.
                              </p>
                            )}
                            <div className="review-panel-actions">
                              <span>
                                {scopeReady
                                  ? "Approval is recorded against this snapshot."
                                  : "Set project details before approving requirements."}
                              </span>
                              <button
                                className="button danger-text small"
                                disabled={!!busy || !scopeReady}
                                onClick={() =>
                                  void reviewRequirement(req, false)
                                }
                              >
                                Reject
                              </button>
                              <button
                                className="button primary small"
                                disabled={
                                  !!busy ||
                                  !scopeReady ||
                                  (!!req.witness_question && answer === null)
                                }
                                onClick={() =>
                                  void reviewRequirement(req, true)
                                }
                              >
                                <Check size={14} />
                                Approve requirement
                              </button>
                            </div>
                          </div>
                        )}
                      </article>
                    ))}
                    {!displayedRequirements.length && (
                      <Empty
                        title={
                          p.requirements.length
                            ? "No matching requirements"
                            : "No requirements yet"
                        }
                        description={
                          p.requirements.length
                            ? "Try another search or status filter."
                            : "Upload a tender in the source inspector, then extract requirements for human review."
                        }
                      />
                    )}
                  </div>
                  <div className="workspace-footnote">
                    <ShieldCheck size={14} />
                    <span>
                      Unknown or conflicting evidence never passes a release
                      gate.
                    </span>
                  </div>
                </>
              )}
              {workspace === "comparison" && (
                <>
                  {proposalList("supplier")}
                  {!p.suppliers.length && (
                    <Empty
                      title="No supplier configurations yet"
                      description="Upload an actual supplier or order source, extract its configuration, and review the proposal before comparing options."
                    />
                  )}
                  <details className="schedule-panel">
                    <summary>
                      <Clock3 size={16} />
                      <span>Review delivery milestone</span>
                      <small>
                        {p.required_delivery_week != null
                          ? `Required: project week ${p.required_delivery_week}`
                          : "Delivery milestone not reviewed"}
                      </small>
                      <ChevronDown size={13} />
                    </summary>
                    <p>
                      Set the required project week from an existing source
                      passage before commercial feasibility can be established.
                    </p>
                    <div className="schedule-fields">
                      <label className="form-label">
                        Required delivery week
                        <input
                          aria-label="Required delivery week"
                          type="number"
                          min="0"
                          max="520"
                          step="1"
                          value={scheduleWeek}
                          placeholder={
                            p.required_delivery_week != null
                              ? String(p.required_delivery_week)
                              : "0–520"
                          }
                          onChange={(e) => setScheduleWeek(e.target.value)}
                        />
                      </label>
                      <label className="form-label">
                        Milestone source passage
                        <select
                          aria-label="Milestone source passage"
                          value={scheduleSource}
                          onChange={(e) => setScheduleSource(e.target.value)}
                        >
                          <option value="">Select a source passage</option>
                          {p.documents.flatMap((doc) =>
                            doc.spans.map((span) => (
                              <option key={span.id} value={span.id}>
                                {doc.name} · p{span.page}:{" "}
                                {span.text.slice(0, 85)}
                              </option>
                            )),
                          )}
                        </select>
                      </label>
                    </div>
                    <div className="schedule-actions">
                      {p.schedule_source_id ? (
                        sourceButton(
                          [p.schedule_source_id],
                          "Delivery milestone",
                        )
                      ) : (
                        <span className="inline-note">
                          Engineer review required
                        </span>
                      )}
                      <button
                        className="button primary small"
                        disabled={
                          !!busy ||
                          !scopeReady ||
                          scheduleWeek === "" ||
                          !Number.isInteger(Number(scheduleWeek)) ||
                          Number(scheduleWeek) < 0 ||
                          Number(scheduleWeek) > 520 ||
                          !scheduleSource
                        }
                        onClick={() =>
                          void mutate(
                            "/schedule",
                            {
                              required_delivery_week: Number(scheduleWeek),
                              source_id: scheduleSource,
                            },
                            "Sourced delivery milestone approved",
                          )
                        }
                      >
                        <Check size={13} />
                        Approve delivery milestone
                      </button>
                    </div>
                  </details>
                  <div className="section-heading">
                    <div>
                      <h2>Technical & commercial assessment</h2>
                      <p>
                        Documented bid prices and recorded adjustments.
                        Undocumented costs remain unknown.
                      </p>
                    </div>
                    <Badge
                      status={
                        !p.requirements.length
                          ? "awaiting requirements"
                          : pending
                            ? "review pending"
                            : "reviewed"
                      }
                    />
                  </div>
                  <div className="comparison-scroll">
                    <table className="comparison-table">
                      <thead>
                        <tr>
                          <th>
                            <span className="table-eyebrow">TENDER BASIS</span>
                            Assessment
                          </th>
                          {p.suppliers.map((s) => (
                            <th key={s.id}>
                              <span className="table-eyebrow">
                                {s.id.toUpperCase()}
                              </span>
                              <strong>{s.name}</strong>
                              <span className="supplier-config">
                                {s.configuration || "Configuration unknown"} ·{" "}
                                {s.revision
                                  ? `Rev ${s.revision}`
                                  : "Revision unknown"}
                              </span>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="comparison-status">
                          <th>Overall eligibility</th>
                          {p.suppliers.map((s) => (
                            <td key={s.id}>
                              <Badge
                                status={
                                  p.comparisons.find(
                                    (c) => c.supplier_id === s.id,
                                  )?.status || "unknown"
                                }
                              />
                            </td>
                          ))}
                        </tr>
                        {p.requirements.map((req) => (
                          <tr key={req.id}>
                            <th>
                              <span>{req.title}</span>
                              <small>
                                {operator(req.operator)} {req.value} {req.unit}{" "}
                                · {conditions(req.conditions)}
                              </small>
                              {sourceButton(
                                req.source_ids,
                                req.title,
                                `Inspect comparison source for ${req.title}`,
                              )}
                            </th>
                            {p.suppliers.map((s) => {
                              const a = p.assessments.find(
                                (a) =>
                                  a.requirement_id === req.id &&
                                  a.supplier_id === s.id,
                              );
                              return (
                                <td key={s.id}>
                                  <Badge status={a?.status || "unknown"} />
                                  <p>
                                    {a?.reason ||
                                      "No applicable evidence supplied."}
                                  </p>
                                  {!!a?.counterexample && (
                                    <div className="counterexample">
                                      <strong>Counterexample</strong>
                                      <span>{readable(a.counterexample)}</span>
                                    </div>
                                  )}
                                  {a &&
                                    sourceButton(
                                      a.source_ids,
                                      `${s.name} · ${req.title}`,
                                      `Inspect ${s.name} assessment for ${req.title}`,
                                    )}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                        <tr className="commercial-divider">
                          <th colSpan={p.suppliers.length + 1}>
                            COMMERCIAL BASIS
                          </th>
                        </tr>
                        <tr>
                          <th>Documented price</th>
                          {p.suppliers.map((s) => (
                            <td className="tabular" key={s.id}>
                              {money(s.price_cents, s.currency)}{" "}
                              <small>{priceBasisLabel(s.price_basis)}</small>
                              {priceHistory(s)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <th>Recorded expedite / rework</th>
                          {p.suppliers.map((s) => (
                            <td className="tabular" key={s.id}>
                              {s.expedite_cents == null
                                ? "Unknown"
                                : money(s.expedite_cents, s.currency)}{" "}
                              /{" "}
                              {s.rework_cents == null
                                ? "Unknown"
                                : money(s.rework_cents, s.currency)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <th>Delivery / delay</th>
                          {p.suppliers.map((s) => {
                            const c = p.comparisons.find(
                              (c) => c.supplier_id === s.id,
                            );
                            const delivery =
                              c?.delivery_weeks ?? s.delivery_weeks;
                            return (
                              <td key={s.id}>
                                {delivery == null
                                  ? "Delivery not established"
                                  : `${delivery} weeks ${deliveryBasisLabel(c?.delivery_basis ?? s.delivery_basis)}`}{" "}
                                <small>
                                  {c?.delay_weeks == null
                                    ? "Delay not established"
                                    : `${c.delay_weeks} weeks delay`}
                                </small>
                              </td>
                            );
                          })}
                        </tr>
                        <tr className="total-row">
                          <th>Documented subtotal</th>
                          {p.suppliers.map((s) => {
                            const c = p.comparisons.find(
                              (c) => c.supplier_id === s.id,
                            );
                            return (
                              <td key={s.id}>
                                {c
                                  ? money(c.total_cents, s.currency)
                                  : "Not evaluated"}
                              </td>
                            );
                          })}
                        </tr>
                        <tr>
                          <th>Open conditions</th>
                          {p.suppliers.map((s) => {
                            const c = p.comparisons.find(
                              (c) => c.supplier_id === s.id,
                            );
                            return (
                              <td key={s.id}>
                                {c?.issues.length ? (
                                  <ul className="issue-list">
                                    {c.issues.map((issue, index) => (
                                      <li key={index}>{readable(issue)}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <span className="muted">
                                    No commercial conditions reported
                                  </span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="next-step">
                    <div>
                      <ShieldCheck size={18} />
                      <div>
                        <strong>Proceed with an eligible configuration</strong>
                        <p>
                          Purchase and shipment remain separate approval gates.
                        </p>
                      </div>
                    </div>
                    <button
                      className="button primary"
                      onClick={() => setWorkspace("acceptance")}
                    >
                      Open acceptance
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </>
              )}
              {workspace === "acceptance" && (
                <>
                  {proposalList("evidence")}
                  <div className="section-heading">
                    <div>
                      <h2>
                        Evidence applicability{" "}
                        <span>
                          {p.evidence.length.toString().padStart(2, "0")}
                        </span>
                      </h2>
                      <p>
                        Serial, family, configuration, revision, and test
                        conditions must apply.
                      </p>
                    </div>
                  </div>
                  <div className="evidence-list">
                    {p.evidence.map((e) => {
                      const ea = p.evidence_assessments.find(
                        (a) =>
                          a.evidence_id === e.id &&
                          a.supplier_id === e.supplier_id,
                      );
                      const supplier = p.suppliers.find(
                        (s) => s.id === e.supplier_id,
                      );
                      return (
                        <article className="evidence-row" key={e.id}>
                          <FileText size={20} className="evidence-icon" />
                          <div className="evidence-content">
                            <div className="title-row">
                              <h3>{e.title}</h3>
                              <Badge status={ea?.status || "unknown"} />
                            </div>
                            <p>
                              {supplier?.name || e.supplier_id} <span>·</span>{" "}
                              {e.kind} <span>·</span>{" "}
                              {e.revision
                                ? `Rev ${e.revision}`
                                : "Revision unknown"}
                            </p>
                            <dl>
                              <div>
                                <dt>Serial</dt>
                                <dd>{e.serial || "—"}</dd>
                              </div>
                              <div>
                                <dt>Family</dt>
                                <dd>{e.family || "—"}</dd>
                              </div>
                              <div>
                                <dt>Configuration</dt>
                                <dd>{e.configuration || "—"}</dd>
                              </div>
                            </dl>
                            <div
                              className={`evidence-reason ${ea?.status === "supported" ? "" : "needs-attention"}`}
                            >
                              {ea?.reason ||
                                "No applicability assessment available."}
                            </div>
                            <p className="conditions">
                              {conditions(e.conditions)}
                            </p>
                            {!!e.measurements && (
                              <details className="measurement-details">
                                <summary>Measurements</summary>
                                <pre>
                                  {JSON.stringify(e.measurements, null, 2)}
                                </pre>
                              </details>
                            )}
                            {sourceButton(
                              [
                                ...new Set([
                                  ...e.source_ids,
                                  ...(ea?.source_ids || []),
                                ]),
                              ],
                              e.title,
                            )}
                          </div>
                        </article>
                      );
                    })}
                    {!p.evidence.length && (
                      <Empty
                        title="No acceptance evidence"
                        description="Upload sources and review their applicability before a shipment release."
                      />
                    )}
                  </div>

                  <div className="section-heading decision-heading">
                    <div>
                      <h2>
                        Prototype release · ERP simulator{" "}
                        <span>
                          {p.decisions.length.toString().padStart(2, "0")}
                        </span>
                      </h2>
                      <p>
                        Purchase: Engineer + Commercial. Shipment: Inspector +
                        Commercial.
                      </p>
                      <p>
                        Checks cover reviewed encoded numeric requirements;
                        unencoded obligations require engineering review.
                      </p>
                    </div>
                    <button
                      className="button primary small"
                      disabled={
                        !!busy ||
                        !scopeReady ||
                        !requirementsReady ||
                        !p.suppliers.length
                      }
                      title={
                        !requirementsReady
                          ? "Approve source-linked requirements before preparing a gate review."
                          : undefined
                      }
                      onClick={() => {
                        setDecisionSupplier(p.suppliers[0]?.id || "");
                        setShowDecision(true);
                      }}
                    >
                      <Plus size={14} />
                      New gate review
                    </button>
                  </div>
                  <div className="decisions-list">
                    {p.decisions.map((d) => {
                      const supplier = p.suppliers.find(
                        (s) => s.id === d.supplier_id,
                      );
                      const stale =
                        d.status === "stale" ||
                        d.snapshot_hash !== p.snapshot_hash;
                      const required =
                        d.gate === "purchase"
                          ? ["engineer", "commercial"]
                          : ["inspector", "commercial"];
                      return (
                        <article
                          className={`decision-row ${stale ? "stale-record" : ""}`}
                          key={d.id}
                        >
                          <div className="decision-top">
                            <div>
                              <span className="table-eyebrow">
                                {d.gate.toUpperCase()} GATE
                              </span>
                              <h3>{supplier?.name || d.supplier_id}</h3>
                            </div>
                            <Badge status={stale ? "stale" : d.status} />
                          </div>
                          <div className="decision-snapshot">
                            <GitBranch size={12} />
                            <code>{d.snapshot_hash.slice(0, 10)}</code>
                            <span>·</span>
                            <span>{date(d.created_at)}</span>
                          </div>
                          <div className="approval-track">
                            {required.map((r) => {
                              const a = d.approvals.find((a) => a.role === r);
                              return (
                                <div className={a ? "signed" : ""} key={r}>
                                  {a ? (
                                    <CheckCheck size={17} />
                                  ) : (
                                    <Clock3 size={17} />
                                  )}
                                  <span>
                                    <strong>{r}</strong>
                                    <small>
                                      {a
                                        ? `${a.actor} · ${date(a.at)}`
                                        : "Approval required"}
                                    </small>
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                          {stale && (
                            <p className="stale-explanation">
                              Engineering data changed. Create a new gate review
                              for the current snapshot.
                            </p>
                          )}
                          <div className="decision-actions">
                            <code>{d.id}</code>
                            {d.status === "released" || !!d.artifact ? (
                              <button
                                className="button small"
                                disabled={!!busy}
                                onClick={() => void getArtifact(d)}
                              >
                                <ArrowDownToLine size={14} />
                                Download record
                              </button>
                            ) : (
                              <>
                                <button
                                  className="button small"
                                  disabled={
                                    !!busy ||
                                    stale ||
                                    !scopeReady ||
                                    !requirementsReady ||
                                    d.status === "approved"
                                  }
                                  onClick={() =>
                                    void mutate(
                                      `/decisions/${encodeURIComponent(d.id)}/approve`,
                                      {},
                                      "Approval recorded",
                                    )
                                  }
                                >
                                  <Check size={14} />
                                  Approve{""}
                                </button>
                                <button
                                  className="button primary small"
                                  disabled={
                                    !!busy ||
                                    stale ||
                                    !requirementsReady ||
                                    d.status !== "approved"
                                  }
                                  onClick={() => void release(d)}
                                >
                                  <ArrowDownToLine size={14} />
                                  Release record
                                </button>
                              </>
                            )}
                          </div>
                        </article>
                      );
                    })}
                    {!p.decisions.length && (
                      <Empty
                        title="No gate reviews yet"
                        description="Create a prototype review for a supplier. The server checks encoded requirements and applicable evidence before preparing an ERP simulator record."
                      />
                    )}
                  </div>
                </>
              )}
              {workspace === "history" && (
                <>
                  <SnapshotComparison
                    key={p.snapshot_hash}
                    project={p}
                    read={request}
                    onInspect={inspect}
                  />
                  <div className="section-heading">
                    <div>
                      <h2>
                        Project activity{" "}
                        <span>
                          {p.events.length.toString().padStart(2, "0")}
                        </span>
                      </h2>
                      <p>Server-recorded changes, newest first.</p>
                    </div>
                    <span className="section-caption">
                      SNAPSHOT-BOUND AUDIT TRAIL
                    </span>
                  </div>

                  <div className="event-timeline">
                    {p.events.map((event) => (
                      <article key={event.id} className="event">
                        <span className="timeline-dot" />
                        <div className="event-time">
                          {date(event.at)}
                          <span>{event.actor}</span>
                        </div>
                        <div className="event-body">
                          <span className="event-type">
                            {event.type
                              .replaceAll("_", " ")
                              .replaceAll(".", " / ")}
                          </span>
                          <h3>{event.summary}</h3>
                          {!!event.details &&
                            Object.keys(Object(event.details)).length > 0 && (
                              <details>
                                <summary>Event details</summary>
                                <pre>
                                  {JSON.stringify(event.details, null, 2)}
                                </pre>
                              </details>
                            )}
                        </div>
                      </article>
                    ))}
                  </div>
                  {!p.events.length && (
                    <Empty
                      title="No recorded changes"
                      description="Reviews, corrections, and gate actions will appear here."
                    />
                  )}
                </>
              )}
            </section>
            {inspectorOpen && (
              <aside
                id="source-inspector"
                className="source-inspector"
                aria-label="Source inspector"
              >
                <div className="inspector-heading">
                  <span>
                    <FileText size={16} />
                    SOURCE INSPECTOR
                  </span>
                  <button
                    aria-label="Close source inspector"
                    onClick={() => setInspectorOpen(false)}
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="inspector-body">
                  <div className="inspector-title">
                    <h2>{sourceTitle}</h2>
                    <p>
                      {sourceIds.length
                        ? "Cited passages from the source record."
                        : "Inspect the documents behind this review."}
                    </p>
                  </div>
                  {pagePreview && (
                    <PdfPagePreview
                      key={`${pagePreview.doc.id}:${pagePreview.page}`}
                      doc={pagePreview.doc}
                      page={pagePreview.page}
                      token={token}
                      onPageChange={(page) =>
                        setPagePreview({ ...pagePreview, page })
                      }
                      onClose={() => setPagePreview(null)}
                    />
                  )}
                  {sourceIds.length > 0 ? (
                    <>
                      <button
                        className="text-button back-to-library"
                        onClick={() => {
                          setSourceIds([]);
                          setSelectedDoc(null);
                          setSourceTitle("Source library");
                        }}
                      >
                        ← All documents
                      </button>
                      {sourceMatches.map(({ doc, span }) => (
                        <div
                          className="source-passage"
                          key={`${doc.id}-${span.id}`}
                        >
                          <div className="source-document-name">
                            <FileText size={14} />
                            <strong>{doc.name}</strong>
                          </div>
                          <div className="source-page">
                            <span>Page {span.page}</span>
                            <span>Rev {doc.revision}</span>
                          </div>
                          <SourceText text={span.text} />
                          {pagePreviewButton(doc, span.page)}
                          <div className="passage-footer">
                            <code>{span.id}</code>
                            <span>
                              {span.text === doclingImageNotice
                                ? "Parser notice"
                                : "Exact source text"}
                            </span>
                          </div>
                        </div>
                      ))}
                      {!sourceMatches.length && (
                        <div className="source-unavailable">
                          <CircleHelp size={20} />
                          <h3>Passage unavailable</h3>
                          <p>
                            No loaded document matches these references. This
                            evidence remains unverified.
                          </p>
                          <code>{sourceIds.join(", ")}</code>
                        </div>
                      )}
                    </>
                  ) : selectedDocument ? (
                    <>
                      <button
                        className="text-button back-to-library"
                        onClick={() => {
                          setSelectedDoc(null);
                          setSourceTitle("Source library");
                        }}
                      >
                        ← All documents
                      </button>
                      <DocumentMeta doc={selectedDocument} />
                      <div className="original-document-actions">
                        {pagePreviewButton(selectedDocument, 1)}
                        <button
                          className="button small"
                          disabled={!!busy}
                          onClick={() =>
                            void originalDocument(selectedDocument)
                          }
                        >
                          <ArrowDownToLine size={13} />
                          Download original
                        </button>
                        {/\.(png|jpe?g|webp|gif|bmp)$/i.test(
                          selectedDocument.name,
                        ) && (
                          <button
                            className="button small"
                            disabled={!!busy}
                            onClick={() =>
                              void originalDocument(selectedDocument, true)
                            }
                          >
                            <Search size={13} />
                            Preview image
                          </button>
                        )}
                      </div>
                      {originalPreview?.documentId === selectedDocument.id && (
                        <figure className="original-image">
                          <img
                            src={originalPreview.url}
                            alt={`Original source: ${originalPreview.name}`}
                          />
                          <figcaption>
                            {originalPreview.name} · original uploaded image
                          </figcaption>
                        </figure>
                      )}
                      <div className="extraction-controls">
                        <label className="form-label">
                          Extraction purpose
                          <select
                            aria-label="Extraction purpose"
                            value={extractionKind}
                            onChange={(e) => setExtractionKind(e.target.value)}
                          >
                            <option value="requirements">
                              Tender requirements
                            </option>
                            <option value="supplier">
                              Supplier bids / configurations
                            </option>
                            <option value="evidence">
                              Acceptance evidence
                            </option>
                          </select>
                        </label>
                        {extractionKind === "evidence" && (
                          <label className="form-label">
                            Evidence supplier
                            <select
                              aria-label="Evidence supplier"
                              value={extractionSupplier}
                              onChange={(e) =>
                                setExtractionSupplier(e.target.value)
                              }
                            >
                              <option value="">Select supplier</option>
                              {p.suppliers.map((s) => (
                                <option key={s.id} value={s.id}>
                                  {s.name}
                                </option>
                              ))}
                            </select>
                          </label>
                        )}
                        <button
                          className="button extract-button"
                          disabled={
                            !!busy ||
                            !scopeReady ||
                            (extractionKind === "evidence" &&
                              !extractionSupplier)
                          }
                          onClick={async () => {
                            const payload: Record<string, unknown> = {
                              kind: extractionKind,
                            };
                            if (extractionKind === "evidence")
                              payload.supplier_id = extractionSupplier;
                            const result = await mutate(
                              `/documents/${encodeURIComponent(selectedDocument.id)}/extract`,
                              payload,
                              "Extraction complete — review model proposals",
                            );
                            if (result !== undefined) {
                              setProposal(result);
                              if (extractionKind === "supplier")
                                setWorkspace("comparison");
                              if (extractionKind === "evidence")
                                setWorkspace("acceptance");
                            }
                          }}
                        >
                          <Layers3 size={14} />
                          Extract with Apertus
                          <ArrowUpRight size={13} />
                        </button>
                      </div>
                      {selectedDocument.spans.map((span) => (
                        <div className="source-passage" key={span.id}>
                          <div className="source-page">
                            <span>Page {span.page}</span>
                            <code>{span.id}</code>
                          </div>
                          <SourceText text={span.text} />
                        </div>
                      ))}
                      {!selectedDocument.spans.length && (
                        <p className="inline-note">
                          No extracted passages are available for this source.
                        </p>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="document-list">
                        {p.documents.map((doc, index) => (
                          <button
                            className="document-item"
                            key={doc.id}
                            onClick={() => {
                              setSelectedDoc(doc.id);
                              setSourceTitle(doc.name);
                            }}
                          >
                            <span className="document-number">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <FileText size={22} />
                            <span className="document-name">
                              <strong>{doc.name}</strong>
                              <small>
                                Rev {doc.revision} · {doc.spans.length} passages
                              </small>
                            </span>
                            <ChevronRight size={14} />
                          </button>
                        ))}
                      </div>
                      {!p.documents.length && (
                        <p className="inline-note">
                          No documents have been uploaded.
                        </p>
                      )}
                    </>
                  )}
                  <div className="upload-panel">
                    <div>
                      <Upload size={17} />
                      <strong>Add a source document</strong>
                    </div>
                    <p>
                      Upload a tender, specification, or test report. Extraction
                      creates proposals for review.
                    </p>
                    <input
                      ref={uploadRef}
                      type="file"
                      aria-label="Upload source document"
                      className="visually-hidden"
                      onChange={(e) => void upload(e.target.files?.[0])}
                    />
                    <button
                      className="button upload-button"
                      disabled={!!busy}
                      onClick={() => uploadRef.current?.click()}
                    >
                      <Plus size={14} />
                      Upload document
                    </button>
                    <small>
                      Source uploads require an authorized engineer account.
                    </small>
                  </div>
                  <div className="model-status">
                    <span className="connection-dot configured" />
                    <div>
                      <strong>
                        {health?.model_configured
                          ? "Apertus configured"
                          : "Apertus not configured"}
                      </strong>
                      <p>
                        {health?.model_configured
                          ? "New extraction requires the model server. Recorded proposals still require human approval."
                          : "Extraction is unavailable until real model credentials are configured."}
                      </p>
                    </div>
                  </div>
                  <div className="source-principle">
                    <ShieldCheck size={18} />
                    <p>A claim is only as strong as its applicable source.</p>
                  </div>
                </div>
              </aside>
            )}
          </div>
        )}
        <footer className="workspace-footer">
          <span>
            TenderProof <span>·</span> Engineering assurance
          </span>
          <span>
            {health?.database || "API connection required"} <span>·</span>{" "}
            {health?.model || "Apertus"}
            {health && !health.model_configured
              ? " · inference unavailable"
              : ""}
          </span>
        </footer>
      </main>
      {showIssues && p && (
        <ReviewQueue
          project={p}
          analysis={analysis}
          error={analysisError}
          onClose={() => setShowIssues(false)}
          onNavigate={navigateRecord}
          onInspect={inspect}
        />
      )}
      {(showMetadata || credentials || showDecision) && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) modalClose();
          }}
        >
          <div
            className="modal"
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <button
              className="modal-close"
              aria-label="Close dialog"
              onClick={modalClose}
            >
              <X size={19} />
            </button>
            {showMetadata ? (
              <>
                <span className="modal-icon">
                  <GitBranch size={23} />
                </span>
                <h2 id="modal-title">Project details</h2>
                <p>
                  Set the actual customer and one explicit equipment
                  configuration or package scope. Metadata changes create a new
                  snapshot and invalidate package approvals.
                </p>
                <label className="form-label">
                  Project name
                  <input
                    aria-label="Project name"
                    value={metadataDraft.name}
                    onChange={(e) =>
                      setMetadataDraft({
                        ...metadataDraft,
                        name: e.target.value,
                      })
                    }
                    placeholder="Procurement or contract reference"
                  />
                </label>
                <label className="form-label">
                  Customer
                  <input
                    aria-label="Customer"
                    value={metadataDraft.customer}
                    onChange={(e) =>
                      setMetadataDraft({
                        ...metadataDraft,
                        customer: e.target.value,
                      })
                    }
                    placeholder="Issuing organization"
                  />
                </label>
                <label className="form-label">
                  Equipment scope
                  <input
                    aria-label="Equipment scope"
                    title={metadataDraft.equipment}
                    value={metadataDraft.equipment}
                    onChange={(e) =>
                      setMetadataDraft({
                        ...metadataDraft,
                        equipment: e.target.value,
                      })
                    }
                    placeholder="Selected rating, equipment, and configuration"
                  />
                </label>
                <p className="inline-note">
                  An authorized engineer account is required. Keep separate
                  configurations and order-line prices distinct.
                </p>
                <div className="modal-actions">
                  <button
                    className="button"
                    onClick={() => setShowMetadata(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="button primary"
                    disabled={
                      !!busy ||
                      !metadataDraft.name.trim() ||
                      !metadataDraft.customer.trim() ||
                      !metadataDraft.equipment.trim()
                    }
                    onClick={async () => {
                      const result = await mutate(
                        "",
                        {
                          name: metadataDraft.name.trim(),
                          customer: metadataDraft.customer.trim(),
                          equipment: metadataDraft.equipment.trim(),
                        },
                        "Project details saved",
                        "PATCH",
                      );
                      if (result !== undefined) setShowMetadata(false);
                    }}
                  >
                    Save project details
                  </button>
                </div>
              </>
            ) : credentials ? (
              <>
                <span className="modal-icon">
                  <LockKeyhole size={23} />
                </span>
                <h2 id="modal-title">Connect to the live workspace</h2>
                <p>
                  The server resolves your role and project permissions from
                  this bearer token. It is stored only in this browser tab’s
                  session.
                </p>
                <label className="form-label">
                  Access token
                  <input
                    type="password"
                    autoComplete="off"
                    value={tokenDraft}
                    onChange={(e) => setTokenDraft(e.target.value)}
                    placeholder="Enter bearer token"
                  />
                </label>
                <div className="modal-actions">
                  <button
                    className="button"
                    onClick={() => setCredentials(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="button primary"
                    onClick={() => {
                      sessionStorage.setItem(
                        "tenderproof-token",
                        tokenDraft.trim(),
                      );
                      setToken(tokenDraft.trim());
                      setCredentials(false);
                    }}
                  >
                    Connect
                  </button>
                </div>
              </>
            ) : (
              <>
                <span className="modal-icon">
                  <ShieldCheck size={23} />
                </span>
                <h2 id="modal-title">Open a gate review</h2>
                <p>
                  Prototype release · ERP simulator. Checks cover reviewed
                  encoded numeric requirements in the current snapshot.
                  Unencoded obligations require engineering review; no external
                  order or shipment is executed.
                </p>
                <label className="form-label">
                  Supplier
                  <select
                    aria-label="Supplier"
                    value={decisionSupplier}
                    onChange={(e) => setDecisionSupplier(e.target.value)}
                  >
                    {p?.suppliers.map((s) => (
                      <option value={s.id} key={s.id}>
                        {s.name} · {s.configuration || "Configuration unknown"}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="form-label">
                  Release gate
                  <select
                    aria-label="Release gate"
                    value={gate}
                    onChange={(e) =>
                      setGate(e.target.value as "purchase" | "shipment")
                    }
                  >
                    <option value="purchase">
                      Purchase · Engineer + Commercial
                    </option>
                    <option value="shipment">
                      Shipment · Inspector + Commercial
                    </option>
                  </select>
                </label>
                <div className="snapshot-confirmation">
                  <GitBranch size={14} />
                  <span>
                    Bound to snapshot{" "}
                    <code>{p?.snapshot_hash.slice(0, 10)}</code>
                  </span>
                </div>
                <div className="modal-actions">
                  <button
                    className="button"
                    onClick={() => setShowDecision(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="button primary"
                    disabled={!!busy || !requirementsReady || !decisionSupplier}
                    onClick={async () => {
                      const result = await mutate(
                        "/decisions",
                        { supplier_id: decisionSupplier, gate },
                        "Gate review created",
                      );
                      if (result !== undefined) setShowDecision(false);
                    }}
                  >
                    Create gate review
                    <ArrowRight size={14} />
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {proposal !== null && (
        <div className="modal-backdrop">
          <div
            ref={dialogRef}
            className="modal proposal-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="proposal-title"
          >
            <button
              className="modal-close"
              aria-label="Close extraction result"
              onClick={() => setProposal(null)}
            >
              <X size={19} />
            </button>
            <h2 id="proposal-title">Apertus extraction result</h2>
            <p>
              These are model proposals. Confirm source, values, conditions, and
              interpretation before approving a record.
            </p>
            {extractionKind === "supplier" &&
              supplierProposalCount(proposal) !== null && (
                <p role="status">
                  {supplierProposalCount(proposal) === 0
                    ? "No supplier proposals returned. Review source coverage and equipment scope."
                    : `${supplierProposalCount(proposal)} supplier proposal${supplierProposalCount(proposal) === 1 ? "" : "s"} ready for individual review.`}
                </p>
              )}
            <pre>{JSON.stringify(proposal, null, 2)}</pre>
            <div className="modal-actions">
              <button
                className="button primary"
                onClick={() => {
                  setProposal(null);
                  setWorkspace(
                    extractionKind === "supplier"
                      ? "comparison"
                      : extractionKind === "evidence"
                        ? "acceptance"
                        : "requirements",
                  );
                }}
              >
                Review proposals
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
const doclingImageNotice =
  "<!-- 🖼️❌ Image not available. Please use `PdfPipelineOptions(generate_picture_images=True)` -->";
function SourceText({ text }: { text: string }) {
  if (text === doclingImageNotice)
    return (
      <div
        className="extraction-notice"
        role="note"
        aria-label="Extraction notice"
      >
        <strong>Extraction notice</strong>
        <p>Image content was not extracted. Inspect the original document.</p>
      </div>
    );
  return <blockquote>{text}</blockquote>;
}
function DocumentMeta({ doc }: { doc: SourceDocument }) {
  return (
    <dl className="document-meta">
      <div>
        <dt>Revision</dt>
        <dd>{doc.revision}</dd>
      </div>
      <div>
        <dt>Authority</dt>
        <dd>{doc.authority}</dd>
      </div>
      <div>
        <dt>Language</dt>
        <dd>{doc.language}</dd>
      </div>
      {doc.parsing?.page_count != null && (
        <div>
          <dt>Pages</dt>
          <dd>{doc.parsing.page_count}</dd>
        </div>
      )}
      {doc.source_url && (
        <div className="source-url-row">
          <dt>Source URL</dt>
          <dd>
            <a href={doc.source_url} target="_blank" rel="noopener noreferrer">
              {doc.source_url}
            </a>
          </dd>
        </div>
      )}
      <div className="hash-row">
        <dt>SHA-256</dt>
        <dd title={doc.sha256}>{doc.sha256}</dd>
      </div>
    </dl>
  );
}
