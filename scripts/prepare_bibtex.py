#import fileinput
import sys
import os
import json
import requests
#import shutil
import bibtexparser
#import os
#requires fuzzywuzzy (https://github.com/seatgeek/fuzzywuzzy) 
#optionally python-Levenshtein
#pip install fuzzywuzzy python-Levenshtein 
from fuzzywuzzy import fuzz
from get_mendeley_library import refresh_access_token, load_api_credentials, ensure_access_token
import get_mendeley_library

#this covers up to now
#SIGMOD
#PVLDB
#ACM SIGMOD Record

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

def add_entry_to_mendeley(access_token, bibtex_data):
    """
    Add a new document to Mendeley using BibTeX metadata.
    
    Parameters:
    - access_token: Your Mendeley API access token.
    - bibtex_data: The BibTeX string containing the entry.
    
    Returns:
    - Response from the Mendeley API.
    """
    url = "https://api.mendeley.com/documents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-bibtex",
        "Content-Disposition": 'attachment; filename="entry.bib"'  # Required header
    }
    
    # Make the POST request to add the document
    response = requests.post(url, headers=headers, data=bibtex_data)
    
    if response.status_code == 201:
        print("Entry successfully added to Mendeley.")
    else:
        print(f"Failed to add entry. Status code: {response.status_code}")
        print(f"Response: {response.text}")
    
    return response

recipes_file = 'scripts/dblp2disc.recipes'
new_library_file = sys.argv[1]
big_library_file = "./library.bib"
max_score_threshold = 80 #for capturing duplicates
replacements = {}
duplicate_keys_map = {}

if (len(sys.argv) == 0):
    print ("Do not run me as a standalone script! Use ./prepare_bibtex.sh")
    exit(-1)

if (len(sys.argv) == 3):
    if (sys.argv[2]=="-f"):
        print ("Running prepare_bibtex from ./prepare_bibtex.sh.\n")
    else:
        print ("Do not run me as a standalone script! Use ./prepare_bibtex.sh")
        exit(-1)
else:
    print ("Do not run me as a standalone script! Use ./prepare_bibtex.sh")
    exit(-1)

with open(recipes_file) as df:
    for l in df:
        a = l.split('|')
        replacements[a[0]]=a[1].replace('\n','')    

print("Opening main library \""+big_library_file+"\"...")
with open(big_library_file) as existing_bibtex_file:
    existing_bibtex_database = bibtexparser.load(existing_bibtex_file)    
existing_entries = existing_bibtex_database.entries
print("[ok]\n")

#make sure that if we have entries with no key we add a dummy key to avoid having them turned into comments
print("Ensuring entries \""+new_library_file+"\" all have a dummy key to avoid data corruption ...")
#read input file
fin = open(new_library_file, "rt")
#read file contents to string
library_file_contents = fin.read()
#replace all occurrences of the required string
library_file_contents = library_file_contents.replace('{,', '{dummy_key,')
#close the input file
fin.close()
#open the input file in write mode
fin = open(new_library_file, "wt")
#overrite the input file with the resulting data
fin.write(library_file_contents)
#close the file
fin.close()
print("[ok]\n")


print("Opening new library \""+new_library_file+"\"...")
with open(new_library_file) as new_bibtex_file:
    new_bibtex_database = bibtexparser.load(new_bibtex_file)    
# print (new_bibtex_database.entries)
# sys.exit()
print("[ok]\n")


print("Inspecting all new entries ...")
for e in new_bibtex_database.entries:
    if 'author' not in e and 'title' not in e:
        print("Please include at least author or title")
        exit(1)
    print("")
    if 'author' in e:
        e['author']=e['author'].replace("\n", " ")
    if 'title' in e:
        e['title']=e['title'].replace("{", "")
        e['title']=e['title'].replace("}", "")
        e['title']=e['title'].replace("\n", " ")
    scores = list(map(lambda x: fuzz.ratio(x.get('title','') + x.get('author', ''), e['title'] + e.get('author', '')), existing_entries))
    max_score = max(scores)
    max_score_title = existing_entries[scores.index(max_score)]['title'] if max_score > 0 else "None"
    max_score_author = existing_entries[scores.index(max_score)]['author'] if max_score > 0 else "None"
    print ("For entry \"" + e['title'] + "\" similarity score: " + str(max_score))
    if max_score >= max_score_threshold:
        # print (f"\tMost similar entry has title: \"{max_score_title}\"")
        # print (f"\tBy: \"{max_score_author}\"")
        positions = [i for i, j in enumerate(scores) if j == max_score]
        print ("***************************************")
        print ("WARNING!! Potential DUPLICATE FOUND WITH " + str(max_score) + "%.")
        print ("\"" + e['title'] + "\" from \""+new_library_file+"\" with details:")
        print ("\t"+"\n\t".join(map(str, zip(e.keys(), e.values())))) 
        print ("MATCHES EXISTING ENTRY (ENTRIES): ")
        print (positions)
        for p in positions:    
            print ("\t" + str(p)+": ", existing_entries[p]['title'])
            print ("\t"+"\n\t".join(map(str, zip(existing_entries[p].keys(), existing_entries[p].values())))) 
        print ("***************************************")
        e['to_delete'] = yes_or_no("Do you want to delete this NEW entry from \""+new_library_file+"\"?")
        print ("***************************************")
    else:
        e['to_delete'] = False
    if 'crossref' in e:
        del e['crossref']
    if 'timestamp' in e:
        del e['timestamp']
    if 'biburl' in e:
        del e['biburl']
    if 'bibsource' in e:
        del e['bibsource']
    if 'author' in e:
        e['author']=e['author'].replace("\n", " ")
    if (e['ENTRYTYPE'] == "inproceedings") and ('booktitle' in e):
        e['booktitle']=e['booktitle'].replace("{", "")
        e['booktitle']=e['booktitle'].replace("}", "")
        e['booktitle']=e['booktitle'].replace("\n", " ")
        for r in replacements:
            if r in e['booktitle']:
                e['booktitle'] = replacements[r]
                break
        if 'editor' in e:
            del e['editor']
        if 'publisher' in e:
            del e['publisher']
    if (e['ENTRYTYPE'] == "article") and ('journal' in e):    
        e['journal']=e['journal'].replace("{", "")
        e['journal']=e['journal'].replace("}", "")
        e['journal']=e['journal'].replace("\n", " ")
        for r in replacements:
            if r in e['journal']:
                e['journal'] = replacements[r]
                break
    if 'ID' in e:
        e['ID']=''
    if 'publisher' in e:    
        e['publisher']=e['publisher'].replace("{", "")
        e['publisher']=e['publisher'].replace("}", "")
    if ('author' in e) and ('year' in e) and ('title' in e):
        first_author = e['author'].split(" and ")[0].strip()
        if ',' in first_author:
            lastname=first_author.split(",")[0].strip()
        else:
            temparray=first_author.split(" ")
            lastname=temparray[len(temparray)-1].strip()
        title_words = e['title'].split()
        lastname = ''.join(filter(str.isalpha, lastname))
        title_words[0] = ''.join(filter(str.isalpha, title_words[0]))
        candidate_key = lastname + e['year'] + title_words[0].capitalize()
        for word in title_words[1:]:
            candidate_key += word[0].upper()
        print (" ==> Proposed key for \""+ e['title'] +"\": \"" + candidate_key + "\"")
        key_exists = any(ex_e['ID'] == candidate_key for ex_e in existing_entries)
        if key_exists:
            print("   !!! Proposed key exists already")
            # Generate a unique key by appending a number
            counter = 1
            new_candidate_key = candidate_key + str(counter)
            while any(ex_e['ID'] == new_candidate_key for ex_e in existing_entries):
                counter += 1
            new_candidate_key = candidate_key + str(counter)
            candidate_key = new_candidate_key
            print("   ==> New unique key: " + candidate_key)
        e['ID'] = candidate_key

output_library_file_final = new_library_file
# for debug reasons write to another file
# os.system("touch ./temp.bib")
# output_library_file_final = "./temp.bib"

print ("")
print ("Dumping "+str(len(new_bibtex_database.entries))+" entrie(s) from the bibtex DB to \""+output_library_file_final +"\"")

#Removes the entries marked as "to_delete"
new_bibtex_database_clean = new_bibtex_database 
new_bibtex_database_clean.entries = list(filter(lambda x: not x['to_delete'], new_bibtex_database.entries))


#Removes the temp "to_delete" attribute
for e in new_bibtex_database.entries:
    del e['to_delete']
    # if 'ID' in e:
    #     del e['ID']
    # json_string = json.dumps(e)
    # print json_string

# for e in new_bibtex_database.entries:
    # print(e)


#TODO
# pause
# print instructions to update the mendeley library from the mendeley app
# compare again the new vs. the full library
# print out all the changes in keys you need to do (if needed)


# print (bibtexparser.dumps(new_bibtex_database_clean))
# print (bibtexparser.dumps(new_bibtex_database))

with open(output_library_file_final,'wb') as bibtex_output:
    bibtex_output.write(bibtexparser.dumps(new_bibtex_database_clean).encode('UTF-8'))

print(output_library_file_final+" is now updated.")
if yes_or_no("Do you want to upload to Mendeley?"):
    os.chdir("scripts")
    credentials = load_api_credentials()
    get_mendeley_library.CLIENT_ID = credentials.get("CLIENT_ID")
    get_mendeley_library.CLIENT_SECRET = credentials.get("CLIENT_SECRET")
    access_token = ensure_access_token()

    print("\nIterating over all BibTeX entries:\n")
    for entry in new_bibtex_database_clean.entries:
        db = bibtexparser.bibdatabase.BibDatabase()
        db.entries = [entry]
        bibtex_entry=bibtexparser.dumps(db)
        print("\nAdding entry: "+bibtex_entry+"...")
        add_entry_to_mendeley(access_token,bibtex_entry)

