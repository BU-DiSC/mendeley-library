import argparse
import re
import time
import xml.etree.ElementTree as ET
import requests
from fuzzywuzzy import fuzz

DBLP_SPARQL  = "https://sparql.dblp.org/sparql"
CROSSREF_API = "https://api.crossref.org/works"
DATACITE_API = "https://api.datacite.org/dois"
ARXIV_API    = "https://export.arxiv.org/api/query"
DOI_BASE     = "https://doi.org"
POLITE_MAILTO = "manos.athanassoulis@gmail.com"

HEADERS = {
    "User-Agent": f"mendeley-library-tool/1.0 (mailto:{POLITE_MAILTO})"
}

# Venues whose DOIs are registered with DataCite rather than CrossRef, keyed by
# the acronym that appears in their DOIs (10.5441/002/edbt.2018.64,
# 10.4230/LIPIcs.ICDT.2015.76). OpenProceedings records carry no container
# title, so the acronym in the DOI is the only reliable source of the venue.
DATACITE_VENUES = {
    "edbt":  "Proceedings of the International Conference on Extending Database Technology (EDBT)",
    "icdt":  "Proceedings of the International Conference on Database Theory (ICDT)",
    "dolap": "Proceedings of the International Workshop on Design, Optimization, Languages and Analytical Processing of Big Data (DOLAP)",
}

# Shown in the search progress, result headers and per-result tags.
SOURCE_LABELS = {
    "dblp":     "dblp (through SPARQL)",
    "crossref": "CrossRef",
    "datacite": "DataCite",
    "arxiv":    "arXiv",
}

# Lowercase surname particles kept with the family name ("van Dam, Wim").
NAME_PARTICLES = {"van", "von", "de", "der", "den", "del", "della", "di", "da", "du", "la", "le", "dos", "das"}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _dblp_last_first(name):
    """'Ting Yao 0001' -> 'Yao, Ting'; 'Wim van Dam' -> 'van Dam, Wim'.

    dblp appends a 4-digit number to disambiguate homonymous authors.
    """
    parts = re.sub(r"\s+\d{4}$", "", name).split()
    if len(parts) < 2:
        return " ".join(parts)
    i = len(parts) - 1
    while i > 1 and parts[i - 1].lower() in NAME_PARTICLES:
        i -= 1
    return f"{' '.join(parts[i:])}, {' '.join(parts[:i])}"


def search_dblp(title_keywords, author_keywords):
    """Query dblp's SPARQL endpoint; returns raw results tagged source='dblp'.

    dblp.org's search API and BibTeX pages sit behind the Anubis bot check,
    but sparql.dblp.org (QLever) does not. Titles are matched through QLever's
    word index (fast); every word must appear. Hyphenated and punctuated words
    are split because the index stores them as separate words. An author-only
    search falls back to a substring match on author names, which is slower.
    """
    title_words  = re.findall(r"[^\W_]+", title_keywords.lower())
    author_words = re.findall(r"[^\W_]+", author_keywords.lower())
    if title_words:
        match = "?text ql:contains-entity ?t . " + " ".join(
            f'?text ql:contains-word "{w}" .' for w in title_words
        ) + " ?p dblp:title ?t ."
    elif author_words:
        match = "?p dblp:hasSignature ?ms . ?ms dblp:signatureDblpName ?mn . FILTER(" + " && ".join(
            f'CONTAINS(LCASE(?mn), "{w}")' for w in author_words
        ) + ")"
    else:
        return []

    query = f"""
PREFIX dblp: <https://dblp.org/rdf/schema#>
PREFIX ql: <http://qlever.cs.uni-freiburg.de/builtin-functions/>
SELECT ?p ?title ?type ?year ?doi ?pages ?ee ?venue ?volume ?number ?booktitle ?ord ?name WHERE {{
  {{ SELECT DISTINCT ?p WHERE {{ {match} }} LIMIT 50 }}
  ?p dblp:title ?title ; dblp:bibtexType ?type .
  OPTIONAL {{ ?p dblp:yearOfPublication ?year }}
  OPTIONAL {{ ?p dblp:doi ?doi }}
  OPTIONAL {{ ?p dblp:pagination ?pages }}
  OPTIONAL {{ ?p dblp:primaryDocumentPage ?ee }}
  OPTIONAL {{ ?p dblp:publishedIn ?venue }}
  OPTIONAL {{ ?p dblp:publishedInJournalVolume ?volume }}
  OPTIONAL {{ ?p dblp:publishedInJournalVolumeIssue ?number }}
  OPTIONAL {{ ?p dblp:publishedAsPartOf ?proc . ?proc dblp:title ?booktitle }}
  OPTIONAL {{ ?p dblp:hasSignature ?s . ?s dblp:signatureOrdinal ?ord ; dblp:signatureDblpName ?name }}
}}"""

    # sparql.dblp.org answers bursts of queries with HTTP 429; wait and retry.
    for attempt in range(3):
        try:
            response = requests.get(
                DBLP_SPARQL,
                params={"query": query},
                headers={**HEADERS, "Accept": "application/sparql-results+json"},
                timeout=60,
            )
        except requests.exceptions.RequestException as e:
            print(f"dblp SPARQL search error: {e.__class__.__name__}")
            return []
        if response.status_code != 429:
            break
        retry_after = response.headers.get("Retry-After", "")
        wait = int(retry_after) if retry_after.isdigit() else 5 * (attempt + 1)
        print(f"dblp SPARQL rate limit hit; retrying in {wait}s...")
        time.sleep(wait)
    else:
        print("dblp SPARQL rate limit persists after retries.")
        return []

    try:
        response.raise_for_status()
        rows = response.json()["results"]["bindings"]
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        # The request URL embeds the whole query, so print only the status.
        print(f"dblp SPARQL search error: HTTP {response.status_code}")
        return []

    # One row per (publication, author, ...) combination: fold them back up.
    pubs = {}
    for row in rows:
        v   = {k: b["value"] for k, b in row.items()}
        pub = pubs.setdefault(v["p"], {"fields": {}, "authors": {}})
        for k, val in v.items():
            pub["fields"].setdefault(k, val)
        if "ord" in v:
            pub["authors"][int(v["ord"])] = _dblp_last_first(v["name"])

    results = []
    for pub in pubs.values():
        f     = pub["fields"]
        kind  = f["type"].rsplit("#", 1)[-1].lower()     # Inproceedings -> inproceedings
        doi   = f.get("doi", "")
        doi   = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi) or None
        # dblp ends titles with a period; keep ? and ! which are part of the title.
        title = re.sub(r"\.$", "", f["title"])
        venue = f.get("booktitle") if kind in ("inproceedings", "incollection") else None
        results.append({
            "title":    title,
            "authors":  [pub["authors"][i] for i in sorted(pub["authors"])],
            "year":     f.get("year", ""),
            "venue":    venue or f.get("venue", ""),
            "doi":      doi,
            "arxiv_id": None,
            "source":   "dblp",
            "kind":     kind,
            "pages":    f.get("pages", ""),
            "volume":   f.get("volume", ""),
            "number":   f.get("number", ""),
            "url":      f.get("ee") or (f"{DOI_BASE}/{doi}" if doi else ""),
        })
    return results


def search_crossref(title_keywords, author_keywords):
    """Query CrossRef; returns raw results tagged source='crossref'.

    Uses query.bibliographic rather than query.title: ACM often splits titles
    at the colon (title='Monkey', subtitle='Optimal Navigable Key-Value Store'),
    and query.title then fails to rank such papers in the top 50 at all.
    """
    params = {
        "rows": 50,
        "select": "title,subtitle,author,published,DOI,type,container-title",
    }
    if title_keywords:
        params["query.bibliographic"] = title_keywords
    if author_keywords:
        params["query.author"] = author_keywords

    try:
        response = requests.get(CROSSREF_API, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"CrossRef search error: {e}")
        return []

    results = []
    for item in response.json().get("message", {}).get("items", []):
        pub_date = (item.get("published") or item.get("published-print") or {})
        year = (pub_date.get("date-parts") or [[None]])[0][0]
        authors = [
            f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
            for a in item.get("author", [])
        ]
        title = (item.get("title") or ["(no title)"])[0]
        if item.get("subtitle"):
            title = f"{title}: {item['subtitle'][0]}"
        results.append({
            "title":    title,
            "authors":  authors,
            "year":     str(year) if year else "",
            "venue":    (item.get("container-title") or [""])[0],
            "doi":      item.get("DOI"),
            "arxiv_id": None,
            "source":   "crossref",
        })
    return results


def _datacite_venue(doi, attrs):
    """Best-effort venue name for a DataCite record (see DATACITE_VENUES)."""
    match = re.search(r"\b(" + "|".join(DATACITE_VENUES) + r")\.\d{4}\b", doi.lower())
    if match:
        return DATACITE_VENUES[match.group(1)]
    return (attrs.get("container") or {}).get("title") or attrs.get("publisher") or ""


def search_datacite(title_keywords, author_keywords):
    """Query DataCite; returns raw results tagged source='datacite'.

    DataCite registers DOIs that CrossRef never sees, notably OpenProceedings
    (EDBT/ICDT/DOLAP, prefix 10.5441) and Dagstuhl LIPIcs (prefix 10.4230).
    Tokens are AND-ed because DataCite also indexes millions of datasets,
    which would otherwise flood the results.
    """
    def tokens(text):
        # Elasticsearch syntax: '/' starts a regex, '<>=' are range operators.
        return [t for t in (re.sub(r"[/<>=]", "", t) for t in _arxiv_tokens(text)) if t]

    parts = []
    if title_keywords and tokens(title_keywords):
        parts.append("titles.title:(" + " AND ".join(tokens(title_keywords)) + ")")
    if author_keywords and tokens(author_keywords):
        parts.append("creators.name:(" + " AND ".join(tokens(author_keywords)) + ")")
    if not parts:
        return []

    try:
        response = requests.get(
            DATACITE_API,
            params={"query": " AND ".join(parts), "page[size]": 50},
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"DataCite search error: {e}")
        return []

    results = []
    for item in response.json().get("data", []):
        attrs     = item.get("attributes", {})
        doi       = attrs.get("doi") or item.get("id")
        container = attrs.get("container") or {}
        authors = [
            f"{c['familyName']}, {c.get('givenName', '')}".strip(", ")
            if c.get("familyName") else c.get("name", "")
            for c in attrs.get("creators", [])
        ]
        pages = "-".join(p for p in (container.get("firstPage"), container.get("lastPage")) if p)
        results.append({
            "title":    (attrs.get("titles") or [{"title": "(no title)"}])[0]["title"],
            "authors":  authors,
            "year":     str(attrs.get("publicationYear") or ""),
            "venue":    _datacite_venue(doi, attrs),
            "doi":      doi,
            "arxiv_id": None,
            "source":   "datacite",
            "is_article": (attrs.get("types") or {}).get("resourceTypeGeneral") == "JournalArticle",
            "pages":    pages,
        })
    return results


def _arxiv_tokens(text):
    """Split text into Lucene-safe tokens for arXiv field queries.

    Hyphens are treated as word separators ("LSM-based" → ["LSM", "based"]).
    True Lucene special characters are stripped; apostrophes are intentionally
    kept — arXiv preserves them in its index, so "Don't" must be queried as
    "Don't" (not "Dont") to match. The most critical character to strip is '!'
    which is the Lucene NOT operator, so "Delete!" without stripping would be
    silently parsed as NOT Delete.
    """
    text = text.replace("-", " ")
    text = re.sub(r"[+&|!(){}\[\]^\"~*?:\\]", "", text)
    return [t for t in text.split() if t]


def search_arxiv(title_keywords, author_keywords):
    """Query arXiv; returns raw results tagged source='arxiv'.

    Venue is always set to 'CoRR' for preprints so the client-side venue
    filter works consistently (e.g. venue_keywords='CoRR' matches arXiv only).
    If the paper also has a DOI (published version), that DOI is stored so
    fetch_bibtex can retrieve the proper publisher BibTeX instead.
    """
    if not title_keywords and not author_keywords:
        return []

    # Build Lucene query with sanitized tokens.
    parts = []
    if title_keywords:
        parts.extend([f"ti:{t}" for t in _arxiv_tokens(title_keywords)])
    if author_keywords:
        parts.extend([f"au:{t}" for t in _arxiv_tokens(author_keywords)])
    query = " AND ".join(parts)

    # Retry up to 3 times on rate-exceeded responses (arXiv enforces ~1 req/s).
    # The rate-limit check must happen before raise_for_status() because arXiv
    # returns HTTP 429 for rate limiting, which raise_for_status() would turn
    # into an immediate exception with no chance to retry.
    for attempt in range(3):
        try:
            response = requests.get(
                ARXIV_API,
                params={"search_query": query, "max_results": 25, "sortBy": "relevance"},
                headers=HEADERS,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            print(f"arXiv search error: {e}")
            return []

        if response.status_code == 429 or "Rate exceeded" in response.text:
            wait = 5 * (attempt + 1)
            print(f"arXiv rate limit hit; retrying in {wait}s...")
            time.sleep(wait)
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"arXiv search error: {e}")
            return []
        break
    else:
        print("arXiv rate limit persists after retries.")
        return []

    ns = {
        "atom":  "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(response.text)
    results = []
    for entry in root.findall("atom:entry", ns):
        raw_id   = entry.find("atom:id", ns).text.split("abs/")[-1]
        arxiv_id = raw_id.split("v")[0]          # strip version suffix
        title    = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        year     = entry.find("atom:published", ns).text[:4]

        authors = []
        for a in entry.findall("atom:author", ns):
            name  = a.find("atom:name", ns).text.strip()
            parts_name = name.split()
            if len(parts_name) >= 2:
                authors.append(f"{parts_name[-1]}, {' '.join(parts_name[:-1])}")
            else:
                authors.append(name)

        doi_el = entry.find("arxiv:doi", ns)
        doi    = doi_el.text.strip() if doi_el is not None else None

        results.append({
            "title":    title,
            "authors":  authors,
            "year":     year,
            "venue":    "CoRR",
            "doi":      doi,
            "arxiv_id": arxiv_id,
            "source":   "arxiv",
        })
    return results


# ---------------------------------------------------------------------------
# Filtering and ranking
# ---------------------------------------------------------------------------

def apply_filters(results, title_keywords, author_keywords, venue_keywords):
    """AND-filter across all three fields.

    - title:   every keyword must appear (case-insensitive substring) in the title
    - authors: every keyword must appear in at least one author name
    - venue:   every keyword must appear in the venue string
    Returns an empty list if nothing survives, rather than padding the output
    with loosely related papers.
    Note: venue uses the full CrossRef container-title for CrossRef results,
    the DATACITE_VENUES name for DataCite results, and 'CoRR' for arXiv
    results; use words from the full name for CrossRef venues
    (e.g. 'Management of Data' for SIGMOD, 'VLDB Endowment' for PVLDB).
    """
    filtered = results
    if title_keywords:
        kws = title_keywords.lower().split()
        filtered = [r for r in filtered if all(kw in r["title"].lower() for kw in kws)]
    if author_keywords:
        kws = author_keywords.lower().split()
        filtered = [r for r in filtered if all(
            any(kw in a.lower() for a in r["authors"]) for kw in kws
        )]
    if venue_keywords:
        kws = venue_keywords.lower().split()
        filtered = [r for r in filtered if all(kw in r["venue"].lower() for kw in kws)]
    return filtered


def rank_and_cap(results, title_keywords, n=10):
    """Sort by fuzzy title similarity when title keywords were provided; cap at n.

    Similarity is skipped (score=None) when no title is given so the result
    header stays clean and the CrossRef/arXiv relevance order is preserved.
    """
    if title_keywords:
        for r in results:
            r["score"] = fuzz.token_set_ratio(title_keywords.lower(), r["title"].lower())
        results.sort(key=lambda r: r["score"], reverse=True)
    else:
        for r in results:
            r["score"] = None
    return results[:n]


# ---------------------------------------------------------------------------
# BibTeX retrieval / generation
# ---------------------------------------------------------------------------

def make_arxiv_bibtex(result):
    """Generate a @article BibTeX entry in CoRR format for an arXiv preprint.

    Uses a placeholder key; prepare_upload_bibtex.py will replace it with the
    generated key (lastname + year + title-words) before upload.
    """
    arxiv_id   = result["arxiv_id"]
    authors_str = " and ".join(result["authors"])
    url        = f"https://doi.org/10.48550/arXiv.{arxiv_id}"
    return (
        f"@article{{dummy_key,\n"
        f"  title = {{{{{result['title']}}}}},\n"
        f"  author = {{{authors_str}}},\n"
        f"  year = {{{result['year']}}},\n"
        f"  url = {{{url}}},\n"
        f"  journal = {{CoRR}},\n"
        f"  volume = {{abs/{arxiv_id}}}\n"
        f"}}\n"
    )


def make_datacite_bibtex(result):
    """Generate an @inproceedings (or @article) BibTeX entry for a DataCite result.

    doi.org content negotiation returns @misc with publisher=OpenProceedings.org
    for these DOIs, so the entry is built locally with a proper booktitle that
    the dblp2disc recipes in prepare_upload_bibtex.py can match.
    """
    entry_type  = "article" if result["is_article"] else "inproceedings"
    venue_field = "journal" if result["is_article"] else "booktitle"
    fields = [
        f"  title = {{{{{result['title']}}}}}",
        f"  author = {{{' and '.join(result['authors'])}}}",
        f"  year = {{{result['year']}}}",
        f"  doi = {{{result['doi']}}}",
        f"  url = {{{DOI_BASE}/{result['doi']}}}",
        f"  {venue_field} = {{{result['venue']}}}",
    ]
    if result["pages"]:
        fields.append(f"  pages = {{{result['pages']}}}")
    return f"@{entry_type}{{dummy_key,\n" + ",\n".join(fields) + "\n}\n"


def make_dblp_bibtex(result):
    """Generate a BibTeX entry from a dblp SPARQL result.

    Mirrors what dblp's own BibTeX export contained (dblp booktitle/journal
    names, which the dblp2disc recipes are written for), so it also works
    for papers without a DOI such as USENIX ones.
    """
    kind = result["kind"]
    fields = [
        f"  title = {{{{{result['title']}}}}}",
        f"  author = {{{' and '.join(result['authors'])}}}",
        f"  year = {{{result['year']}}}",
    ]
    if result["doi"]:
        fields.append(f"  doi = {{{result['doi']}}}")
    if result["url"]:
        fields.append(f"  url = {{{result['url']}}}")
    if kind == "article":
        fields.append(f"  journal = {{{result['venue']}}}")
        if result["volume"]:
            fields.append(f"  volume = {{{result['volume']}}}")
        if result["number"]:
            fields.append(f"  number = {{{result['number']}}}")
    elif result["venue"]:
        fields.append(f"  booktitle = {{{result['venue']}}}")
    if result["pages"]:
        fields.append(f"  pages = {{{result['pages']}}}")
    return f"@{kind}{{dummy_key,\n" + ",\n".join(fields) + "\n}\n"


def fetch_bibtex(result):
    """Return the BibTeX string for a result.

    - dblp result: generate the entry locally from its dblp metadata.
    - DataCite result: generate the entry locally from its metadata.
    - Any other result with a DOI: content negotiation via doi.org (CrossRef or publisher).
    - arXiv result without a DOI: generate CoRR @article locally.
    """
    if result["source"] == "dblp":
        return make_dblp_bibtex(result)

    if result["source"] == "datacite":
        return make_datacite_bibtex(result)

    if result["doi"]:
        response = requests.get(
            f"{DOI_BASE}/{result['doi']}",
            headers={**HEADERS, "Accept": "application/x-bibtex"},
            allow_redirects=True,
            timeout=15,
        )
        response.raise_for_status()
        bibtex = response.text
        # CrossRef emits bare-word month values (e.g. month=June) that
        # bibtexparser cannot parse — wrap them in braces.
        bibtex = re.sub(r"(\bmonth\s*=\s*)([A-Za-z]+)(\s*[,}])", r"\1{\2}\3", bibtex)
        return bibtex

    if result["source"] == "arxiv" and result["arxiv_id"]:
        return make_arxiv_bibtex(result)

    raise ValueError("Result has neither a DOI nor an arXiv ID — cannot produce BibTeX.")


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------

def _print_results(results):
    for i, r in enumerate(results, 1):
        author_str = ", ".join(r["authors"][:3])
        if len(r["authors"]) > 3:
            author_str += " et al."
        score_tag  = f" [similarity: {r['score']}%]" if r["score"] is not None else ""
        source_tag = f"[{SOURCE_LABELS[r['source']]}]"
        print(f"\nResult {i}{score_tag} {source_tag}:")
        print(f"  Title:   {r['title']}")
        print(f"  Authors: {author_str}")
        print(f"  Year:    {r['year']}")
        print(f"  Venue:   {r['venue']}")
        print(f"  DOI:     {r['doi']}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("dblp (through SPARQL) + CrossRef + DataCite + arXiv Search and BibTeX Downloader")

    parser = argparse.ArgumentParser(
        description="Search dblp (through SPARQL), then CrossRef, then DataCite (arXiv as "
                    "fallback), and download BibTeX entries."
    )
    parser.add_argument("--output", type=str, help="Output filename for the BibTeX entry.")
    args = parser.parse_args()

    title_keywords  = input("Enter title keywords: ").strip()
    author_keywords = input("Enter author keywords (optional): ").strip()
    venue_keywords  = input("Enter venue keywords (optional): ").strip()

    if not title_keywords and not author_keywords and not venue_keywords:
        print("Please provide at least one search term.")
        return

    # --- Phase 1: dblp, falling back to CrossRef, then DataCite ---
    doi_results = []
    for source, search in (("dblp", search_dblp), ("crossref", search_crossref),
                           ("datacite", search_datacite)):
        name = SOURCE_LABELS[source]
        print(f"\nSearching {name}...")
        doi_results = rank_and_cap(
            apply_filters(search(title_keywords, author_keywords),
                          title_keywords, author_keywords, venue_keywords),
            title_keywords,
        )
        if doi_results:
            print(f"\n{name} Results:")
            _print_results(doi_results)
            break
        print(f"Not found in {name}.")

    if doi_results:
        try:
            choice = int(input(
                "\nEnter number to download BibTeX, 0 to cancel, -1 to search arXiv: "
            ))
        except ValueError:
            print("Invalid selection. Exiting.")
            return
    else:
        print("Falling back to arXiv.")
        choice = -1

    if choice == 0:
        print("Exiting without downloading.")
        return

    # --- Phase 2: arXiv (fallback, or on demand) ---
    if choice == -1:
        print("\nSearching arXiv...")
        ax_raw     = search_arxiv(title_keywords, author_keywords)
        ax_results = rank_and_cap(
            apply_filters(ax_raw, title_keywords, author_keywords, venue_keywords),
            title_keywords,
        )

        if not ax_results:
            print("No arXiv results found. Exiting.")
            return

        print("\narXiv Results:")
        _print_results(ax_results)

        try:
            choice = int(input("\nEnter number to download BibTeX (0 to cancel): "))
        except ValueError:
            print("Invalid selection. Exiting.")
            return

        if choice == 0:
            print("Exiting without downloading.")
            return

        try:
            selected = ax_results[choice - 1]
        except IndexError:
            print("Invalid selection. Exiting.")
            return
    else:
        try:
            selected = doi_results[choice - 1]
        except IndexError:
            print("Invalid selection. Exiting.")
            return

    # --- Fetch / generate BibTeX ---
    print("\nGenerating BibTeX...")
    try:
        bibtex = fetch_bibtex(selected)
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"An error occurred: {e}")
        return

    if args.output:
        with open(args.output, "w") as f:
            f.write(bibtex)
        print(f"BibTeX entry saved to {args.output}")
    else:
        print("\nBibTeX Entry:")
        print(bibtex)


if __name__ == "__main__":
    main()
