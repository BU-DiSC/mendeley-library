def format_authors(authors_string):
    """
    Converts a string of authors separated by "and" into a list of names 
    in the format "lastname, firstname middle_initial".
    
    Parameters:
    - authors_string: A string of authors separated by "and".
    
    Returns:
    - A list of formatted author names.
    """
    formatted_authors = []
    
    # Split the authors string by "and"
    authors = authors_string.split(" and ")
    
    # Check if authors already have commas
    if all("," in author for author in authors):
        return authors_string

    for author in authors:
        # Split the name into parts
        name_parts = author.split()
        
        if len(name_parts) < 2:
            # Skip if the name does not have at least two parts
            continue
        
        # Last word is the last name
        last_name = name_parts[-1]
        
        # Remaining words are the first name and middle names
        first_names = name_parts[:-1]
        
        # Create initials for middle names (excluding the first name)
        first_name = first_names[0]
        middle_initials = " ".join([name[0] + ". " for name in first_names[1:]]).strip()
        
        # Format the name
        if middle_initials:
            formatted_name = f"{last_name}, {first_name} {middle_initials}"
        else:
            formatted_name = f"{last_name}, {first_name}"
        
        formatted_authors.append(formatted_name)
        formatted_authors_string = " and ".join(formatted_authors)
    
    return formatted_authors_string

def yes_or_no(question):
    reply = str(input(question+' (y/n): ')).lower().strip()
    if not reply:
        return yes_or_no(question)
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return yes_or_no(question)

def convert_to_mendeley_json(json_entry, group_id):
    """
    Converts a single BibTeX entry into Mendeley JSON format, excluding empty fields.

    Parameters:
    - json_entry: Dictionary representing a single BibTeX entry.
    - group_id: The Mendeley group ID to associate the entry with.

    Returns:
    - Dictionary in Mendeley JSON format with non-empty fields.
    """
    # Map BibTeX types to Mendeley types
    bibtex_type_map = {
        "inproceedings": "conference_proceedings",
        "article": "journal",
        "book": "book",
        "incollection": "book_section",
        "phdthesis": "thesis",
        "techreport": "report"
    }

    if "ID" not in json_entry:
        raise ValueError("The key 'ID' is missing in the json_entry.")
    # Convert the json entry
    mendeley_json = {
        "type": bibtex_type_map.get(json_entry.get("ENTRYTYPE", ""), "generic"),
        "title": json_entry.get("title", "").strip(),
        "authors": [
            {
                "first_name": " ".join(name.split(" ")[:-1]).strip() if len(name.split(" ")) == 3 and ", " not in name else (name.split(", ")[1].strip() if ", " in name else name.split(" ")[0].strip()),
                "last_name": name.split(", ")[0].strip() if ", " in name else name.split(" ")[-1].strip()
            } for name in json_entry.get("author", "").split(" and ") if name.strip()
        ],
        "year": json_entry.get("year", "").strip(),
        "websites": [
            json_entry.get("url", "").strip()
        ],
        "identifiers": {
            "doi": json_entry.get("doi", "").strip(),
            "isbn": json_entry.get("isbn", "").strip(),
            "issn": json_entry.get("issn", "").strip()
        },
        "source": json_entry.get("journal", json_entry.get("booktitle", "")).strip(),
        "pages": json_entry.get("pages", "").strip(),
        "volume": json_entry.get("volume", "").strip(),
        "issue": json_entry.get("number", "").strip(),
        "abstract": json_entry.get("abstract", "").strip(),
        "keywords": [keyword.strip() for keyword in json_entry.get("keywords", "").split(", ") if keyword.strip()],
        "group_id": group_id,
        "citation_key": json_entry.get("ID", "").strip(),
    }

    # Remove empty fields from the top-level and nested dictionaries
    def remove_empty_fields(data):
        if isinstance(data, dict):
            return {k: remove_empty_fields(v) for k, v in data.items() if v}
        elif isinstance(data, list):
            return [remove_empty_fields(v) for v in data if v]
        return data

    return remove_empty_fields(mendeley_json)