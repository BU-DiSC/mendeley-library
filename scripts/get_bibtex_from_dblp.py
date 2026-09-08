import argparse
import re
import requests

CROSSREF_API = "https://api.crossref.org/works"
DOI_BASE = "https://doi.org"
POLITE_MAILTO = "manos.athanassoulis@gmail.com"

HEADERS = {
    "User-Agent": f"mendeley-library-tool/1.0 (mailto:{POLITE_MAILTO})"
}


def search_crossref(title_keywords, author_keywords, venue_keywords):
    params = {
        "rows": 20,
        "select": "title,author,published,DOI,type,container-title",
    }
    if title_keywords:
        params["query.title"] = title_keywords
    if author_keywords:
        params["query.author"] = author_keywords
    if venue_keywords:
        params["query.container-title"] = venue_keywords
    if not title_keywords and not author_keywords and not venue_keywords:
        print("Please provide at least one search term.")
        return []

    try:
        response = requests.get(CROSSREF_API, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while querying CrossRef: {e}")
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
            "title": (item.get("title") or ["(no title)"])[0],
            "authors": authors,
            "year": year,
            "venue": (item.get("container-title") or [""])[0],
            "doi": item.get("DOI"),
        })
    return results


def fetch_bibtex(doi):
    response = requests.get(
        f"{DOI_BASE}/{doi}",
        headers={**HEADERS, "Accept": "application/x-bibtex"},
        allow_redirects=True,
        timeout=15,
    )
    response.raise_for_status()
    bibtex = response.text
    # CrossRef emits bare-word month values (e.g. month=June) that bibtexparser
    # cannot parse as a string — wrap them in braces.
    bibtex = re.sub(r"(\bmonth\s*=\s*)([A-Za-z]+)(\s*[,}])", r"\1{\2}\3", bibtex)
    return bibtex


def main():
    print("CrossRef Search and BibTeX Downloader")

    parser = argparse.ArgumentParser(
        description="Search CrossRef and download BibTeX entries."
    )
    parser.add_argument("--output", type=str, help="Output filename for the BibTeX entry.")
    args = parser.parse_args()

    title_keywords = input("Enter title keywords: ").strip()
    author_keywords = input("Enter author keywords (optional): ").strip()
    venue_keywords = input("Enter venue keywords (optional): ").strip()

    print("\nSearching CrossRef...")
    results = search_crossref(title_keywords, author_keywords, venue_keywords)

    if not results:
        print("No results found.")
        return

    print("\nSearch Results:")
    for i, r in enumerate(results, 1):
        author_str = ", ".join(r["authors"][:3])
        if len(r["authors"]) > 3:
            author_str += " et al."
        print(f"\nResult {i}:")
        print(f"  Title:   {r['title']}")
        print(f"  Authors: {author_str}")
        print(f"  Year:    {r['year']}")
        print(f"  Venue:   {r['venue']}")
        print(f"  DOI:     {r['doi']}")

    try:
        choice = int(input("\nEnter the number of the result to download BibTeX (0 to exit): "))
        if choice == 0:
            print("Exiting without downloading.")
            return
        selected = results[choice - 1]
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        return

    if not selected["doi"]:
        print("No DOI available for the selected result — cannot download BibTeX.")
        return

    print("\nDownloading BibTeX...")
    try:
        bibtex = fetch_bibtex(selected["doi"])
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading BibTeX: {e}")
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
