import os
import requests
from get_mendeley_library import refresh_access_token, load_api_credentials, ensure_access_token
import get_mendeley_library
from utils import format_authors, convert_to_mendeley_json, yes_or_no
from datetime import datetime


def add_web_page_to_mendeley(access_token, group_id, url, date_accessed, citation_key, title, author=None):
    """
    Adds a web page to Mendeley with the specified metadata.
    
    Parameters:
    - access_token: Mendeley API access token.
    - url: The URL of the web page.
    - date_accessed: The date the web page was accessed (e.g., "2024-11-17").
    - citation_key: Mandatory citation key for the web page.
    - title: Title of the web page.
    - author: Optional author(s) of the web page (list of dicts with "first_name" and "last_name").
    
    Returns:
    - Response from the Mendeley API.
    """
    if not citation_key:
        raise ValueError("citation_key is required and cannot be empty.")
    
    api_url = f"https://api.mendeley.com/documents?group_id={group_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.mendeley-document.1+json"
    }

    # Prepare the data payload
    document_data = {
        "type": "web_page",
        "websites": [url],
        "accessed": date_accessed,
        "citation_key": citation_key,
        "title": title,
        "group_id": group_id
    }

    if author:
        document_data["authors"] = author

    # Make the POST request
    response = requests.post(api_url, headers=headers, json=document_data)

    # if response.status_code == 201:
    #     print("Web page successfully added to Mendeley.")
    # else:
    #     print(f"Failed to add web page. Status code: {response.status_code}")
    #     print(f"Response: {response.text}")

    return response


def main():
    """
    Main function to interact with the user and add a web page to Mendeley.
    """
    print("Add a Web Page to Mendeley")
    
    # Gather required input
    os.chdir("scripts")
    credentials = load_api_credentials()
    get_mendeley_library.CLIENT_ID = credentials.get("CLIENT_ID")
    get_mendeley_library.CLIENT_SECRET = credentials.get("CLIENT_SECRET")
    access_token = ensure_access_token()
    url = input("Enter the URL of the web page: ").strip()
    date_accessed = datetime.today().strftime('%Y-%m-%d')
    if not yes_or_no("Do you want to use today's date ("+date_accessed+")?"):
        date_accessed = input("Provide the date accessed as YYYY-MM-DD: ").strip()
    citation_key = input("Enter the citation key: ").strip()
    title = input("Enter the title of the web page: ").strip()
    
    if not citation_key:
        print("Citation key is required. Exiting...")
        return

    # Gather optional input

    authors_input = input("Enter the authors (comma-separated, optional): ").strip()

    # Parse authors if provided
    authors = []
    if authors_input:
        for author in authors_input.split(","):
            name_parts = author.strip().split()
            if len(name_parts) >= 2:
                authors.append({
                    "first_name": " ".join(name_parts[:-1]),
                    "last_name": name_parts[-1]
                })
            else:
                authors.append({
                    "first_name": "",
                    "last_name": name_parts[-1]
                })

    # Add the web page to Mendeley
    try:
        response = add_web_page_to_mendeley(
            access_token=access_token,
            group_id=get_mendeley_library.GROUP_ID,
            url=url,
            date_accessed=date_accessed,
            citation_key=citation_key,
            title=title if title else None,
            author=authors if authors else None
        )
        if response.status_code == 201:
            print("Web page successfully added to Mendeley.")
        else:
            print("Error adding web page:", response.text)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
