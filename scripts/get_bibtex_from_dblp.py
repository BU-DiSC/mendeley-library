import argparse
import re
import time
import xml.etree.ElementTree as ET
import requests
from fuzzywuzzy import fuzz

CROSSREF_API = "https://api.crossref.org/works"
ARXIV_API    = "https://export.arxiv.org/api/query"
DOI_BASE     = "https://doi.org"
POLITE_MAILTO = "manos.athanassoulis@gmail.com"

HEADERS = {
    "User-Agent": f"mendeley-library-tool/1.0 (mailto:{POLITE_MAILTO})"
}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_crossref(title_keywords, author_keywords):
    """Query CrossRef; returns raw results tagged source='crossref'."""
    params = {
        "rows": 50,
        "select": "title,author,published,DOI,type,container-title",
    }
    if title_keywords:
        params["query.title"] = title_keywords
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
        results.append({
            "title":    (item.get("title") or ["(no title)"])[0],
            "authors":  authors,
            "year":     str(year) if year else "",
            "venue":    (item.get("container-title") or [""])[0],
            "doi":      item.get("DOI"),
            "arxiv_id": None,
            "source":   "crossref",
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
    Falls back to the unfiltered list if nothing survives.
    Note: venue uses the full CrossRef container-title for CrossRef results and
    'CoRR' for arXiv results; use words from the full name for CrossRef venues
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

    if not filtered and results:
        print("(No results matched all criteria; showing broader matches.)")
        return results
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


def fetch_bibtex(result):
    """Return the BibTeX string for a result.

    - Any result with a DOI: content negotiation via doi.org (CrossRef or publisher).
    - arXiv result without a DOI: generate CoRR @article locally.
    """
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
        source_tag = f"[{r['source'].upper()}]"
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
    print("CrossRef + arXiv Search and BibTeX Downloader")

    parser = argparse.ArgumentParser(
        description="Search CrossRef and arXiv, then download BibTeX entries."
    )
    parser.add_argument("--output", type=str, help="Output filename for the BibTeX entry.")
    args = parser.parse_args()

    title_keywords  = input("Enter title keywords: ").strip()
    author_keywords = input("Enter author keywords (optional): ").strip()
    venue_keywords  = input("Enter venue keywords (optional): ").strip()

    if not title_keywords and not author_keywords and not venue_keywords:
        print("Please provide at least one search term.")
        return

    # --- Phase 1: CrossRef ---
    print("\nSearching CrossRef...")
    cr_raw   = search_crossref(title_keywords, author_keywords)
    cr_results = rank_and_cap(
        apply_filters(cr_raw, title_keywords, author_keywords, venue_keywords),
        title_keywords,
    )

    if cr_results:
        print("\nCrossRef Results:")
        _print_results(cr_results)
    else:
        print("No CrossRef results found.")

    try:
        choice = int(input(
            "\nEnter number to download BibTeX, 0 to cancel, -1 to search arXiv: "
        ))
    except ValueError:
        print("Invalid selection. Exiting.")
        return

    if choice == 0:
        print("Exiting without downloading.")
        return

    # --- Phase 2: arXiv (on demand) ---
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
            selected = cr_results[choice - 1]
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
