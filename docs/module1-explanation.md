# Module 1: Duplicate Caption Detection

## Problem and input

Module 1 scans the configured CSV dataset and groups its non-empty `Post_Caption` values. It uses `Post_id` when present and otherwise reports the CSV data row number as the post identifier. Blank captions are counted and skipped. The service follows the project convention: `CONTENTIQ_DATASET_PATH` overrides the default `Dataset/instagram_posts_synthetic.csv` path.

The implementation runs in memory and does not require SQLite or an embedding model. It produces exact duplicate groups, near-duplicate caption pairs, and captions that have no detected duplicate. A near-duplicate pair is a pair of different normalized captions whose exact Jaccard similarity meets the requested threshold. Exact-normalized copies are grouped before near-duplicate comparisons, so the same pair is not reported in both categories.

## Pipeline

1. Read caption rows from the CSV and preserve each caption, post ID, and row number.
2. Normalize every caption with Unicode NFKC and case folding. Split on punctuation and extra whitespace, while keeping hashtags as tokens and retaining common emoji and symbol code points. Thus `Great-day!` and `great day` normalize the same, while `#summer` and `summer` remain different.
3. Insert each non-empty normalized caption into the custom separate-chaining hash table. The value is the list of dataset records with that caption. Any value with multiple records is an exact duplicate group.
4. For each distinct normalized caption, tokenize the words, hashtags, and retained symbols. Make sets of consecutive word shingles, using up to three tokens per shingle. If a caption has only one or two tokens, its full token span is used as the shingle width.
5. Create a deterministic MinHash signature for each shingle set. Each coordinate is the minimum BLAKE2b digest of every shingle with that coordinate's seed.
6. Split signatures into bands. Two captions become a candidate if at least one band matches.
7. Calculate exact Jaccard similarity for every candidate. Keep a pair when the score is at least the threshold (default `0.75`).
8. Captions with one source post that are in neither an exact group nor a detected near pair are listed as unique. Exact duplicate groups are not counted as unique.

## Data structures and algorithms

### Hash table and exact matches

The existing `HashTable` is a custom separate-chaining map. A normalized caption is a key and its associated dataset rows are the value. This avoids comparing each caption to all earlier captions. With a good hash distribution, inserting and looking up a caption takes average O(1), so grouping N captions takes average O(N) table operations in addition to normalization. If all keys collide into one bucket, an operation can take O(N), and building the index can take O(N²) in the worst case. The table stores up to one key per distinct normalized caption, plus the post records in its values.

### Strings and normalization

NFKC maps compatible Unicode forms to a consistent representation, and `casefold()` makes case-insensitive comparisons. Punctuation becomes a token boundary by being omitted during tokenization. Hashtags stay prefixed and intact as one token. Symbols in the supported emoji ranges are retained, although multi-codepoint emoji sequences can be represented as multiple symbol tokens. Normalization over a caption of L characters takes O(L) time and O(L) output space.

### Shingles and Jaccard similarity

A shingle is a short consecutive token sequence. For `a sunny beach day`, 3-word shingles are `{a sunny beach, sunny beach day}`. Shingles preserve local word order and context: the sets for `a sunny beach day` and `a sunny beach trip` share the first shingle.

For two shingle sets A and B, the service calculates `|A ∩ B| / |A ∪ B|`. Two empty sets are assigned similarity 1 by the reusable helper, but empty captions are skipped by the dataset service. Set intersection and union take expected O(|A| + |B|) time and O(|A| + |B|) temporary space.

### MinHash

MinHash estimates Jaccard similarity by comparing signatures. For each seeded hash function, it records the smallest hash value among the caption's shingles. The proportion of equal signature coordinates estimates the set Jaccard similarity. This implementation uses deterministic seeded BLAKE2b digests instead of Python's process-randomized `hash()`.

With S shingles and H hash functions, signature construction takes O(H·S) time and stores O(H) integers per caption. More hash functions generally reduce estimate noise, while increasing runtime and storage linearly. Module 1 uses 64 hash functions. MinHash estimates are used for candidate signatures only; final classification uses exact Jaccard similarity.

### LSH banding and candidate generation

Locality-sensitive hashing (LSH) divides a signature into bands. A pair sharing a complete band is considered a candidate. For a pair with similarity s, b bands, and r rows per band, the common approximation for candidate probability is `1 - (1 - s^r)^b`. With 64 signature cells and 16 bands, the default has four rows per band. LSH reduces the comparisons for typical data, but it can miss similar pairs and can still generate many candidates when buckets are crowded.

For C distinct captions, signature banding takes O(C·H) work. Candidate generation also emits each pair within every bucket; its cost depends on bucket sizes and reaches O(C²) when many captions share a band. Pair keys are deduplicated before verification. The exact Jaccard check costs O(|A| + |B|) expected time for the two shingle sets. Across all candidates, verification cost is the sum of those per-pair costs.

### Why not compare every pair?

Brute force checks C(C - 1)/2 caption pairs, requiring O(C²) comparisons before accounting for shingle sizes. The current pipeline hashes each caption once, then verifies only pairs admitted by LSH. This is generally much smaller for varied data, but the worst case remains quadratic because a large LSH bucket creates many candidates. The code and documentation do not treat LSH as a worst-case complexity guarantee.

## Worked example

Take `A sunny beach walk` and `A sunny beach stroll`. After normalization the tokens are `[a, sunny, beach, walk]` and `[a, sunny, beach, stroll]`. With three-token shingles, the sets are `{a sunny beach, sunny beach walk}` and `{a sunny beach, sunny beach stroll}`. Their intersection contains one shingle and their union contains three, so Jaccard similarity is `1/3` (about 0.333). They are not a near-duplicate at the default 0.75 threshold, even if LSH happens to select them as a candidate.

## API

`POST /api/duplicate-detection/scan`

Request:

```json
{ "similarity_threshold": 0.75 }
```

The threshold is inclusive and must be between 0 and 1. The response contains the number of CSV rows scanned, non-empty captions analyzed, blank captions skipped, exact groups, extra exact matching posts, near pairs, unique captions, and the detailed result lists. Post IDs and CSV row numbers are included with each result. If `Post_id` is absent, data row numbering is used. Missing files or a CSV without `Post_Caption` return HTTP 503; invalid thresholds return HTTP 422.

## Complexity summary

Let N be CSV rows, C distinct non-empty normalized captions, L total caption characters, S the maximum shingles per caption, H the number of MinHash functions, and P the number of LSH candidate pairs.

| Stage | Time | Additional space |
|---|---:|---:|
| Read and normalize | O(L) | O(L) records/text |
| Exact hash-table grouping | O(N) average; O(N²) worst case for collisions | O(C + N) |
| Shingling | O(total tokens) expected set work | O(total unique shingles) |
| MinHash signatures | O(H · total shingles) | O(C · H) signatures |
| LSH buckets and candidates | O(C · H + emitted bucket pairs), worst O(C²) | O(C · H + P) |
| Exact Jaccard verification | O(sum of shingle sizes over P pairs) expected | O(max shingle set size) temporary per comparison |

The current service returns all result groups in one response. For much larger datasets, result pagination, an index cache, or a persistent store could reduce repeated scan and transfer costs.

## Limitations and evaluation

- LSH is probabilistic candidate selection. A real near-duplicate can be missed if it shares no band with its counterpart.
- Jaccard treats all shingles equally and does not understand meaning, synonyms, or word order beyond local shingles.
- Short captions produce very small shingle sets, so one token can change similarity sharply.
- The default 3-token shingle size, 64 hashes, 16 bands, and 0.75 threshold are starting parameters, not values tuned against a labeled benchmark.
- The CSV is read and indexed on every scan; this feature does not use SQLite or persist results.
- The repository has no labeled duplicate-caption benchmark. Synthetic unit fixtures verify mechanics, but they cannot support a meaningful real-data precision, recall, or F1 claim. Those metrics require labeled duplicate and non-duplicate pairs.

## Viva and application questions

1. **What happens when captions differ only by punctuation?** Punctuation is omitted during tokenization, so `Great-day!` and `great day` normalize to the same caption and become an exact duplicate group.
2. **Why use a hash table instead of nested loops for exact matches?** Each normalized caption is looked up by key, giving average constant-time lookup and average linear grouping work, rather than comparing every pair.
3. **What is the worst case for the custom hash table?** If many keys collide into one chain, each lookup can scan the chain and total grouping can approach O(N²).
4. **What is a shingle?** It is a set element containing a short consecutive token sequence, such as `sunny beach walk`.
5. **Why use sets of shingles?** Sets make duplicate n-grams count once and let Jaccard compare shared content independent of repeated occurrences.
6. **What does Jaccard measure?** The fraction of distinct shingles shared by two captions out of the distinct shingles appearing in either caption.
7. **What happens if the threshold increases?** Fewer candidate pairs pass final verification, usually improving precision and reducing recall.
8. **Can MinHash be inaccurate?** Yes. Its estimate is based on a finite number of signatures; more hash functions generally reduce estimation variance.
9. **Why use deterministic hashing?** Reproducible signatures make tests and LSH buckets stable across runs; Python's built-in hash can change between processes.
10. **Why can LSH miss a real pair?** Similar signatures do not guarantee a matching full band; the pair may not collide in any band.
11. **Can LSH still do quadratic work?** Yes. If many captions land in the same bucket, candidate pair generation can approach O(C²).
12. **How are very short captions handled?** Shingle width shrinks to the number of available tokens. A one-token caption gets a one-token shingle; blank captions are skipped.
13. **What if both shingle sets are empty?** The reusable Jaccard helper returns 1 for two empty sets, but the service removes blank normalized captions before comparisons.
14. **What does the system do with emojis and hashtags?** Hashtags remain attached to their word token, and common emoji/symbol code points are retained; punctuation is dropped as a separator.
15. **What changes for 100,000 captions?** The code would need profiling, likely caching or persistent indexes, paginated results, and potentially tuning LSH bands/hash count; worst-case bucket sizes still need monitoring.
16. **Why verify LSH candidates with exact Jaccard?** A shared band only means “worth checking.” Exact set overlap enforces the user's threshold and prevents relying on an approximate score for classification.
17. **Can Jaccard understand synonyms?** No. `happy` and `joyful` are different tokens, so semantic similarity is outside this DSA-based method.
18. **How should precision, recall, and F1 be evaluated?** Compare predicted pairs with a human-labeled pair set, then calculate TP/(TP+FP), TP/(TP+FN), and their harmonic mean. The current synthetic fixtures are not a labeled benchmark.
