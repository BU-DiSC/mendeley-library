import os
import requests
import json

# Mendeley API Credentials
CLIENT_ID = ''
CLIENT_SECRET = ''
REDIRECT_URI = "http://localhost"
TOKEN_FILE = "tokens.json"
GROUP_ID="c40c69e8-f198-3ed3-9843-25c8b605eed5"

# Load Mendeley API credentials from a JSON file
def load_api_credentials():
    credentials_file = "credentials.json"
    if os.path.exists(credentials_file):
        with open(credentials_file, "r") as f:
            return json.load(f)
    else:
        raise Exception(f"Credentials file '{credentials_file}' not found.")

# Save tokens to a file
def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    print("Tokens saved to file.")

# Load tokens from a file
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

# Refresh the access token
def refresh_access_token(refresh_token):
    response = requests.post(
        "https://api.mendeley.com/oauth/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    if response.status_code != 200:
        raise Exception(f"Error refreshing token: {response.text}")
    tokens = response.json()
    save_tokens(tokens)
    return tokens["access_token"]

# Ensure that refresh token is updated
def ensure_refresh_token(refresh_token):
    """
    Refreshes the Mendeley access token using the refresh token.
    """
    url = "https://api.mendeley.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token"), token_data.get("expires_in")
    else:
        raise ValueError(f"Failed to refresh token: {response.status_code}, {response.text}")

# Perform the initial OAuth flow
def get_access_token():
    auth_url = (
        f"https://api.mendeley.com/oauth/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=all"
    )
    print("Open the following URL in your browser and authorize the app:")
    print(auth_url)
    authorization_code = input("Enter the authorization code from the URL: ")

    response = requests.post(
        "https://api.mendeley.com/oauth/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    if response.status_code != 200:
        raise Exception(f"Error getting access token: {response.text}")
    tokens = response.json()
    save_tokens(tokens)
    return tokens["access_token"]

# Ensure a valid access token
def ensure_access_token():
    tokens = load_tokens()
    if tokens:
        print("Using saved tokens.")
        try:
            return refresh_access_token(tokens["refresh_token"])
        except Exception as e:
            print(f"Failed to refresh token: {e}")
    print("Performing new authentication.")
    return get_access_token()

# Fetch all groups
def fetch_groups(access_token):
    response = requests.get(
        "https://api.mendeley.com/groups",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        raise Exception(f"Error fetching groups: {response.text}")
    return response.json()

# Fetch documents with extended metadata
def fetch_documents(access_token, group_id):
    response = requests.get(
        f"https://api.mendeley.com/documents?group_id={group_id}&view=bib",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        raise Exception(f"Error fetching documents: {response.text}")
    return response.json()



def get_document_count(access_token, group_id):
    """
    Fetch the total number of documents in a Mendeley group using the `Mendeley-Count` header.
    """
    url = f"https://api.mendeley.com/documents?group_id={group_id}&limit=1"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        raise Exception(f"Error fetching document count: {response.text}")

    # Extract the total count from the `Mendeley-Count` header
    total_count = response.headers.get("Mendeley-Count")
    if total_count is None:
        raise Exception("Mendeley-Count header not found in response.")
    return int(total_count)

def fetch_all_documents(access_token, group_id):
    """
    Fetch all documents from a Mendeley group by following pagination links
    as described in the API guidelines.
    """
    base_url = f"https://api.mendeley.com/documents?group_id={group_id}&view=bib&limit=500"
    documents = []
    document_ids = set()  # Track unique document IDs to avoid duplicates
    url = base_url

    while url:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise Exception(f"Error fetching documents: {response.text}")

        # Parse the current batch of documents
        data = response.json()

        # Add only new documents to the list
        new_documents = [doc for doc in data if doc.get("id") not in document_ids]
        for doc in new_documents:
            document_ids.add(doc.get("id"))
            documents.append(doc)

        print(f"Retrieved {len(new_documents)} new documents (total: {len(documents)}).")

        # Parse the Link header to navigate to the next page
        link_header = response.headers.get("Link")
        if link_header:
            links = parse_link_header(link_header)
            url = links.get("next") or links.get("last")  # Prefer 'next', fallback to 'last'
        else:
            url = None  # No more pages to fetch

    print(f"Completed fetching all documents. Total unique documents: {len(documents)}.")
    return documents


def parse_link_header(link_header):
    """
    Parse the Link header to extract URLs for rel values.
    """
    links = {}
    parts = link_header.split(",")
    for part in parts:
        section = part.split(";")
        if len(section) != 2:
            continue
        url = section[0].strip()[1:-1]  # Remove angle brackets
        rel = section[1].strip().split("=")[1].strip('"')  # Extract rel value
        links[rel] = url
    return links

def to_bibtex(entry):
    """
    Converts a document entry to a BibTeX formatted string based on its type.
    """
    # Determine BibTeX type
    bibtex_type_map = {
        "conference_proceedings": "inproceedings",
        "journal": "article",
        "book": "book",
        "book_section": "incollection",
        "thesis": "phdthesis",
        "report": "techreport",
        "web_page": "misc",
        "patent": "misc",
        "generic": "misc"
    }
    entry_type = entry.get("type", "misc")
    bibtex_type = bibtex_type_map.get(entry_type, "misc")

    # Use citation key if available, fallback to ID
    citation_key = entry.get("citation_key", entry.get("id", "unknown"))

    fields = []

    # Common fields
    if "title" in entry:
        fields.append(f"  title = {{{{{entry['title']}}}}}")

    if "authors" in entry and entry["authors"]:
        authors = " and ".join(
            f"{author.get('last_name', '')}, {author.get('first_name', '')}".strip(", ")
            for author in entry["authors"]
        )
        fields.append(f"  author = {{{authors}}}")

    if "year" in entry:
        fields.append(f"  year = {{{entry['year']}}}")

    if "doi" in entry:
        fields.append(f"  doi = {{{entry['doi']}}}")

    if entry_type != "web_page":
        if "websites" in entry and entry["websites"]:
            fields.append(f"  url = {{{entry['websites'][0]}}}")
    elif entry_type == "web_page":
        if "websites" in entry and entry["websites"]:
            fields.append(f"  howpublished = {{\\url{{{entry['websites'][0]}}}}}")
        if "accessed" in entry:
            fields.append(f"  note = {{(Accessed: {entry['accessed']})}}")

    # Type-specific fields
    if bibtex_type == "article":
        if "source" in entry:
            fields.append(f"  journal = {{{entry['source']}}}")
        if "volume" in entry:
            fields.append(f"  volume = {{{entry['volume']}}}")
        if "issue" in entry:
            fields.append(f"  number = {{{entry['issue']}}}")
        if "pages" in entry:
            fields.append(f"  pages = {{{entry['pages']}}}")
    elif bibtex_type == "inproceedings":
        if "source" in entry:
            fields.append(f"  booktitle = {{{entry['source']}}}")
        if "pages" in entry:
            fields.append(f"  pages = {{{entry['pages']}}}")
    elif bibtex_type == "book":
        if "publisher" in entry:
            fields.append(f"  publisher = {{{entry['publisher']}}}")
    elif bibtex_type == "incollection":
        if "source" in entry:
            fields.append(f"  booktitle = {{{entry['source']}}}")
        if "publisher" in entry:
            fields.append(f"  publisher = {{{entry['publisher']}}}")
    elif bibtex_type == "techreport":
        if "institution" in entry:
            fields.append(f"  institution = {{{entry['institution']}}}")
    elif bibtex_type == "phdthesis":
        if "school" in entry:
            fields.append(f"  school = {{{entry['school']}}}")

    # Join fields and ensure no trailing comma
    bibtex_entry = f"@{bibtex_type}{{{citation_key},\n"
    bibtex_entry += ",\n".join(fields)
    bibtex_entry += "\n}\n"

    return bibtex_entry




# Main execution
def main():
    try:
        # Check and navigate to the appropriate folder
        current_folder = os.path.basename(os.getcwd())
        if current_folder != "scripts":
            os.chdir("scripts")
        else:
            raise Exception("scripts folder not found.")

        # print("Number of arguments: "+str(len(os.sys.argv)))

        global CLIENT_ID, CLIENT_SECRET
        if len(os.sys.argv) == 1:
            credentials = load_api_credentials()
            CLIENT_ID = credentials.get("CLIENT_ID")
            CLIENT_SECRET = credentials.get("CLIENT_SECRET")
            if not CLIENT_ID or not CLIENT_SECRET:
                raise Exception("CLIENT_ID or CLIENT_SECRET not found in credentials file.")
        elif len(os.sys.argv) == 4 or len(os.sys.argv) == 5:
            CLIENT_ID = os.sys.argv[1]
            CLIENT_SECRET = os.sys.argv[2]


        # print(f"CLIENT_ID: {CLIENT_ID}")
        # print(f"CLIENT_SECRET: {CLIENT_SECRET}")

        # Ensure a valid access token
        if len(os.sys.argv) == 4:
            ## This is now deprecated
            access_token = os.sys.argv[3]
        if len(os.sys.argv) == 5:
            ## this is used by the automatic workflow. The idea is to refresh the token before accessing Mendeley
            access_token = os.sys.argv[3]
            refresh_token = os.sys.argv[4]
            access_token, expires_in = ensure_refresh_token(refresh_token)
        else:
            access_token = ensure_access_token()

        # Fetch groups
        groups = fetch_groups(access_token)
        if not groups:
            print("No groups found.")
            return

        ## if you want to allow trying out multiple groups use that
        # print("\nAvailable Groups:")
        # for i, group in enumerate(groups, start=1):
        #     print(f"{i}. {group['name']} (ID: {group['id']})")

        # # Prompt user to select a group
        # group_number = int(input("\nEnter the number of the group to fetch documents: "))
        # if group_number < 1 or group_number > len(groups):
        #     print("Invalid group number.")
        #     return
        
        # group_id = groups[group_number - 1]["id"]

        ## this is to always select the DiSC library group
        group_id = GROUP_ID
        

        # Get total document count
        total_documents = get_document_count(access_token, group_id)
        print(f"The group contains {total_documents} documents.")

        # Fetch documents
        # documents = fetch_documents(access_token, group_id)
        documents = fetch_all_documents(access_token, group_id)

        # Save JSON metadata
        json_filename = f"group_{group_id}_library_detailed.json"
        with open(json_filename, "w") as f:
            json.dump(documents, f, indent=2)
        print(f"Full JSON library saved to '{json_filename}'")

        # Save BibTeX
        bibtex_entries = [to_bibtex(doc) for doc in documents]
        # bibtex_filename = f"group_{group_id}_library.bib"
        # bibtex_filename = f"../group_{group_id}_library.bib"
        bibtex_filename = f"../library.bib"
        with open(bibtex_filename, "w") as f:
            f.writelines(bibtex_entries)
        print(f"Library converted to BibTeX and saved to '{bibtex_filename}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
