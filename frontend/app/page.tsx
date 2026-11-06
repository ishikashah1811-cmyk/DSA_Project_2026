"use client";

import { useState } from "react";
import type { FormEvent } from "react";

type Recommendation = {
  hashtag: string;
  score: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function parseHashtags(value: string) {
  return value
    .split(/[,\s]+/)
    .map((tag) => tag.replace(/^#+/, "").trim())
    .filter(Boolean);
}

export default function Home() {
  const [caption, setCaption] = useState("");
  const [selectedHashtags, setSelectedHashtags] = useState("");
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function getRecommendations(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setRecommendations([]);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/hashtag-recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caption,
          selected_hashtags: parseHashtags(selectedHashtags),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Could not get recommendations.");
      }

      setRecommendations(result.recommendations);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not connect to the recommendation service.",
      );
    } finally {
      setLoading(false);
    }
  }

  function addHashtag(hashtag: string) {
    const currentTags = parseHashtags(selectedHashtags);
    if (!currentTags.some((tag) => tag.toLowerCase() === hashtag.toLowerCase())) {
      setSelectedHashtags([...currentTags, hashtag].join(", "));
    }
  }

  return (
    <main className="page">
      <header className="header">
        <a className="brand" href="/">ContentIQ</a>
        <span>HASHTAG RECOMMENDATIONS</span>
      </header>

      <section className="intro">
        <p className="eyebrow">A BETTER FIT FOR YOUR NEXT POST</p>
        <h1>Find hashtags that fit your caption.</h1>
        <p>Share what your post is about. We’ll find related tags from similar posts.</p>
      </section>

      <section className="workspace">
        <form className="card form" onSubmit={getRecommendations}>
          <label htmlFor="caption">Caption</label>
          <textarea
            id="caption"
            value={caption}
            onChange={(event) => setCaption(event.target.value)}
            placeholder="Write or paste your caption..."
            maxLength={5000}
            required
            rows={6}
          />

          <label htmlFor="hashtags">Hashtags you already selected</label>
          <input
            id="hashtags"
            value={selectedHashtags}
            onChange={(event) => setSelectedHashtags(event.target.value)}
            placeholder="#travel, #weekend"
          />
          <p className="hint">Separate hashtags with commas or spaces.</p>

          <button type="submit" disabled={loading || !caption.trim()}>
            {loading ? "Finding hashtags..." : "Get recommendations"}
          </button>
        </form>

        <section className="card results" aria-live="polite">
          <h2>Recommended hashtags</h2>
          {error ? (
            <p className="error" role="alert">{error}</p>
          ) : recommendations.length ? (
            <div className="tags">
              {recommendations.map((item) => (
                <button
                  className="tag"
                  key={item.hashtag}
                  onClick={() => addHashtag(item.hashtag)}
                  title={`Score: ${item.score.toFixed(2)}`}
                  type="button"
                >
                  + #{item.hashtag}
                </button>
              ))}
            </div>
          ) : (
            <p className="hint">Your recommendations will appear here.</p>
          )}
        </section>
      </section>
    </main>
  );
}
