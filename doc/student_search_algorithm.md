# Search Algorithm Design — Student Search

Focused doc on how `student_service.search` actually works, from query
in to ranked results out. `database_layer_design.md` §4 already decided
*that* FTS5 is used; this doc covers *how* the query is processed, and
corrects one real gap in that earlier design — the default tokenizer
doesn't actually work for Thai names.

## 1. Requirements

**Confirmed search scope**: `student_id`, name, grade, and room number.
**`national_id` is explicitly excluded from search** — it's still stored
on the student record for official purposes, just never matched against
in the search box. Narrower and more deliberate than the original draft
of this doc assumed.

- Staff type **partial** information — a piece of a name they remember,
  or a class identifier like "ม.1" or "ม.1/2" — not always the exact
  start of the field.
- Fast enough for search-as-you-type on old hardware, on a roster of a
  few thousand students today, growing over time.
- The query could be an ID (all digits), a name (Thai script), or a
  grade/room identifier — the algorithm needs to tell these apart and
  route each to the right query, not force one strategy on all three.

## 2. The gap in the earlier design: Thai text has no spaces

`database_layer_design.md` §4 specified `students_fts` as a plain FTS5
virtual table with no tokenizer named, which means SQLite defaults to
**`unicode61`** — a word-boundary tokenizer. Word-boundary tokenizing
assumes words are separated by spaces or punctuation. **Thai script
doesn't put spaces between words within a name.** A name like
`นายเจษฎา งาคชสาร` would get tokenized as roughly two giant blobs (prefix
title+first name run together, then last name), not into searchable
pieces — so searching for a substring in the middle of someone's first
name (something staff will absolutely do) would fail to match at all
under `unicode61`.

**Fix: use FTS5's `trigram` tokenizer instead**, which SQLite has
supported since 3.34. It doesn't care about word boundaries at all — it
indexes every overlapping 3-character window in the text, so it works
identically well on Thai, English, or a mix, and inherently supports
substring search (searching for a chunk from the middle of a name), not
just prefix search:

```sql
CREATE VIRTUAL TABLE students_fts USING fts5(
    full_name,
    content='students', content_rowid='student_id',
    tokenize='trigram'
);
-- national_id intentionally not indexed — out of search scope (§1)
```

**Trade-offs, stated plainly**: a trigram index is larger than a
word-based one (every 3-character window is indexed, not every word),
and a query shorter than 3 characters can't use it at all (§4 covers the
fallback). Neither matters at school-roster scale — a few thousand rows
of short strings — and correctness (actually finding the student) beats
a marginal index-size difference every time. The same tokenizer change
applies to `books_fts` in `database_layer_design.md` §4, for the same
reason. This supersedes the tokenizer choice in `database_layer_design.md`
§4; that doc should be read with this correction in mind.

## 3. Query pipeline

```
raw query
   │
   ▼
normalize (trim, collapse whitespace — reuse build_db.py's clean())
   │
   ▼
looks like grade/room? ("ม.1", "ม1", "ม.1/2", "ม1/2", "ม.1.2", or "1/2")
   │                                    │
  yes                                   no
   │                                    │
   ▼                                    ▼
parse grade (+ optional room),   is the query all digits?
query current-period                    │           │
enrollments joined to                  yes          no
students (§3a)                          │           │
   │                                    ▼           ▼
   ▼                          exact/prefix match  query length < 3?
return                        on student_id            │       │
                               (§3b)                   yes     no
                                    │                    │       │
                                    ▼                    ▼       ▼
                                 return          LIKE '%query%'  FTS5 trigram
                                                 fallback on      search on
                                                  full_name        students_fts,
                                                                    order by bm25()
```

- **Grade/room detection now covers the formats people actually type**,
  not just the one canonical form: with the "ม" prefix or without it,
  with or without a dot after "ม", and either "/" or "." as the
  separator between grade and room. §3a has the exact patterns.
- **What still makes this branch unambiguous without a required
  prefix**: a bare `student_id` is a plain run of digits with nothing
  else in it. The moment a query contains a separator character (`/` or
  `.`) between two digit groups, it can't be a `student_id` (IDs don't
  contain those characters) and can't be a name (Thai text doesn't
  contain digits or those separators either) — so the separator itself
  is what disambiguates `"1/2"` as grade/room, not the "ม" prefix. The
  prefix only matters for a **grade-alone** query with no separator
  (`"ม.1"`, `"ม1"`), since a bare `"1"` with no prefix and no separator
  stays a `student_id` search (§3b) — there's nothing else to tell those
  two apart.
- **ID-style queries short-circuit** against `student_id` only —
  `national_id` is out of scope entirely (§1). **Confirmed: this is a
  suffix match, not a prefix match** — staff typically identify a
  student by the last 4 digits, or type the complete ID for an exact
  hit (§3c). If the digit query hits, return immediately without
  touching FTS.
- **Very short text queries (1–2 characters)** fall back to `LIKE`,
  since trigram needs at least 3 characters to have a token to match on.
- **Everything else** goes through the trigram FTS index on `full_name`
  only, ranked by `bm25()`.

### 3a. Grade/room parsing

Two patterns, tried in order:

1. **With a "ม" prefix** (dot after it optional), room optional:
   `"ม.1"`, `"ม1"` → grade only. `"ม.1/2"`, `"ม1/2"`, `"ม.1.2"`,
   `"ม1.2"` → grade and room, separator can be `/` or `.`.
2. **Without a prefix, separator required**: `"1/2"`, `"1.2"` → grade
   and room. No prefix means no way to tell "grade alone" from a plain
   ID, so the room part isn't optional in this form (§3, previous
   bullet).

Grade-only matches every current enrollment with that `grade_level`, any
room. Grade+room narrows to `grade_level = ... AND room = ...`. This
queries `enrollments` for the **current** year/semester only (matching
`current_enrollment` in `application_layer_design.md` §3) — searching a
past class list a student was in years ago isn't part of this, and isn't
obviously wanted (open question in §9). Join back to `students` for the
actual name/ID to display, same as any other result row.

### 3b. Why a bare room number doesn't need its own branch

A bare digit with no separator and no "ม" prefix is always treated as a
`student_id` search, never a room number — a room number alone isn't a
meaningful query on its own anyway (a "room 3" only means something
relative to a grade — "grade 1, room 3" vs "grade 2, room 3" are
different classes), so any real room lookup naturally comes with a grade
attached, which is exactly what routes it into §3a instead.

### 3c. `student_id` matching: suffix, not prefix

Confirmed: staff mostly identify a student by the **last 4 digits**, and
sometimes type the **complete ID** for a direct hit — not the first few
digits. Both are the same query underneath: a suffix match
(`student_id LIKE '%' || query`), not a prefix match. Typing the last 4
digits naturally gives a suffix match against several possible IDs (rare
to collide given the roster size); typing the full ID is just the
special case where the suffix happens to be the whole string, which
matches exactly one row automatically — no separate "exact match" branch
needed, one query handles both.

A trailing wildcard on `LIKE` can't use a normal index either way (same
reasoning as the original case for switching to FTS, `database_layer_design.md`
§4) — but `students` is a few thousand rows, and this only runs after
the grade/room and empty-query checks have already ruled themselves out,
so a full scan here is genuinely fine, not a performance risk worth
engineering around.

## 4. Ranking

Plain `bm25()` ranking is relevance-based but doesn't know that an exact
ID match should always outrank a fuzzy name match — that's already
handled by the short-circuit in §3 (ID matches never even reach the FTS
path). Within name results themselves, `bm25()`'s default behavior
(rewarding rarer, more specific token matches) is a reasonable ranking
as-is — no custom ranking function needed on top of it for a dataset
this size. Revisit only if real usage shows the ordering feels wrong
once there's real data to test against.

## 5. Search-as-you-type performance

If the Student List screen (`ui_layer_design.md` §2) re-queries on every
keystroke, that's a query per character on hardware that might be 8+
years old — worth debouncing (wait ~150–250ms after the last keystroke
before actually running the query) rather than querying on every single
keypress. This is a UI-layer detail, not the algorithm itself, but it
directly determines whether the algorithm above *feels* fast in
practice, so it's called out here rather than left implicit.

## 6. Pagination and empty/short queries

- An empty query returns nothing and prompts for input — never silently
  dumps the full roster.
- Cap results at a reasonable page size (e.g. 50) even for a broad match
  — consistent with the pagination approach already set in
  `database_layer_design.md` §9 — rather than returning hundreds of rows
  for a common short name.

## 7. Pseudocode

```python
# "ม.1", "ม1", "ม.1/2", "ม1/2", "ม.1.2", "ม1.2" — prefix, room optional
GRADE_WITH_PREFIX_RE = re.compile(r"^ม\.?(\d)(?:[./](\d+))?$")
# "1/2", "1.2" — no prefix, separator required (that's what makes it unambiguous)
GRADE_NO_PREFIX_RE = re.compile(r"^(\d)[./](\d+)$")

def parse_grade_room(query: str) -> tuple[str, int | None] | None:
    m = GRADE_WITH_PREFIX_RE.match(query) or GRADE_NO_PREFIX_RE.match(query)
    if not m:
        return None
    grade, room = m.groups()
    return grade, int(room) if room else None

def search_student(raw_query: str, limit: int = 50) -> list[StudentRow]:
    query = clean(raw_query)  # trim + collapse whitespace, build_db.py's clean()
    if not query:
        return []

    grade_room = parse_grade_room(query)
    if grade_room:
        grade, room = grade_room
        return enrollment_repo.current_period_by_grade_room(
            grade_level=f"ม.{grade}", room=room, limit=limit,
        )

    if query.isdigit():
        id_hits = student_repo.match_id_suffix(query, limit=limit)  # LIKE '%' || query
        if id_hits:
            return id_hits  # short-circuit, never touches FTS

    if len(query) < 3:
        return student_repo.like_scan_name(query, limit=limit)

    return student_repo.fts_search_name(query, limit=limit)  # bm25()-ranked
```

## 8. Testing this specifically

Beyond the general service tests already planned
(`application_layer_design.md` §10), this algorithm needs cases that
exercise each branch of §3's pipeline directly:

- Exact full-ID match, and a **suffix** match on the last 4 digits
  (confirms it's suffix-based, not prefix-based)
- A query for `national_id` returns **nothing** — confirms it's actually
  excluded, not just unindexed by accident
- Grade-only query, prefix with and without a dot (`"ม.1"`, `"ม1"`)
  return every current student in that grade, any room
- Grade+room query in each supported format (`"ม.1/2"`, `"ม1/2"`,
  `"ม.1.2"`, `"1/2"`) all return the same result — the same class,
  regardless of which format staff happened to type
- A bare digit query with no separator (e.g. `"12"`) is still treated as
  a `student_id` search, not misread as a grade — confirms §3b's
  disambiguation actually holds
- Exact full-name match
- **Substring match from the middle of a name** — this is the case that
  would have silently failed under the original `unicode61` tokenizer
  (§2), so it's the one test that would have caught this gap before it
  shipped
- A 1–2 character query, confirming the `LIKE` fallback fires
- An empty query, confirming it returns nothing rather than the full
  roster

## 9. Open questions

**Resolved this round:**
- ~~Should ID matching cover `national_id` too, and match anywhere
  within it or only from the start?~~ Moot — `national_id` is excluded
  from search entirely (§1). Resolved for `student_id`: it's a
  **suffix** match, not prefix (§3c) — staff mostly search by the last 4
  digits, or the complete ID.
- ~~Does grade/room search need to reach past enrollment periods?~~
  Confirmed current-period-only is correct — classroom/grade updates
  happen through the yearly xlsx re-import (`design_doc.md` §6a), which
  writes new `enrollments` rows for the new period rather than editing
  old ones, so "current period" always means the latest import.

**Still open:**
- No open items remain that need a business decision. One
  implementation checklist item for whoever builds this (not a decision
  point): once real roster data is loaded, run `EXPLAIN QUERY PLAN`
  against a real search query to confirm the trigram index is actually
  being used efficiently, per `database_layer_design.md` §9 — a
  five-minute verification step, not something to design around now.
