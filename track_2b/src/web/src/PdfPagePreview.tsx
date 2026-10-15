import { useEffect, useState } from "react";
import { LoaderCircle, X } from "lucide-react";
import type { SourceDocument } from "./types";

export default function PdfPagePreview({
  doc,
  page,
  token,
  onPageChange,
  onClose,
}: {
  doc: SourceDocument;
  page: number;
  token: string;
  onPageChange: (page: number) => void;
  onClose: () => void;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [zoom, setZoom] = useState(false);
  const [draft, setDraft] = useState(String(page));
  const [attempt, setAttempt] = useState(0);
  const pageCount = doc.parsing?.page_count;
  const validPage =
    /^\d+$/.test(draft) &&
    Number(draft) >= 1 &&
    Number(draft) <= (pageCount ?? 10000);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    let objectUrl = "";
    setLoading(true);
    setError("");
    setUrl("");
    async function load() {
      try {
        const response = await fetch(
          `/api/projects/default/documents/${encodeURIComponent(doc.id)}/pages/${page}/preview?max_dimension=1800`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
          },
        );
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(
            typeof body.detail === "string"
              ? body.detail
              : `Original page preview failed (${response.status}).`,
          );
        }
        if (response.headers.get("Content-Type")?.split(";")[0] !== "image/png")
          throw new Error(
            "The original page preview did not return a PNG image.",
          );
        const blob = await response.blob();
        if (disposed) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch (problem) {
        if (!disposed)
          setError(
            problem instanceof TypeError
              ? "Cannot reach the original-page preview API. Retry when the server is available."
              : (problem as Error).message,
          );
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void load();
    return () => {
      disposed = true;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [doc.id, page, token, attempt]);

  return (
    <section
      className="pdf-page-preview"
      aria-label="Original PDF page preview"
    >
      <div className="pdf-preview-heading">
        <h3>
          Original PDF · page {page}
          {pageCount != null ? ` of ${pageCount}` : ""}
        </h3>
        <button
          className="text-button"
          aria-label="Close page preview"
          onClick={onClose}
        >
          <X size={15} />
        </button>
      </div>
      <p className="pdf-preview-name">{doc.name}</p>
      <form
        className="pdf-preview-controls"
        aria-label="Select original PDF page"
        onSubmit={(event) => {
          event.preventDefault();
          if (validPage) onPageChange(Number(draft));
        }}
      >
        <label className="form-label">
          Original PDF page
          <input
            aria-label="Original PDF page"
            type="number"
            min={1}
            max={pageCount ?? 10000}
            step={1}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button className="button small" disabled={!validPage} type="submit">
          View page
        </button>
      </form>
      {loading && (
        <p
          role="status"
          aria-label="Page preview loading"
          className="pdf-preview-loading"
        >
          <LoaderCircle size={16} className="spin" />
          Rendering original PDF page {page}…
        </p>
      )}
      {error && (
        <div className="pdf-preview-error">
          <p role="alert">{error}</p>
          <button
            className="text-button"
            onClick={() => setAttempt(attempt + 1)}
          >
            Retry page preview
          </button>
        </div>
      )}
      {url && !error && (
        <>
          <div className="pdf-preview-actions">
            <button
              className="text-button"
              aria-pressed={zoom}
              onClick={() => setZoom(!zoom)}
            >
              {zoom ? "Fit width" : "Zoom 2×"}
            </button>
            <a
              className="source-link"
              href={url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open full preview
            </a>
          </div>
          <figure>
            <div className="pdf-preview-viewport">
              <img
                className={zoom ? "pdf-page-image zoomed" : "pdf-page-image"}
                src={url}
                alt={`Original PDF page ${page} of ${doc.name}`}
                onError={() =>
                  setError(
                    "The original page image could not be displayed. Download the original PDF to inspect it.",
                  )
                }
              />
            </div>
            <figcaption>
              Raster of the stored original PDF. Compare handwriting and form
              cells with the extracted text below.
            </figcaption>
          </figure>
        </>
      )}
    </section>
  );
}
