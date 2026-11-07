"use client";

import { useState } from "react";

type CaptionPost = { post_id: string; row_number: number; caption: string };
type ExactGroup = { normalized_caption: string; posts: CaptionPost[] };
type NearMatch = {
  caption_a: string;
  caption_b: string;
  posts_a: CaptionPost[];
  posts_b: CaptionPost[];
  similarity: number;
  category: string;
};
type UniqueCaption = { caption: string; posts: CaptionPost[] };
type ScanResult = {
  total_posts_scanned: number;
  captions_analyzed: number;
  empty_captions_skipped: number;
  exact_duplicate_groups: number;
  exact_duplicate_matches: number;
  near_duplicate_matches: number;
  unique_caption_count: number;
  exact_duplicates: ExactGroup[];
  near_duplicates: NearMatch[];
  unique_captions: UniqueCaption[];
  similarity_threshold: number;
};
type ResultTab = "exact" | "near" | "unique";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const numberFormat = new Intl.NumberFormat("en-US");

function isScanResult(value: unknown): value is ScanResult {
  if (!value || typeof value !== "object") return false;
  const result = value as Partial<ScanResult>;
  return (
    typeof result.total_posts_scanned === "number" &&
    typeof result.captions_analyzed === "number" &&
    typeof result.exact_duplicate_groups === "number" &&
    typeof result.near_duplicate_matches === "number" &&
    typeof result.unique_caption_count === "number" &&
    Array.isArray(result.exact_duplicates) &&
    Array.isArray(result.near_duplicates) &&
    Array.isArray(result.unique_captions)
  );
}

export default function DuplicatesPage() {
  const [threshold, setThreshold] = useState(0.75);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [activeTab, setActiveTab] = useState<ResultTab>("exact");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function scanDataset() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/duplicate-detection/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ similarity_threshold: threshold }),
      });
      const body: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const detail =
          body && typeof body === "object" && "detail" in body
            ? String((body as { detail: unknown }).detail)
            : "Could not scan the dataset.";
        throw new Error(detail.includes("Dataset not found")
          ? "Dataset not found. Set CONTENTIQ_DATASET_PATH to a valid CSV file."
          : detail);
      }
      if (!isScanResult(body)) {
        throw new Error("The duplicate detection service returned an unexpected response.");
      }
      setResult(body);
      setActiveTab("exact");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not connect to the duplicate detection service.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="header">
        <a className="brand" href="/">ContentIQ</a>
        <nav className="site-nav" aria-label="Main navigation">
          <a className="nav-link" href="/">Recommendations</a>
          <a className="nav-link" href="/analytics">Analytics</a>
          <a className="nav-link nav-link-active" href="/duplicates">Duplicates</a>
        </nav>
      </header>

      <section className="intro">
        <p className="eyebrow">MODULE 1 · CAPTION QUALITY</p>
        <h1>Duplicate Caption Detection</h1>
        <p>Scan dataset captions for repeated wording and close variations.</p>
      </section>

      <section className="duplicate-controls card" aria-label="Scan controls">
        <div className="duplicate-control-copy">
          <h2>Scan the dataset</h2>
          <p className="hint">Find exact matches and verify likely near matches using word overlap.</p>
        </div>
        <label className="threshold-control" htmlFor="similarity-threshold">
          <span>Near-duplicate threshold</span>
          <strong>{Math.round(threshold * 100)}%</strong>
          <input
            id="similarity-threshold"
            type="range"
            min="0.50"
            max="0.95"
            step="0.01"
            value={threshold}
            onChange={(event) => setThreshold(Number(event.target.value))}
            disabled={loading}
          />
          <span className="threshold-hint">Higher values require more similar captions.</span>
        </label>
        <button className="scan-button" type="button" onClick={scanDataset} disabled={loading}>
          {loading ? "Scanning captions…" : result ? "Scan again" : "Scan dataset"}
        </button>
      </section>

      {error && <p className="error duplicate-error" role="alert">{error}</p>}

      {!result && !loading && !error && (
        <p className="hint duplicate-empty-state">Choose a threshold and scan to see results from the configured dataset.</p>
      )}

      {loading && (
        <p className="hint duplicate-empty-state" aria-live="polite">Scanning captions and checking candidate pairs. Larger datasets can take a little while.</p>
      )}

      {result && !loading && (
        <>
          <section className="duplicate-summary" aria-label="Scan summary">
            <article className="card duplicate-stat"><span>Captions scanned</span><strong>{numberFormat.format(result.captions_analyzed)}</strong><small>{numberFormat.format(result.empty_captions_skipped)} blank skipped</small></article>
            <article className="card duplicate-stat"><span>Exact groups</span><strong>{numberFormat.format(result.exact_duplicate_groups)}</strong><small>{numberFormat.format(result.exact_duplicate_matches)} extra matching posts</small></article>
            <article className="card duplicate-stat"><span>Near matches</span><strong>{numberFormat.format(result.near_duplicate_matches)}</strong><small>At {Math.round(result.similarity_threshold * 100)}% threshold</small></article>
            <article className="card duplicate-stat"><span>Unique captions</span><strong>{numberFormat.format(result.unique_caption_count)}</strong><small>Not part of a detected match</small></article>
          </section>

          <section className="card duplicate-results" aria-label="Detection results" aria-live="polite">
            <div className="duplicate-tabs" role="tablist" aria-label="Result category">
              <button role="tab" aria-selected={activeTab === "exact"} className={activeTab === "exact" ? "duplicate-tab active" : "duplicate-tab"} onClick={() => setActiveTab("exact")} type="button">Exact ({result.exact_duplicates.length})</button>
              <button role="tab" aria-selected={activeTab === "near"} className={activeTab === "near" ? "duplicate-tab active" : "duplicate-tab"} onClick={() => setActiveTab("near")} type="button">Near ({result.near_duplicates.length})</button>
              <button role="tab" aria-selected={activeTab === "unique"} className={activeTab === "unique" ? "duplicate-tab active" : "duplicate-tab"} onClick={() => setActiveTab("unique")} type="button">Unique ({result.unique_captions.length})</button>
            </div>

            {activeTab === "exact" && (result.exact_duplicates.length ? (
              <div className="duplicate-list">
                {result.exact_duplicates.map((group) => (
                  <article className="duplicate-item" key={group.normalized_caption}>
                    <div className="duplicate-caption"><span className="result-label">Normalized caption</span><p>{group.normalized_caption}</p></div>
                    <div className="post-reference-list">{group.posts.map((post) => <div className="post-reference" key={`${post.post_id}-${post.row_number}`}><strong>Post {post.post_id}</strong><span>Row {post.row_number}</span><p>{post.caption}</p></div>)}</div>
                  </article>
                ))}
              </div>
            ) : <p className="hint result-empty">No exact duplicate groups found.</p>)}

            {activeTab === "near" && (result.near_duplicates.length ? (
              <div className="duplicate-list">
                {result.near_duplicates.map((match) => (
                  <article className="duplicate-item near-item" key={`${match.posts_a[0]?.row_number}-${match.posts_b[0]?.row_number}`}>
                    <div className="similarity-badge">{(match.similarity * 100).toFixed(1)}% similar</div>
                    <div className="near-captions">
                      <div className="duplicate-caption"><span className="result-label">Caption A · Post {match.posts_a.map((post) => post.post_id).join(", ")}</span><p>{match.caption_a}</p></div>
                      <div className="duplicate-caption"><span className="result-label">Caption B · Post {match.posts_b.map((post) => post.post_id).join(", ")}</span><p>{match.caption_b}</p></div>
                    </div>
                  </article>
                ))}
              </div>
            ) : <p className="hint result-empty">No near-duplicate pairs met this threshold.</p>)}

            {activeTab === "unique" && (result.unique_captions.length ? (
              <div className="duplicate-list">
                {result.unique_captions.map((item) => (
                  <article className="unique-item" key={`${item.posts[0]?.row_number}-${item.caption}`}>
                    <p>{item.caption}</p><span>Post {item.posts.map((post) => post.post_id).join(", ")} · Row {item.posts[0]?.row_number}</span>
                  </article>
                ))}
              </div>
            ) : <p className="hint result-empty">Every analyzed caption belongs to a detected duplicate group.</p>)}
          </section>
        </>
      )}

      <details className="card how-it-works">
        <summary>How it works</summary>
        <ol>
          <li>Captions are Unicode-normalized, lowercased, and tokenized. Punctuation separates words; hashtags and emoji symbols are retained.</li>
          <li>A custom hash table groups captions with the same normalized text for exact duplicate detection.</li>
          <li>Word shingles represent short runs of up to three tokens. MinHash creates deterministic signatures for those sets.</li>
          <li>LSH banding narrows the candidate pairs. Exact Jaccard similarity verifies each candidate against the selected threshold.</li>
        </ol>
        <p className="hint">LSH is a candidate filter, so a similar pair can be missed if its signatures do not share a band. The threshold is applied to exact Jaccard similarity.</p>
      </details>
    </main>
  );
}
