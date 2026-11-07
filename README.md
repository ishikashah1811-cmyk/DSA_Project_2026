# ContentIQ – Instagram Content Intelligence Engine

## 1. Project Overview

ContentIQ is an Instagram content intelligence system designed to help users analyse their content, identify duplicate captions, understand hashtag performance, and discover relevant hashtags for future posts.

The system uses data structures and algorithms to process Instagram-related datasets, analyse relationships between captions and hashtags, and generate meaningful recommendations based on historical engagement.

## 2. Core Features

### Module 1: Duplicate Caption Detection

Identifies identical and near-duplicate captions within a dataset.

**How it works:**
- Preprocess and normalise captions.
- Generate representations of captions.
- Compare captions using similarity algorithms.
- Identify duplicate and near-duplicate content.

**DSA concepts:**
- Hashing
- Strings and Unicode normalization
- Sets
- Shingling, Jaccard similarity, MinHash and LSH

**Module 1 implementation:**

- `POST /api/duplicate-detection/scan` scans the configured CSV. Send an optional `similarity_threshold` from 0 to 1; the default is `0.75`.
- Exact matches are grouped by normalized caption with the custom separate-chaining hash table. Normalization uses Unicode NFKC, case folding, punctuation boundaries, and consistent whitespace. Hashtags and common emoji/symbol code points are retained.
- Near-duplicate candidates are generated from 3-token shingle sets using 64 deterministic BLAKE2b-based MinHash values and 16 LSH bands. Candidate pairs are verified with exact Jaccard similarity; LSH can miss pairs and may generate quadratic candidates in a crowded bucket.
- Blank captions are skipped. The response includes dataset rows scanned, analyzed captions, exact groups and extra duplicate posts, verified near pairs, unique captions, post IDs, and CSV row numbers.
- The frontend is available at `/duplicates`, uses the existing `NEXT_PUBLIC_API_URL` setting, and shows backend results with threshold control and exact/near/unique views.
- Module 1 reads the CSV directly and does not use SQLite or an embedding model. See [`docs/module1-explanation.md`](docs/module1-explanation.md) for the pipeline, complexity analysis, limitations, and viva questions.

### Module 2: Hashtag Intelligence and Analytics

Analyses hashtag usage and historical engagement to identify useful and popular hashtags.

**How it works:**
- Extract hashtags from posts.
- Calculate hashtag frequency.
- Analyse likes, comments and shares.
- Identify hashtags frequently used together.
- Rank hashtags based on popularity and engagement.

**DSA concepts:**
- Hash Maps
- Graphs
- Sorting
- Priority Queues / Heaps

**Module 2 implementation:**

- Hashtag analytics are exposed separately from Module 3 under `/api/hashtag-analytics`.
- The frontend analytics dashboard is available at `/analytics`; it displays dataset totals, lets users rank hashtags by popularity or average engagement, and searches co-occurring hashtags.
- `GET /api/hashtag-analytics/overview` returns post counts, unique hashtag counts, total hashtag uses, and total likes, comments, and shares.
- `GET /api/hashtag-analytics/hashtags?sort_by=popularity&limit=20` ranks hashtags by usage. Use `sort_by=engagement` to rank by average likes, comments, and shares per post containing each hashtag.
- `GET /api/hashtag-analytics/hashtags/{hashtag}/related?limit=10` returns hashtags that co-occur with the requested hashtag and their co-occurrence counts.
- Module 2 has its own analytics service, hashtag index, and graph instance. Its hashtag aggregates use the custom separate-chaining hash table in `algorithms/hash_tables/hash_table.py`; its related-tag output and deterministic tie ordering use the stable merge sort in `algorithms/sorting/merge_sort.py`.
- Popularity and engagement rankings use the existing max heap, and co-occurrences use the existing weighted hashtag graph. These shared structures retain their existing behavior for Module 3.
- It reads the same CSV columns used by Module 3. The dataset path uses `CONTENTIQ_DATASET_PATH` or defaults to `Dataset/instagram_posts_synthetic.csv`.
- Tests cover hash collisions and resizing, stable sorting, analytics output, and a Module 3 recommendation request using the shared graph.

### Module 3: Context-Aware Hashtag Recommendation

Recommends relevant hashtags based on the meaning of a user's caption and the hashtags they have already selected.

For example, if a user enters:

Caption: "Missing those school days! Nothing beats the memories we made with our friends."

Existing hashtags:
- #school
- #memories

ContentIQ identifies semantically similar historical captions, retrieves their associated hashtags, analyses their performance, and recommends complementary hashtags such as:

- #oldDays
- #friends
- #schoolLife
- #nostalgia
- #throwback

**How it works:**

1. Convert the user's caption into a numerical embedding using a Sentence Transformer model.
2. Compare the caption embedding with embeddings created from the dataset captions.
3. Retrieve the most semantically similar dataset posts using cosine similarity.
4. Collect hashtags from those posts and add graph neighbors of hashtags the user selected.
5. Remove hashtags already selected by the user.
6. Score each remaining candidate by caption relevance, graph association, and engagement.
7. Rank the candidates and return the top recommendations using a Max Heap.

**Recommendation scoring:**

Final Score = 0.50 * Semantic Relevance + 0.30 * Hashtag Association + 0.20 * Engagement

The weights are initial values and can be tuned during testing.

**Module 3 implementation:**

- The backend endpoint is `POST /api/hashtag-recommendations`. Send a caption, optional selected hashtags, and optional `top_k`/`neighbors` values. It returns ranked hashtags with each score component.
- The service reads a CSV once, creates normalized caption embeddings with `sentence-transformers/all-MiniLM-L6-v2`, and keeps its caption vectors, hashtag-to-post index, and graph in memory. Embeddings and the graph are built on the first recommendation request; the model may need to download the first time it is used.
- The CSV uses the dataset's columns: `Post_Caption`, `Post_Hashtags`, `No_of_likes`, `No_of_comments`, and `No_of_shares`. Hashtags should use `#` prefixes, as in the supplied dataset.
- **Graph:** each hashtag is a node. Two tags share a weighted, undirected edge whose weight counts the posts where they occur together. Caption matches supply initial candidates; direct neighbors of selected tags expand that set. Graph association is the average Jaccard overlap between a candidate and each selected tag, which reduces the advantage of generic tags.
- **Scoring:** for each candidate, semantic relevance and engagement are averaged over its five most similar dataset posts. Engagement is `log1p(likes + comments + shares)` normalized against the maximum in the dataset. Graph association is the average Jaccard overlap described above; it is zero when no hashtags were selected. The final score is `0.50 * relevance + 0.30 * association + 0.20 * engagement`. Selected hashtags are excluded from results.
- **Current scope/deviation:** the repository dataset `Dataset/instagram_posts_synthetic.csv` has 20,000 synthetic rows and is tracked in this checkout. The original 10,000 rows were preserved, and 10,000 additional synthetic rows were appended, including 1,000 posts tagged `#winter`. Services use this path by default and report an error if it is missing; set `CONTENTIQ_DATASET_PATH` to use another CSV. They read the CSV directly and build indexes in memory; posts and embeddings are not persisted in SQLite. The frontend includes Module 1 duplicate detection, the Module 2 analytics dashboard, and the Module 3 recommendation screen.

To run the API from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

On macOS or Linux, from the repository root:

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

The service uses `Dataset/instagram_posts_synthetic.csv` by default. To use a different file, set `CONTENTIQ_DATASET_PATH`. The model can be changed with `CONTENTIQ_EMBEDDING_MODEL`.

**Windows quick start:** double-click `run_project.bat` from File Explorer or run it from Command Prompt. It opens separate backend and frontend terminal windows, then opens the app in your default browser. Keep both server windows open while using the app. Python dependencies, Node.js/npm, frontend packages, and the dataset must already be installed/present.

To start the frontend manually in a second terminal:

```powershell
Set-Location frontend
npm run dev
```

On macOS or Linux, run the same frontend command from the `frontend` directory:

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:3000` to use the frontend. The Next.js development server allows both `127.0.0.1` and `localhost` for its development resources. The UI uses `http://127.0.0.1:8000` for the backend by default. Set `NEXT_PUBLIC_API_URL` before starting Next.js to use a different backend URL. The backend permits the local Next.js origins by default; set `CONTENTIQ_CORS_ORIGINS` to a comma-separated list of allowed origins when deploying.

Example request:

```json
{
  "caption": "Missing those school days and the memories with friends",
  "selected_hashtags": ["#school", "#memories"],
  "top_k": 5,
  "neighbors": 30
}
```

API docs are available at `/docs` while the server is running.

Module 1 request example:

```bash
curl -X POST http://127.0.0.1:8000/api/duplicate-detection/scan \
  -H 'Content-Type: application/json' \
  -d '{"similarity_threshold": 0.75}'
```

The JSON response includes `total_posts_scanned`, `captions_analyzed`, `exact_duplicates`, `near_duplicates`, `unique_captions`, and their corresponding counts. Exact groups contain their normalized caption and associated post rows. Near pairs contain the two original captions, their post rows, and exact Jaccard `similarity`.

**DSA concepts:**
- Graphs
- Hash Maps
- Sets
- Max Heaps
- Similarity Search
- String Processing

## 3. Technology Stack

| Component | Technology | Purpose / current status |
|---|---|---|
| Programming Language | Python | Core backend logic and algorithms; used |
| Data Processing | Python CSV, NumPy | CSV loading and embedding math; used by Module 3 |
| Backend | FastAPI | Recommendation API; used |
| Frontend | Next.js, TypeScript | Analytics dashboard and recommendation page; used |
| Styling | CSS | Analytics dashboard and recommendation page styling; Tailwind is installed but not used |
| Visualisation | CSS bars and metric cards | Hashtag ranking dashboard; used |
| Primary Database | SQLite | Planned persistent storage; Module 3 currently reads CSV and keeps its index in memory |
| Text Embeddings | Sentence Transformers | Caption embeddings; used |
| Similarity Search | Cosine Similarity with NumPy | Caption and candidate-post matching; used |
| Vector Search (Optional) | FAISS | Optional future optimization; not used |
| Testing | Pytest | Recommendation service, graph, and API tests; used |
| Deployment | Render, Vercel | Possible future deployment targets; not configured |

**Database decision:**

SQLite will remain the primary database for storing posts, captions, hashtags, engagement metrics and relationships.

We will initially implement vector similarity search using NumPy or scikit-learn. FAISS can be introduced later if the dataset grows.

A separate vector database is not required for the initial implementation.

## 4. Database Design

The database will contain the following main entities:

### USERS
- user_id
- username
- followers_count

### POSTS
- post_id
- user_id
- caption
- timestamp
- likes
- comments
- shares

### HASHTAGS
- hashtag_id
- hashtag
- usage_count

### POST_HASHTAGS
- post_id
- hashtag_id

This creates a many-to-many relationship between posts and hashtags.

Caption embeddings will initially be stored separately as numerical vector data, associated with their respective post IDs.

Additional tables can be introduced as the application develops.

## 5. Overall System Workflow

### Phase A: Data Collection and Processing

1. Obtain Instagram export data and relevant Kaggle datasets.
2. Extract the required information.
3. Clean and normalise captions and hashtags.
4. Process engagement metrics.
5. Import structured data into SQLite.

### Phase B: Data Structure Construction

1. Build Hash Maps for hashtag frequencies and associations.
2. Construct a Graph representing hashtag co-occurrence.
3. Generate caption embeddings.
4. Prepare data structures for similarity search.
5. Calculate engagement statistics.

### Phase C: Feature Execution

**Duplicate Caption Detection**
- Accept a caption.
- Compare it with existing captions.
- Identify duplicates and similar captions.

**Hashtag Intelligence**
- Analyse hashtag usage.
- Calculate popularity and engagement.
- Display ranked hashtags and analytics.

**Context-Aware Recommendations**
- Accept a caption and optional existing hashtags.
- Generate caption embeddings.
- Retrieve similar historical posts.
- Extract associated hashtags.
- Rank candidates using relevance and engagement.
- Return the top recommendations.

### Phase D: Frontend and Deployment

1. Develop the user interface using Next.js.
2. Connect the frontend to FastAPI.
3. Display analytics and recommendations.
4. Test the application.
5. Deploy the frontend and backend.

## 6. DSA Implementation

An important objective of ContentIQ is to implement fundamental data structures and algorithms in practical applications rather than relying entirely on external libraries.

| Data Structure / Algorithm | Application | Status |
|---|---|---|
| Separate-chaining hash table; hash maps and lists | Module 2 hashtag aggregates; Module 3 hashtag-to-post lookup | Used by Modules 2 and 3 |
| Separate-chaining hash table | Module 1 exact normalized-caption grouping | Implemented |
| Graph | Weighted hashtag co-occurrence and selected-tag associations | Used by Modules 2 and 3 |
| Max heap | Ranking hashtags and retrieving top-ranked recommendations | Used by Modules 2 and 3 |
| Merge sort | Deterministic ordering of analytics and related hashtags | Used by Module 2 |
| Sets | Module 1 shingles and Jaccard similarity; Module 3 tag filtering | Used by Modules 1 and 3 |
| Sorting | Selecting nearest captions and candidate posts | Used by Module 3 |
| String processing | Module 1 caption normalization and shingling; Module 3 hashtag extraction | Used by Modules 1 and 3 |
| Tries | Hashtag autocomplete | Planned; not implemented |
| MinHash and LSH | Candidate generation for near-duplicate caption detection | Implemented in Module 1 |
| Similarity search | Finding semantically similar captions | Used by Module 3 |

## 7. Suggested Project Structure

```text
ContentIQ/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── database/
│   │   ├── models/
│   │   ├── algorithms/
│   │   │   ├── hash_tables/
│   │   │   ├── graphs/
│   │   │   ├── heaps/
│   │   │   ├── tries/
│   │   │   ├── minhash/
│   │   │   ├── sets/
│   │   │   ├── sorting/
│   │   │   ├── string_algorithms/
│   │   │   └── similarity_search/
│   │   ├── modules/
│   │   │   ├── duplicate_detection/
│   │   │   ├── hashtag_analytics/
│   │   │   └── hashtag_recommendation/
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── components/
│   └── public/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── embeddings/
│
├── README.md
└── .gitignore
```

## 8. Testing and Evaluation

Each module will be tested independently.

- Duplicate detection: unit and API tests cover normalization, shingles, Jaccard, deterministic MinHash, LSH candidates, classification, thresholds, and dataset errors. A labeled benchmark is not included, so precision, recall, and F1 have not been measured on real labeled data.
- Hashtag analytics: Correctness of frequency and engagement calculations.
- Hashtag recommendations: Unit tests cover graph construction and scoring, selected-tag filtering, dataset validation, and API responses. Precision@K and other offline ranking metrics are not yet evaluated.
- Backend: API and database testing.
- DSA: Correctness and time complexity analysis of implemented algorithms.

Run the backend suite from the repository root after installing `backend/requirements.txt`:

```bash
python -m pytest backend/tests -q
```

Build-check the frontend from its directory:

```bash
npm run build
```

## 9. Development Roadmap

1. Inspect and understand available datasets.
2. Design the SQLite database.
3. Implement data extraction and preprocessing.
4. Develop duplicate caption detection.
5. Develop hashtag analytics.
6. Build caption embedding and similarity search.
7. Implement hashtag association and recommendation algorithms.
8. Integrate the backend and frontend.
9. Test, evaluate and deploy ContentIQ.

Modules 1, 2, and 3 have backend APIs and frontend routes. SQLite persistence remains planned work; the current modules read CSV data and keep their indexes in memory.

---

## 10. Installing Dependencies

The repository keeps Python and frontend dependencies in separate manifests. From the repository root, install them with:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
```

On macOS or Linux, from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm install
```

SQLite is included with Python and requires no separate package. The current hashtag recommendation module reads the CSV directly and does not use SQLite. FAISS remains optional and is not included in the initial setup.

## 11. Module 3: What We Built and How It Works

The table below describes the current implementation rather than the future modules in the project plan.

| Part | What we implemented and how it works |
|---|---|
| Dataset | Reads `Dataset/instagram_posts_synthetic.csv`, which currently contains 20,000 synthetic posts (the original 10,000 plus 10,000 added rows). It uses `Post_Caption` for text, `Post_Hashtags` for tags, and the three `No_of_*` columns for engagement. The file is tracked in this repository; `CONTENTIQ_DATASET_PATH` can point to another CSV with the same columns. |
| Caption embeddings | Uses the Sentence Transformers model `sentence-transformers/all-MiniLM-L6-v2` to encode every dataset caption. The normalized vectors are held in memory. The model and index initialize on the first recommendation request, so that request may take longer and may require a model download. |
| Caption similarity | Encodes the submitted caption and compares it with dataset vectors using cosine similarity. The `neighbors` request value (default 30) controls how many closest posts supply the initial candidate hashtags. |
| Hashtag graph | Builds a sparse, undirected graph while reading posts. A hashtag is a node; an edge connects two tags that appear in the same post, and its weight is the number of such posts. The current 20,000-row dataset produces 139 nodes and 1,750 unique edges. |
| Candidate hashtags | Starts with tags from the closest caption posts, then adds direct graph neighbors for every user-selected tag. Finally, it removes tags the user already selected. This lets selected-tag relationships introduce candidates even when they are not in the closest caption posts. |
| Graph association | For a candidate and selected tag, computes Jaccard similarity: co-occurrence count divided by the number of posts containing either tag. It averages this value over selected tags. With no selected tags, this score is zero. |
| Engagement | Adds likes, comments, and shares for each post. Applies `log1p` and scales against the largest post engagement in the dataset, reducing the effect of unusually large counts. |
| Candidate score | For each candidate, finds its five most semantically similar dataset posts and averages their cosine relevance and normalized engagement. Combines those averages with graph association using `0.50 * relevance + 0.30 * association + 0.20 * engagement`. |
| Ranking | Pushes scored candidates into the project’s max heap and pops the highest scores up to `top_k` (default 10, maximum 50). |
| API and UI | `POST /api/hashtag-recommendations` accepts a caption, selected hashtags, and optional `top_k` and `neighbors` values. The Next.js page sends this request, displays recommendations, and lets the user add a suggested hashtag to their selected list. |
| Persistence and evaluation | The current module keeps dataset posts, vectors, and graph in memory; it does not store them in SQLite. Tests use a fixed encoder to check graph edges, graph-based candidate expansion, ranking behavior, selected-tag filtering, and API output. They do not measure real-model Precision@K or guarantee recommendation quality for every caption. |
