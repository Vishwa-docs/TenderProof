import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  AlertTriangle,
  Check,
  ChevronRight,
  FileSearch,
  FileText,
  GitBranch,
  Layers3,
  LoaderCircle,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import type {
  PackageAnalysis,
  Project,
  ReviewDossier,
  ReviewIssue,
  SnapshotDiff,
  SnapshotList,
  SourceSearchResponse,
} from "./types";

type Read = (path: string) => Promise<unknown>;
type Inspect = (ids: string[], title: string) => void;
export type NavigateRecord = (
  type: string,
  id: string,
  documentId: string | null,
  sourceIds: string[],
) => void;
const endpoint = "/api/projects/default";
function readable(value: unknown): string {
  return value == null
    ? "Not recorded"
    : typeof value === "object"
      ? JSON.stringify(value, null, 2)
      : String(value);
}
function failure(error: unknown) {
  return error instanceof Error
    ? error.message
    : "The request failed. Retry when the API is available.";
}
function shorten(hash: string) {
  return hash.slice(0, 10);
}
function State({ value }: { value: string }) {
  return (
    <span className={`state-label ${value.replaceAll("_", "-")}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
function Loading({ label }: { label: string }) {
  return (
    <p className="read-loading" role="status">
      <LoaderCircle size={18} className="spin" aria-hidden="true" />
      {label}
    </p>
  );
}
function ReadError({ message }: { message: string }) {
  return (
    <p className="read-error" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      {message}
    </p>
  );
}

export function ReleaseStatus({
  project,
  analysis,
  onReview,
}: {
  project: Project;
  analysis: PackageAnalysis | null;
  onReview: () => void;
}) {
  const runs = (project.extraction_runs || []).filter(
    (run) => run.status !== "recorded" || run.conditions.length,
  );
  const pending = project.requirements.filter(
    (row) => row.status === "pending",
  ).length;
  const count = analysis?.summary.issue_count;
  const blocked =
    analysis?.release_gates
      .filter((gate) => gate.status === "blocked")
      .map((gate) => gate.gate) || [];
  const heading = analysis
    ? blocked.length === 2
      ? "Purchase and shipment blocked"
      : blocked.length
        ? `${blocked[0] === "purchase" ? "Purchase" : "Shipment"} blocked`
        : "Release review required"
    : runs.length
      ? "Purchase and shipment blocked"
      : "Release status awaits analysis";
  return (
    <section className="release-status" aria-label="Release status">
      <ShieldCheck size={22} aria-hidden="true" />
      <div className="release-status-copy">
        <strong>{heading}</strong>
        <span>
          {analysis
            ? `${analysis.summary.blocking_issue_count} blocking issues · ${pending} requirements pending`
            : `${runs.length} incomplete extraction runs · ${pending} requirements pending`}
        </span>
      </div>
      {analysis && (
        <div className="gate-statuses">
          {analysis.release_gates.map((gate) => (
            <span key={gate.gate}>
              {gate.gate === "purchase" ? "Purchase" : "Shipment"}
              <State value={gate.status} />
            </span>
          ))}
        </div>
      )}
      <button className="button" onClick={onReview}>
        Review issues{count != null ? ` (${count})` : ""}
        <ArrowRight size={16} aria-hidden="true" />
      </button>
    </section>
  );
}

export function Overview({
  project,
  analysis,
  analysisError,
  read,
  onReview,
  onNavigate,
  onEvidence,
  onRequirements,
  onOffers,
  onRelease,
}: {
  project: Project;
  analysis: PackageAnalysis | null;
  analysisError: string;
  read: Read;
  onReview: () => void;
  onNavigate: NavigateRecord;
  onEvidence: () => void;
  onRequirements: () => void;
  onOffers: () => void;
  onRelease: () => void;
}) {
  const pending = project.requirements.filter(
    (row) => row.status === "pending",
  ).length;
  const offers = (project.proposals || []).filter(
    (row) => row.kind === "supplier" && row.status === "pending",
  ).length;
  const corrections = [
    ...(project.proposals || []),
    ...project.suppliers,
  ].reduce((sum, row) => sum + (row.price_corrections?.length || 0), 0);
  const priority =
    analysis?.issues
      .filter((issue) => issue.severity === "blocking")
      .slice(0, 4) || [];
  return (
    <div className="overview-workspace">
      <section className="package-intro">
        <div>
          <span className="section-kicker">Current package</span>
          <h2>{project.name || "Untitled project"}</h2>
          <p>{project.customer || "Customer not recorded"}</p>
        </div>
        <div className="package-revision">
          <GitBranch size={18} aria-hidden="true" />
          <span>
            Revision {project.version}
            <code>{shorten(project.snapshot_hash)}</code>
          </span>
        </div>
        <p className="equipment-scope">
          {project.equipment || "Set the equipment scope before extraction."}
        </p>
      </section>
      <div className="overview-metrics" aria-label="Package counts">
        <button onClick={onEvidence}>
          <FileText size={20} aria-hidden="true" />
          <strong>{project.documents.length}</strong>
          <span>Source documents</span>
          <small>
            {project.documents.reduce((n, d) => n + d.spans.length, 0)} retained
            passages
          </small>
        </button>
        <button onClick={onRequirements}>
          <Layers3 size={20} aria-hidden="true" />
          <strong>{pending}</strong>
          <span>Requirements pending</span>
          <small>{project.requirements.length} total requirements</small>
        </button>
        <button onClick={onOffers}>
          <FileSearch size={20} aria-hidden="true" />
          <strong>{offers}</strong>
          <span>Offers pending</span>
          <small>{project.suppliers.length} approved supplier records</small>
        </button>
        <button onClick={onRelease}>
          <ShieldCheck size={20} aria-hidden="true" />
          <strong>{project.evidence.length}</strong>
          <span>Acceptance records</span>
          <small>
            {project.decisions.filter((d) => d.status === "released").length}{" "}
            released decisions
          </small>
        </button>
      </div>
      <div className="overview-columns">
        <section className="workbench-panel next-review">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Next actions</span>
              <h2>Resolve review blockers</h2>
            </div>
            <span className="count-pill">
              {analysis?.summary.blocking_issue_count ?? "—"}
            </span>
          </div>
          {analysisError ? (
            <ReadError message={analysisError} />
          ) : !analysis ? (
            <Loading label="Loading review issues" />
          ) : priority.length ? (
            <div className="priority-list">
              {priority.map((issue) => (
                <button
                  key={issue.id}
                  onClick={() =>
                    onNavigate(
                      issue.next_action.target,
                      issue.next_action.record_id || issue.record_id,
                      issue.next_action.document_id || issue.document_id,
                      issue.source_ids,
                    )
                  }
                >
                  <span className="issue-priority-dot" />
                  <span>
                    <strong>{issue.title}</strong>
                    <small>{issue.next_action.label}</small>
                  </span>
                  <ArrowUpRight size={18} aria-hidden="true" />
                </button>
              ))}
            </div>
          ) : (
            <p className="empty-copy">
              No blocking issue appears in this snapshot. Required role
              approvals still apply.
            </p>
          )}
          <button className="text-button" onClick={onReview}>
            Open complete review queue
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </section>
        <section className="workbench-panel dossier-panel">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Review handoff</span>
              <h2>Export a review dossier</h2>
            </div>
            <ArrowDownToLine size={22} aria-hidden="true" />
          </div>
          <p>
            Share the source catalog, pending claims, corrections, and release
            blockers for this snapshot.
          </p>
          <div className="dossier-details">
            <span>
              <GitBranch size={16} aria-hidden="true" />
              Snapshot-bound records
            </span>
            <span>
              <FileText size={16} aria-hidden="true" />
              {analysis?.summary.correction_count ?? corrections} recorded
              corrections
            </span>
            <span>
              <ShieldCheck size={16} aria-hidden="true" />
              Draft review; no release approval
            </span>
          </div>
          <DossierExport read={read} project={project} />
        </section>
      </div>
      <section className="workbench-panel">
        <div className="panel-heading">
          <div>
            <span className="section-kicker">Evidence path</span>
            <h2>Follow a claim to its source</h2>
          </div>
          <button className="text-button" onClick={onEvidence}>
            Open evidence workspace
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
        <div className="workflow-path">
          <span>
            <FileText size={20} aria-hidden="true" />
            <strong>Original documents</strong>
            <small>Hashes and page references</small>
          </span>
          <ChevronRight aria-hidden="true" />
          <span>
            <Layers3 size={20} aria-hidden="true" />
            <strong>Extracted claims</strong>
            <small>Requirements and offers</small>
          </span>
          <ChevronRight aria-hidden="true" />
          <span>
            <Check size={20} aria-hidden="true" />
            <strong>Qualified review</strong>
            <small>Meaning and applicability</small>
          </span>
          <ChevronRight aria-hidden="true" />
          <span>
            <ShieldCheck size={20} aria-hidden="true" />
            <strong>Release gates</strong>
            <small>Required role approvals</small>
          </span>
        </div>
      </section>
    </div>
  );
}

export function ReviewQueue({
  project,
  analysis,
  error,
  onClose,
  onNavigate,
  onInspect,
}: {
  project: Project;
  analysis: PackageAnalysis | null;
  error: string;
  onClose: () => void;
  onNavigate: NavigateRecord;
  onInspect: Inspect;
}) {
  const [severity, setSeverity] = useState("all"),
    [query, setQuery] = useState(""),
    [limit, setLimit] = useState(20);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement;
    ref.current?.querySelector<HTMLElement>("button")?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const fields = [
          ...ref.current!.querySelectorAll<HTMLElement>(
            "button:not(:disabled),input,select,summary,a[href]",
          ),
        ];
        const first = fields[0],
          last = fields.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      opener?.focus();
    };
  }, []);
  const issues = (analysis?.issues || []).filter(
    (issue) =>
      (severity === "all" || issue.severity === severity) &&
      `${issue.title} ${issue.detail} ${issue.type}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <div
      className="modal-backdrop queue-backdrop"
      onMouseDown={(e) => {
        if (e.currentTarget === e.target) onClose();
      }}
    >
      <div
        className="review-queue"
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-queue-title"
        ref={ref}
      >
        <div className="queue-heading">
          <div>
            <span className="section-kicker">
              Snapshot {shorten(project.snapshot_hash)}
            </span>
            <h2 id="review-queue-title">Review issues</h2>
            <p>
              Reviewing a claim does not clear omitted obligations or failed
              audits.
            </p>
          </div>
          <button
            className="icon-button"
            aria-label="Close review issues"
            onClick={onClose}
          >
            <X size={22} />
          </button>
        </div>
        <div className="queue-tools">
          <label className="search-field">
            <Search size={18} aria-hidden="true" />
            <input
              aria-label="Filter review issues"
              placeholder="Find a document, claim, or issue"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setLimit(20);
              }}
            />
          </label>
          <label className="compact-label">
            Severity
            <select
              aria-label="Issue severity"
              value={severity}
              onChange={(event) => {
                setSeverity(event.target.value);
                setLimit(20);
              }}
            >
              <option value="all">All issues</option>
              <option value="blocking">Blocking</option>
              <option value="review">Review</option>
              <option value="info">Information</option>
            </select>
          </label>
        </div>
        <div className="queue-body">
          {error ? (
            <ReadError message={error} />
          ) : !analysis ? (
            <Loading label="Loading review issues" />
          ) : (
            <>
              <p className="result-summary">
                {issues.length} issues · {analysis.summary.blocking_issue_count}{" "}
                block release
              </p>
              {issues.slice(0, limit).map((issue) => (
                <article className="review-issue" key={issue.id}>
                  <div className="issue-title">
                    <State value={issue.severity} />
                    <span className="muted">
                      {issue.record_type.replaceAll("_", " ")}
                    </span>
                    <span className="issue-gates">
                      {issue.gates.join(" · ")}
                    </span>
                  </div>
                  <h3>{issue.title}</h3>
                  <p>{issue.detail}</p>
                  <div className="issue-actions">
                    <button
                      className="button small"
                      onClick={() => {
                        onNavigate(
                          issue.next_action.target,
                          issue.next_action.record_id || issue.record_id,
                          issue.next_action.document_id || issue.document_id,
                          issue.source_ids,
                        );
                        onClose();
                      }}
                    >
                      {issue.next_action.label}
                      <ArrowRight size={15} aria-hidden="true" />
                    </button>
                    {!!issue.source_ids.length && (
                      <button
                        className="source-link"
                        onClick={() => {
                          onInspect(issue.source_ids, issue.title);
                          onClose();
                        }}
                      >
                        <FileText size={16} aria-hidden="true" />
                        Inspect source
                      </button>
                    )}
                  </div>
                </article>
              ))}
              {!issues.length && (
                <p className="empty-copy">
                  No issues match these filters. The release state remains
                  unchanged.
                </p>
              )}
              {issues.length > limit && (
                <button className="button" onClick={() => setLimit(limit + 20)}>
                  Show 20 more issues
                </button>
              )}
            </>
          )}
          <details className="raw-extraction">
            <summary>
              Raw extraction records ({project.extraction_runs?.length || 0})
            </summary>
            <section aria-label="Extraction assurance">
              <h3>Extraction assurance requires review</h3>
              <p>
                These records preserve the conditions attached to this package.
              </p>
              {(project.extraction_runs || []).map((run) => (
                <details key={run.id}>
                  <summary>
                    {project.documents.find((doc) => doc.id === run.document_id)
                      ?.name || "Unresolved source"}{" "}
                    · {run.kind || "unknown purpose"}
                  </summary>
                  <ul>
                    {run.conditions.map((condition, index) => (
                      <li key={index}>{condition}</li>
                    ))}
                  </ul>
                  <code>Run {run.id}</code>
                </details>
              ))}
            </section>
          </details>
        </div>
      </div>
    </div>
  );
}

export function EvidenceWorkspace({
  project,
  analysis,
  analysisError,
  read,
  onInspect,
  onNavigate,
  onDocument,
}: {
  project: Project;
  analysis: PackageAnalysis | null;
  analysisError: string;
  read: Read;
  onInspect: Inspect;
  onNavigate: NavigateRecord;
  onDocument: (id: string) => void;
}) {
  const [query, setQuery] = useState(""),
    [documentId, setDocumentId] = useState(""),
    [selection, setSelection] = useState<string | null>(null);
  const [result, setResult] = useState<SourceSearchResponse | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const requestId = useRef(0);
  useEffect(
    () => () => {
      requestId.current += 1;
    },
    [],
  );
  async function search(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    const id = ++requestId.current;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const params = new URLSearchParams({ q: query.trim(), limit: "12" });
      if (documentId) params.set("document_id", documentId);
      const value = (await read(
        `${endpoint}/search?${params}`,
      )) as SourceSearchResponse;
      if (
        !Array.isArray(value.results) ||
        typeof value.total_matches !== "number"
      )
        throw new Error("Source search returned an invalid response.");
      if (value.snapshot_hash !== project.snapshot_hash)
        throw new Error(
          "The package changed. Refresh the workspace before searching again.",
        );
      if (id === requestId.current) setResult(value);
    } catch (e) {
      if (id === requestId.current) setError(failure(e));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }
  const selected = analysis?.documents.find(
    (doc) => doc.document_id === selection,
  );
  const linkedIds = new Set([`document:${selection}`]);
  for (const edge of analysis?.lineage.edges || []) {
    if (edge.source === `document:${selection}`) linkedIds.add(edge.target);
  }
  const nodes =
    analysis?.lineage.nodes.filter(
      (node) => linkedIds.has(node.id) || node.document_id === selection,
    ) || [];
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges =
    analysis?.lineage.edges.filter(
      (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target),
    ) || [];
  return (
    <div className="evidence-workspace">
      <section className="source-search-panel">
        <div className="panel-heading">
          <div>
            <span className="section-kicker">Search original text</span>
            <h2>Find the source behind a claim</h2>
          </div>
          <FileSearch size={26} aria-hidden="true" />
        </div>
        <p>
          Search retained document passages. Open the cited page to check the
          original evidence.
        </p>
        <form className="source-search-form" onSubmit={search}>
          <label className="search-field">
            <Search size={19} aria-hidden="true" />
            <input
              aria-label="Search source text"
              placeholder="Search a rating, price, clause, or drawing reference"
              maxLength={300}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select
            aria-label="Search document"
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
          >
            <option value="">All documents</option>
            {project.documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.name}
              </option>
            ))}
          </select>
          <button className="button primary" disabled={!query.trim()}>
            Search sources
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </form>
      </section>
      {loading && <Loading label="Searching retained passages" />}
      {error && <ReadError message={error} />}
      {result && (
        <section className="search-results" aria-label="Source search results">
          <div className="panel-heading">
            <h2>
              {result.total_matches} matching passage
              {result.total_matches === 1 ? "" : "s"}
            </h2>
            <span className="method-label">{result.retrieval_method}</span>
          </div>
          <p className="result-summary">
            {result.score_meaning} Results belong to snapshot{" "}
            {shorten(result.snapshot_hash)}.
          </p>
          {!result.results.length ? (
            <div className="empty-state">
              <FileSearch size={30} aria-hidden="true" />
              <h3>No matching source passages</h3>
              <p>Try a shorter source phrase or choose another document.</p>
            </div>
          ) : (
            result.results.map((match, index) => (
              <article className="search-result" key={match.source_id}>
                <div className="search-result-heading">
                  <span className="result-rank">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <h3>{match.document_name}</h3>
                    <span>
                      Page {match.page} · lexical score {match.score.toFixed(3)}
                    </span>
                  </div>
                  <button
                    className="button small"
                    aria-label={`Inspect passage on page ${match.page}`}
                    onClick={() =>
                      onInspect(
                        [match.source_id],
                        `${match.document_name} · page ${match.page}`,
                      )
                    }
                  >
                    Inspect passage
                    <ArrowUpRight size={16} aria-hidden="true" />
                  </button>
                </div>
                <blockquote>{match.text}</blockquote>
                {match.text_truncated && (
                  <p className="inline-note">
                    Bounded excerpt. Open the source to inspect the complete
                    passage.
                  </p>
                )}
                <div className="search-result-meta">
                  <code>{match.source_id}</code>
                  <span>SHA-256 {shorten(match.sha256)}</span>
                </div>
                {!!match.context.length && (
                  <details>
                    <summary>Adjacent source context</summary>
                    {match.context.map((context) => (
                      <div className="context-passage" key={context.source_id}>
                        <span>Page {context.page}</span>
                        <blockquote>{context.text}</blockquote>
                        <button
                          className="source-link"
                          onClick={() =>
                            onInspect(
                              [context.source_id],
                              "Adjacent source context",
                            )
                          }
                        >
                          Inspect context
                          <ArrowUpRight size={14} aria-hidden="true" />
                        </button>
                      </div>
                    ))}
                  </details>
                )}
                {match.duplicate_count > 0 && (
                  <details>
                    <summary>
                      {match.duplicate_count} duplicate citation
                      {match.duplicate_count === 1 ? "" : "s"}; not independent
                      evidence
                    </summary>
                    {match.duplicate_citations.map((citation) => (
                      <button
                        className="source-link"
                        key={citation.source_id}
                        onClick={() =>
                          onInspect(
                            [citation.source_id],
                            citation.document_name,
                          )
                        }
                      >
                        {citation.document_name} · page {citation.page}
                      </button>
                    ))}
                  </details>
                )}
              </article>
            ))
          )}
        </section>
      )}
      <section className="workbench-panel">
        <div className="panel-heading">
          <div>
            <span className="section-kicker">Coverage and provenance</span>
            <h2>Document coverage</h2>
          </div>
          <span className="count-pill">{project.documents.length} sources</span>
        </div>
        <p className="panel-description">
          Citation coverage measures linked passages. It does not measure
          extraction accuracy or completeness.
        </p>
        {analysisError ? (
          <ReadError message={analysisError} />
        ) : !analysis ? (
          <Loading label="Loading document coverage" />
        ) : (
          <div className="coverage-table-wrap">
            <table className="coverage-table">
              <thead>
                <tr>
                  <th>Source document</th>
                  <th>Linked passages</th>
                  <th>Records</th>
                  <th>Extraction</th>
                  <th>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {analysis.documents.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className={selection === doc.document_id ? "selected" : ""}
                  >
                    <th>
                      <button
                        className="document-title-button"
                        onClick={() => onDocument(doc.document_id)}
                      >
                        {doc.name}
                        <ArrowUpRight size={14} aria-hidden="true" />
                      </button>
                      <small>
                        {doc.page_count == null
                          ? "Page count not recorded"
                          : `${doc.page_count} pages`}{" "}
                        · {doc.span_count} passages
                      </small>
                    </th>
                    <td>
                      <strong>
                        {doc.cited_span_count} / {doc.span_count}
                      </strong>
                      <div
                        className="coverage-meter"
                        aria-label={`${Math.round(doc.citation_coverage * 100)} percent of passages cited`}
                      >
                        <span
                          style={{
                            width: `${Math.min(100, Math.max(0, doc.citation_coverage * 100))}%`,
                          }}
                        />
                      </div>
                    </td>
                    <td>
                      {doc.requirement_count} requirements
                      <br />
                      {doc.proposal_count} proposals
                    </td>
                    <td>
                      <State value={doc.assurance_status} />
                    </td>
                    <td>
                      <button
                        className="button small"
                        aria-label={`View lineage for ${doc.name}`}
                        onClick={() =>
                          setSelection(
                            selection === doc.document_id
                              ? null
                              : doc.document_id,
                          )
                        }
                      >
                        View links
                        <GitBranch size={16} aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!analysis.documents.length && (
              <p className="empty-copy">
                Upload an original source document to begin.
              </p>
            )}
          </div>
        )}
      </section>
      {selected && analysis && (
        <section
          className="workbench-panel lineage-panel"
          aria-label="Source lineage"
        >
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Source lineage</span>
              <h2>{selected.name}</h2>
            </div>
            <button
              className="icon-button"
              aria-label="Close source lineage"
              onClick={() => setSelection(null)}
            >
              <X size={20} />
            </button>
          </div>
          <p className="panel-description">
            {nodes.length} linked records · {edges.length} stored relationships
          </p>
          <div className="lineage-records">
            {nodes
              .filter((node) => node.type !== "document")
              .map((node) => {
                const relationships = edges.filter(
                  (edge) => edge.target === node.id || edge.source === node.id,
                );
                return (
                  <article key={node.id}>
                    <GitBranch size={21} aria-hidden="true" />
                    <div>
                      <span className="section-kicker">
                        {node.type.replaceAll("_", " ")}
                      </span>
                      <h3>{node.label}</h3>
                      {relationships.map((edge, index) => (
                        <small key={`${edge.source}-${edge.target}-${index}`}>
                          {edge.relation.replaceAll("_", " ")}
                        </small>
                      ))}
                      <code>{node.record_id}</code>
                    </div>
                    <button
                      className="button small"
                      aria-label={`Open ${node.label}`}
                      onClick={() =>
                        onNavigate(
                          node.type,
                          node.record_id,
                          node.document_id,
                          node.source_ids,
                        )
                      }
                    >
                      Open record
                      <ArrowUpRight size={15} aria-hidden="true" />
                    </button>
                  </article>
                );
              })}
          </div>
          {nodes.length <= 1 && (
            <p className="empty-copy">
              No claim links appear for this document in the current snapshot.
            </p>
          )}
          {analysis.lineage.truncated && (
            <p className="inline-note">
              The server bounded this graph to {analysis.lineage.limit} records.
              Additional links may exist.
            </p>
          )}
        </section>
      )}
    </div>
  );
}

export function SnapshotComparison({
  project,
  read,
  onInspect,
}: {
  project: Project;
  read: Read;
  onInspect: Inspect;
}) {
  const [list, setList] = useState<SnapshotList | null>(null),
    [from, setFrom] = useState(""),
    [to, setTo] = useState(project.snapshot_hash),
    [result, setResult] = useState<SnapshotDiff | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const comparisonId = useRef(0);
  useEffect(() => {
    let active = true;
    setList(null);
    setResult(null);
    setError("");
    read(`${endpoint}/snapshots`)
      .then((raw) => {
        const value = raw as SnapshotList;
        if (!Array.isArray(value.snapshots))
          throw new Error("Snapshot history returned an invalid response.");
        if (value.snapshot_hash !== project.snapshot_hash)
          throw new Error(
            "The package changed. Refresh before comparing snapshots.",
          );
        if (active) {
          setList(value);
          setTo(value.current_snapshot_hash);
          setFrom(
            value.snapshots.find(
              (row) => row.snapshot_hash !== value.current_snapshot_hash,
            )?.snapshot_hash || value.current_snapshot_hash,
          );
        }
      })
      .catch((e) => {
        if (active) setError(failure(e));
      });
    return () => {
      active = false;
      comparisonId.current += 1;
    };
  }, [project.snapshot_hash]);
  async function compare() {
    const id = ++comparisonId.current;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const params = new URLSearchParams({ from_hash: from, to_hash: to });
      const value = (await read(`${endpoint}/diff?${params}`)) as SnapshotDiff;
      if (!Array.isArray(value.changes) || !value.summary)
        throw new Error("Snapshot comparison returned an invalid response.");
      if (
        value.snapshot_hash !== project.snapshot_hash ||
        value.from_hash !== from ||
        value.to_hash !== to
      )
        throw new Error(
          "The package changed. Refresh before comparing snapshots.",
        );
      if (id === comparisonId.current) setResult(value);
    } catch (e) {
      if (id === comparisonId.current) setError(failure(e));
    } finally {
      if (id === comparisonId.current) setLoading(false);
    }
  }
  return (
    <section className="snapshot-comparison workbench-panel">
      <div className="panel-heading">
        <div>
          <span className="section-kicker">Revision review</span>
          <h2>Compare package snapshots</h2>
        </div>
        <GitBranch size={24} aria-hidden="true" />
      </div>
      <p className="panel-description">
        Inspect stored record changes before reviewing a revised package.
      </p>
      {error && <ReadError message={error} />}
      <div className="snapshot-selectors">
        <label className="form-label">
          From snapshot
          <select
            aria-label="From snapshot"
            disabled={loading}
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setResult(null);
            }}
          >
            {list?.snapshots.map((row) => (
              <option key={row.snapshot_hash} value={row.snapshot_hash}>
                Revision {row.version} · {shorten(row.snapshot_hash)}
                {row.is_current ? " · current" : ""}
              </option>
            ))}
          </select>
        </label>
        <ArrowRight size={20} aria-hidden="true" />
        <label className="form-label">
          To snapshot
          <select
            aria-label="To snapshot"
            disabled={loading}
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setResult(null);
            }}
          >
            {list?.snapshots.map((row) => (
              <option key={row.snapshot_hash} value={row.snapshot_hash}>
                Revision {row.version} · {shorten(row.snapshot_hash)}
                {row.is_current ? " · current" : ""}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button primary"
          disabled={!list || loading || !from || !to}
          onClick={() => void compare()}
        >
          Compare snapshots
        </button>
      </div>
      {loading && <Loading label="Comparing stored snapshots" />}
      {list?.truncated && (
        <p className="inline-note">
          Showing {list.snapshots.length} of {list.total_count} snapshots.
        </p>
      )}
      {result && (
        <section className="snapshot-changes" aria-label="Snapshot changes">
          <div className="change-summary">
            <span>
              <strong>{result.summary.added}</strong> added
            </span>
            <span>
              <strong>{result.summary.modified}</strong> modified
            </span>
            <span>
              <strong>{result.summary.removed}</strong> removed
            </span>
            <span>{result.impacted_records.length} impacted records</span>
          </div>
          {!result.changed && (
            <p className="empty-copy">
              These snapshots contain no record changes.
            </p>
          )}
          {result.changes.map((change, index) => (
            <article
              className="snapshot-change"
              key={`${change.collection}-${change.record_id}-${index}`}
            >
              <div className="panel-heading">
                <h3>{change.label}</h3>
                <State value={change.change} />
              </div>
              <p className="result-summary">
                {change.collection} · <code>{change.record_id}</code>
              </p>
              <div className="diff-table-wrap">
                <table className="diff-table">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Before</th>
                      <th>After</th>
                    </tr>
                  </thead>
                  <tbody>
                    {change.fields.map((field, index) => (
                      <tr key={`${field.path}-${index}`}>
                        <th>{field.path}</th>
                        <td>
                          <pre>{readable(field.before)}</pre>
                        </td>
                        <td>
                          <pre>{readable(field.after)}</pre>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!!change.source_ids.length && (
                <button
                  className="source-link"
                  aria-label="Inspect changed record sources"
                  onClick={() => onInspect(change.source_ids, change.label)}
                >
                  <FileText size={16} aria-hidden="true" />
                  Inspect source references
                </button>
              )}
            </article>
          ))}
        </section>
      )}
    </section>
  );
}

function markdownCell(value: unknown) {
  return readable(value).replaceAll("|", "\\|").replaceAll("\n", " ");
}
export function dossierMarkdown(packet: ReviewDossier, project: Project) {
  const lines = [
    `# ${project.name || packet.project_id}: draft review dossier`,
    "",
    "> Draft review. This packet does not grant purchase or shipment approval.",
    "",
    packet.meaning,
    "",
    `- Project: ${packet.project_id}`,
    `- Revision: ${packet.version}`,
    `- Snapshot: ${packet.snapshot_hash}`,
    `- Canonical JSON packet SHA-256: ${packet.packet_hash}`,
    "",
    "## Release gates",
    "",
    "| Gate | State | Linked issues |",
    "| --- | --- | --- |",
    ...packet.release_gates.map(
      (gate) =>
        `| ${gate.gate} | ${gate.status.replaceAll("_", " ")} | ${gate.issue_ids.length} |`,
    ),
    "",
    "## Review issues",
    "",
    ...packet.issues.flatMap((issue) => [
      `### ${issue.title}`,
      "",
      `**${issue.severity}** · ${issue.record_type} · ${issue.record_id}`,
      "",
      issue.detail,
      "",
      `Next action: ${issue.next_action.label}`,
      `Source references: ${issue.source_ids.join(", ") || "None recorded"}`,
      "",
    ]),
    "## Source catalog",
    "",
    "| Document | SHA-256 |",
    "| --- | --- |",
    ...packet.source_catalog.map(
      (doc) =>
        `| ${markdownCell(doc.name || doc.document_id || doc.id)} | ${markdownCell(doc.sha256)} |`,
    ),
    "",
  ];
  for (const [title, records] of [
    ["Requirements", packet.requirements],
    ["Proposals", packet.proposals],
    ["Suppliers", packet.suppliers],
    ["Acceptance evidence", packet.evidence],
    ["Corrections", packet.corrections],
    ["Extraction runs", packet.extraction_runs],
    ["Decisions", packet.decisions],
  ] as [string, Record<string, unknown>[]][]) {
    lines.push(`## ${title}`, "");
    if (!records.length) lines.push("No records in this snapshot.", "");
    for (const record of records) {
      lines.push(
        `### ${readable(record.title || record.name || record.id || title)}`,
        "",
        "```json",
        JSON.stringify(record, null, 2),
        "```",
        "",
      );
    }
  }
  lines.push(
    "## Source lineage",
    "",
    "```json",
    JSON.stringify(packet.lineage, null, 2),
    "```",
    "",
  );
  return lines.join("\n");
}
function DossierExport({ read, project }: { read: Read; project: Project }) {
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  async function exportFile(format: "json" | "md") {
    setBusy(format);
    setError("");
    setNotice("");
    try {
      const packet = (await read(`${endpoint}/dossier`)) as ReviewDossier;
      if (
        packet.packet_type !== "draft_review_dossier" ||
        packet.status !== "draft" ||
        !packet.packet_hash
      )
        throw new Error("The server did not return a draft review dossier.");
      if (packet.snapshot_hash !== project.snapshot_hash)
        throw new Error(
          "The package changed. Refresh before exporting a dossier.",
        );
      const body =
        format === "md"
          ? dossierMarkdown(packet, project)
          : JSON.stringify(packet, null, 2);
      const url = URL.createObjectURL(
        new Blob([body], {
          type:
            format === "md"
              ? "text/markdown;charset=utf-8"
              : "application/json",
        }),
      );
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `tenderproof-draft-review-r${packet.version}-${shorten(packet.snapshot_hash)}.${format}`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice(
        `Draft ${format === "md" ? "Markdown" : "JSON"} dossier downloaded.`,
      );
    } catch (e) {
      setError(failure(e));
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <div className="dossier-export-actions">
        <button
          className="button primary"
          disabled={!!busy}
          onClick={() => void exportFile("md")}
        >
          <ArrowDownToLine size={17} aria-hidden="true" />
          {busy === "md" ? "Preparing Markdown…" : "Export Markdown"}
        </button>
        <button
          className="button"
          disabled={!!busy}
          onClick={() => void exportFile("json")}
        >
          {busy === "json" ? "Preparing JSON…" : "Export JSON"}
        </button>
      </div>
      {error && <ReadError message={error} />}
      <p className="export-notice" role="status">
        {notice}
      </p>
    </>
  );
}
