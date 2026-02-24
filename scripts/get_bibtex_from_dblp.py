import argparse
import requests

global BASE_DBLP_URL
global DBLP_MIRROR_URL
global DBLP_URL
global USE_MIRROR 

BASE_DBLP_URL="dblp.org"
DBLP_MIRROR_URL="dblp.uni-trier.de"
DBLP_URL=""
USE_MIRROR = False

def get_response_with_fallback(url, params=None, timeout=10):
    """
    Fetch a URL and, if it is on the base DBLP host and fails with a server
    error or network error, retry against the mirror.

    Returns:
    - (response, used_mirror)
    """
    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code >= 500 and BASE_DBLP_URL in url:
            raise requests.exceptions.HTTPError(
                f"{response.status_code} server error from {BASE_DBLP_URL}",
                response=response
            )
        response.raise_for_status()
        return response, False
    except requests.exceptions.RequestException as e:
        if BASE_DBLP_URL in url:
            mirror_url = url.replace(BASE_DBLP_URL, DBLP_MIRROR_URL)
            print(f"Encountered error from {BASE_DBLP_URL}: {e}")
            print(f"Retrying with mirror {DBLP_MIRROR_URL} ...")
            response = requests.get(mirror_url, params=params, timeout=timeout)
            response.raise_for_status()
            return response, True
        raise

def search_dblp(title_keywords, author_keywords, venue_keywords):
    """
    Searches DBLP for papers matching title and author keywords.
    
    Parameters:
    - title_keywords: Keywords to search in the title.
    - author_keywords: Keywords to search for in the author names.
    
    Returns:
    - A list of search results (each result is a dictionary with metadata).
    """
    # url = "https://dblp.org/search/publ/api"
    # url = "https://dblp.uni-trier.de/search/publ/api"
    global DBLP_URL
    global USE_MIRROR
    url = f"https://{DBLP_URL}/search/publ/api"
    query = f"{title_keywords} {author_keywords} {venue_keywords}".strip()
    params = {
        "q": query,
        "format": "json",
        "h": 20  # Number of results to fetch
    }

    try:
        # Perform the GET request
        response, used_mirror = get_response_with_fallback(url, params=params)
        if used_mirror:
            USE_MIRROR = True
            DBLP_URL = DBLP_MIRROR_URL

        # Parse the JSON response
        data = response.json()
        results = data.get("result", {}).get("hits", {}).get("hit", [])

        # Process results into a cleaner format
        processed_results = []
        for result in results:
            info = result.get("info", {})
            print(info.get("authors"))
            processed_results.append({
                "title": info.get("title"),
                "authors": [info.get("authors", {}).get("author", {}).get("text")] if isinstance(info.get("authors", {}).get("author"), dict) else [author.get("text") for author in info.get("authors", {}).get("author", [])],
                "year": info.get("year"),
                "venue": info.get("venue"),
                "url": info.get("url"),
                "bibtex_url": info.get("url") + ".bib" if info.get("url") else None
            })

        return processed_results
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while querying DBLP: {e}")
        return []
    except ValueError as e:
        print(f"Failed to parse DBLP response as JSON: {e}")
        return []

def download_bibtex(bibtex_url):
    """
    Downloads the BibTeX entry from the provided URL.
    
    Parameters:
    - bibtex_url: The URL to download the BibTeX entry from.
    
    Returns:
    - The BibTeX entry as a string.
    """
    global USE_MIRROR
    try:
        response, used_mirror = get_response_with_fallback(bibtex_url)
        if used_mirror:
            USE_MIRROR = True
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading BibTeX: {e}")
        return None

def main():
    """
    Main function to search DBLP and optionally download a BibTeX entry.
    """
    print("DBLP Search and BibTeX Downloader")

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Search DBLP and download BibTeX entries.")
    parser.add_argument("--output", type=str, help="Output filename to save the BibTeX entry.")
    args = parser.parse_args()

    # Gather input
    title_keywords = input("Enter title keywords: ").strip()
    author_keywords = input("Enter author keywords (optional): ").strip()
    venue_keywords = input("Enter venue keywords (optional): ").strip()
    
    global BASE_DBLP_URL
    global DBLP_URL
    global DBLP_MIRROR_URL
    global USE_MIRROR

    # Test if BASE DBLP URL is working
    test_url = f"https://{BASE_DBLP_URL}"
    try:
        response = requests.get(test_url, timeout=2)
        response.raise_for_status()
        print(f"Successfully connected to {BASE_DBLP_URL}")
        DBLP_URL = BASE_DBLP_URL
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to {BASE_DBLP_URL}: {e}")
        print(f"Reverting to mirror URL {DBLP_MIRROR_URL}")
        test_url = f"https://{DBLP_MIRROR_URL}"
        try:
            response = requests.get(test_url, timeout=2)
            response.raise_for_status()
            print(f"Successfully connected to {DBLP_MIRROR_URL}")
            DBLP_URL = DBLP_MIRROR_URL
            USE_MIRROR = True
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to {DBLP_MIRROR_URL}: {e}")
            exit(1)



    # Search DBLP
    print("\nSearching DBLP...")
    results = search_dblp(title_keywords, author_keywords, venue_keywords)

    if not results:
        print("No results found.")
        return

    # Display results
    print("\nSearch Results:")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Title: {result['title']}")
        print(f"Authors: {', '.join(result['authors'])}")
        print(f"Year: {result['year']}")
        print(f"Venue: {result['venue']}")
        print(f"URL: {result['url']}")

    # Ask the user to select a result
    try:
        choice = int(input("\nEnter the number of the result to download BibTeX (0 to exit): "))
        if choice == 0:
            print("Exiting without downloading.")
            return
        selected_result = results[choice - 1]
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        return

    # Download the BibTeX entry
    bibtex_url = selected_result.get("bibtex_url")
    if bibtex_url and USE_MIRROR:
        bibtex_url = bibtex_url.replace(BASE_DBLP_URL, DBLP_MIRROR_URL)
    if not bibtex_url:
        print("No BibTeX URL available for the selected result.")
        return

    print("\nDownloading BibTeX...")
    bibtex_entry = download_bibtex(bibtex_url)

    if bibtex_entry:
        if args.output:
            with open(args.output, "w") as f:
                f.write(bibtex_entry)
            print(f"BibTeX entry saved to {args.output}")
        else:
            print("\nBibTeX Entry:")
        print(bibtex_entry)
    else:
        print("Failed to download the BibTeX entry.")

if __name__ == "__main__":
    main()
