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
- String matching
- Sets
- Similarity algorithms

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
2. Compare the embedding with previously stored caption embeddings.
3. Retrieve the most semantically similar historical posts using cosine similarity.
4. Extract hashtags associated with those posts.
5. Remove hashtags already selected by the user.
6. Calculate relevance, hashtag association and engagement scores.
7. Rank the candidates and return the top recommendations using a Max Heap.

**Recommendation scoring:**

Final Score = 0.50 × Semantic Relevance + 0.30 × Hashtag Association + 0.20 × Engagement

The weights are initial values and can be tuned during testing.

**DSA concepts:**
- Graphs
- Hash Maps
- Sets
- Max Heaps
- Similarity Search
- String Processing

## 3. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Programming Language | Python | Core logic and algorithms |
| Data Processing | Pandas, NumPy | Cleaning and processing datasets |
| Backend | FastAPI | Application API and backend services |
| Frontend | Next.js, TypeScript | User interface |
| Styling | Tailwind CSS | Frontend styling |
| Visualisation | Recharts | Analytics dashboards |
| Primary Database | SQLite | Persistent structured storage |
| Text Embeddings | Sentence Transformers | Semantic caption understanding |
| Similarity Search | Cosine Similarity | Finding similar captions |
| Vector Search (Optional) | FAISS | Efficient similarity search at scale |
| Testing | Pytest | Testing algorithms and application logic |
| Deployment | Render, Vercel | Backend and frontend deployment |

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

| Data Structure / Algorithm | Application |
|---|---|
| Hash Tables | Hashtag lookup and frequency counting |
| Graphs | Hashtag relationship modelling |
| Heaps (min/max) | Retrieving top-ranked recommendations |
| Tries | Hashtag autocomplete |
| Sets | Duplicate removal and hashtag filtering |
| Sorting | Ranking hashtags |
| String Algorithms | Caption processing and comparison |
| MinHash | Approximate near-duplicate caption detection |
| Similarity Search | Finding semantically similar captions |

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

- Duplicate detection: Precision, Recall and F1-score.
- Hashtag analytics: Correctness of frequency and engagement calculations.
- Hashtag recommendations: Relevance of recommended hashtags, ranking quality and Precision@K where suitable.
- Backend: API and database testing.
- DSA: Correctness and time complexity analysis of implemented algorithms.

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

---

## 10. Installing Dependencies

The repository keeps Python and frontend dependencies in separate manifests. From the repository root, install them with:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
```

SQLite is included with Python and requires no separate package. FAISS remains optional and is not included in the initial setup.