"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type Overview = {
  total_posts: number;
  posts_with_hashtags: number;
  unique_hashtags: number;
  total_hashtag_uses: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
};

type Hashtag = {
  hashtag: string;
  usage_count: number;
  average_likes: number;
  average_comments: number;
  average_shares: number;
  average_engagement: number;
};

type RelatedHashtag = {
  hashtag: string;
  cooccurrences: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const numberFormat = new Intl.NumberFormat("en-US");

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [hashtags, setHashtags] = useState<Hashtag[]>([]);
  const [sortBy, setSortBy] = useState<"popularity" | "engagement">("popularity");
  const [query, setQuery] = useState("");
  const [related, setRelated] = useState<RelatedHashtag[]>([]);
  const [overviewError, setOverviewError] = useState("");
  const [rankingError, setRankingError] = useState("");
  const [relatedError, setRelatedError] = useState("");
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingRankings, setLoadingRankings] = useState(true);
  const [loadingRelated, setLoadingRelated] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      setLoadingOverview(true);
      setOverviewError("");
      try {
        const response = await fetch(`${API_URL}/api/hashtag-analytics/overview`);
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || "Could not load dataset overview.");
        }
        if (active) setOverview(result);
      } catch (requestError) {
        if (active) {
          setOverviewError(
            requestError instanceof Error ? requestError.message : "Could not load dataset overview.",
          );
        }
      } finally {
        if (active) setLoadingOverview(false);
      }
    }

    void loadOverview();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadRankings() {
      setLoadingRankings(true);
      setRankingError("");
      try {
        const response = await fetch(
          `${API_URL}/api/hashtag-analytics/hashtags?sort_by=${sortBy}&limit=10`,
        );
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || "Could not load hashtag rankings.");
        }
        if (active) setHashtags(result);
      } catch (requestError) {
        if (active) {
          setRankingError(
            requestError instanceof Error ? requestError.message : "Could not load hashtag rankings.",
          );
        }
      } finally {
        if (active) setLoadingRankings(false);
      }
    }

    void loadRankings();
    return () => {
      active = false;
    };
  }, [sortBy]);

  async function findRelated(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hashtag = query.trim().replace(/^#+/, "");
    if (!hashtag) return;

    setLoadingRelated(true);
    setRelatedError("");
    setRelated([]);
    try {
      const response = await fetch(
        `${API_URL}/api/hashtag-analytics/hashtags/${encodeURIComponent(hashtag)}/related?limit=10`,
      );
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Could not find related hashtags.");
      }
      setRelated(result);
    } catch (requestError) {
      setRelatedError(
        requestError instanceof Error ? requestError.message : "Could not find related hashtags.",
      );
    } finally {
      setLoadingRelated(false);
    }
  }

  const maxValue = Math.max(
    1,
    ...hashtags.map((item) =>
      sortBy === "popularity" ? item.usage_count : item.average_engagement,
    ),
  );

  return (
    <main className="page">
      <header className="header">
        <a className="brand" href="/">ContentIQ</a>
        <nav className="site-nav" aria-label="Main navigation">
          <a className="nav-link" href="/">Recommendations</a>
          <a className="nav-link nav-link-active" href="/analytics">Analytics</a>
          <a className="nav-link" href="/duplicates">Duplicates</a>
        </nav>
      </header>

      <section className="intro">
        <p className="eyebrow">HASHTAG INTELLIGENCE</p>
        <h1>Know what your hashtags are doing.</h1>
        <p>Explore usage and historical engagement in your dataset.</p>
      </section>

      <section className="analytics-content" aria-label="Hashtag analytics">
        <div className="stats-grid">
          <article className="card stat-card">
            <p className="stat-label">Posts analyzed</p>
            <strong>{loadingOverview ? "..." : numberFormat.format(overview?.total_posts ?? 0)}</strong>
          </article>
          <article className="card stat-card">
            <p className="stat-label">Unique hashtags</p>
            <strong>{loadingOverview ? "..." : numberFormat.format(overview?.unique_hashtags ?? 0)}</strong>
          </article>
          <article className="card stat-card">
            <p className="stat-label">Hashtag uses</p>
            <strong>{loadingOverview ? "..." : numberFormat.format(overview?.total_hashtag_uses ?? 0)}</strong>
          </article>
          <article className="card stat-card">
            <p className="stat-label">Posts with hashtags</p>
            <strong>{loadingOverview ? "..." : numberFormat.format(overview?.posts_with_hashtags ?? 0)}</strong>
          </article>
        </div>
        {overviewError && <p className="error" role="alert">{overviewError}</p>}

        <section className="card analytics-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">TOP 10</p>
              <h2>Hashtag rankings</h2>
            </div>
            <label className="sort-control">
              <span>Rank by</span>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value as "popularity" | "engagement")}
              >
                <option value="popularity">Popularity</option>
                <option value="engagement">Average engagement</option>
              </select>
            </label>
          </div>
          {rankingError ? (
            <p className="error" role="alert">{rankingError}</p>
          ) : loadingRankings ? (
            <p className="hint">Loading hashtag rankings...</p>
          ) : hashtags.length ? (
            <ol className="ranking-list">
              {hashtags.map((item, index) => {
                const value = sortBy === "popularity" ? item.usage_count : item.average_engagement;
                return (
                  <li className="ranking-item" key={item.hashtag}>
                    <span className="rank-number">{String(index + 1).padStart(2, "0")}</span>
                    <div className="ranking-details">
                      <div className="ranking-label">
                        <strong>#{item.hashtag}</strong>
                        <span>
                          {sortBy === "popularity"
                            ? `${numberFormat.format(item.usage_count)} uses`
                            : `${item.average_engagement.toFixed(1)} avg. interactions`}
                        </span>
                      </div>
                      <div
                        className="ranking-track"
                        role="progressbar"
                        aria-label={`#${item.hashtag} ${sortBy}`}
                        aria-valuemin={0}
                        aria-valuemax={Math.ceil(maxValue)}
                        aria-valuenow={Math.round(value)}
                      >
                        <div className="ranking-fill" style={{ width: `${(value / maxValue) * 100}%` }} />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="hint">No hashtag ranking data is available.</p>
          )}
          {sortBy === "engagement" && (
            <p className="hint ranking-note">Average interactions = average likes + comments + shares per use.</p>
          )}
        </section>

        <section className="card analytics-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">CO-OCCURRENCE</p>
              <h2>Find related hashtags</h2>
            </div>
          </div>
          <form className="related-form" onSubmit={findRelated}>
            <label className="visually-hidden" htmlFor="related-hashtag">Hashtag to explore</label>
            <input
              id="related-hashtag"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try travel or #travel"
              required
            />
            <button type="submit" disabled={loadingRelated || !query.trim()}>
              {loadingRelated ? "Searching..." : "Find related"}
            </button>
          </form>
          {relatedError ? (
            <p className="error" role="alert">{relatedError}</p>
          ) : related.length ? (
            <ul className="related-list">
              {related.map((item) => (
                <li key={item.hashtag}>
                  <strong>#{item.hashtag}</strong>
                  <span>{numberFormat.format(item.cooccurrences)} posts together</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="hint">
              {loadingRelated ? "Looking for hashtags used together..." : "Search to see hashtags that appear alongside yours."}
            </p>
          )}
        </section>
      </section>
    </main>
  );
}
