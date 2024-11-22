#import fileinput
import sys
import os
import json
#import shutil
import bibtexparser
#import os
#requires fuzzywuzzy (https://github.com/seatgeek/fuzzywuzzy) 
#optionally python-Levenshtein
#pip install fuzzywuzzy python-Levenshtein 
from fuzzywuzzy import fuzz

#this covers up to now
#SIGMOD
#PVLDB
#ACM SIGMOD Record

def yes_or_no(question):
    reply = str(input(question+' (y/n): ')).lower().strip()
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return yes_or_no("Uhhhh... please enter ")


recipes_file = 'scripts/dblp2disc.recipes'
library_file = sys.argv[1]
big_library_file = "./library.bib"
max_score_threshold = 80 #for capturing duplicates
replacements = {}
duplicate_keys_map = {}

with open(recipes_file) as df:
    for l in df:
        a = l.split('|')
        replacements[a[0]]=a[1].replace('\n','')    

with open(big_library_file) as existing_bibtex_file:
    existing_bibtex_database = bibtexparser.load(existing_bibtex_file)    
existing_entries = existing_bibtex_database.entries

if (len(sys.argv) == 0):
    print ("Do not run me as a standalone script! Use ./prepare_bibtex.sh")
    exit(-1)

if (len(sys.argv) == 3):
    if (sys.argv[2]=="-f"):
        print ("Running prepare_bibtex from ./prepare_bibtex.sh.")
    else:
        print ("Do not run me as a standalone script! Use ./prepare_bibtex.sh")
        exit(-1)
else:
    print ("Do not run me as a standalone script! Use ./prepare_bibtex.sh")
    exit(-1)

#make sure that if we have entries with no key we add a dummy key to avoid having them turned into comments
#read input file
fin = open(library_file, "rt")
#read file contents to string
library_file_contents = fin.read()
#replace all occurrences of the required string
library_file_contents = library_file_contents.replace('{,', '{dummy_key,')
#close the input file
fin.close()
#open the input file in write mode
fin = open(library_file, "wt")
#overrite the input file with the resulting data
fin.write(library_file_contents)
#close the file
fin.close()



with open(library_file) as new_bibtex_file:
    new_bibtex_database = bibtexparser.load(new_bibtex_file)    

# print (new_bibtex_database.entries)

# sys.exit()


for e in new_bibtex_database.entries:
    e['title']=e['title'].replace("{", "")
    e['title']=e['title'].replace("}", "")
    e['title']=e['title'].replace("\n", " ")
    scores = map(lambda x: fuzz.ratio(x['title'], e['title']), existing_entries)
    max_score = max(scores)
    print ("For entry \"" + e['title'] + "\" similarity score: " + str(max_score))
    # print (e)
    # TODO: 
    # duplicate_keys_map[e['ID']]=''
    if max_score >= max_score_threshold:
        positions = [i for i, j in enumerate(scores) if j == max_score]
        print ("***************************************")
        print ("WARNING!! DUPLICATE FOUND WITH " + str(max_score) + "%.")
        print ("\"" + e['title'] + "\" from \""+library_file+"\" with details:")
        print ("\t"+"\n\t".join(map(str, zip(e.keys(), e.values())))) 
        print ("MATCHES EXISTING ENTRY (ENTRIES): ")
        for p in positions:    
            print ("\t" + str(p)+": ", existing_entries[p]['title'])
            print ("\t"+"\n\t".join(map(str, zip(existing_entries[p].keys(), existing_entries[p].values())))) 
        print ("***************************************")
        e['to_delete'] = yes_or_no("Do you want to delete this NEW entry from \""+library_file+"\"?")
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
    if ('author' in e) and ('year' in e):
        first_author = e['author'].split("and")[0].strip()
        if ',' in first_author:
            lastname=first_author.split(",")[0].strip()
        else:
            temparray=first_author.split(" ")
            lastname=temparray[len(temparray)-1].strip()
        candidate_key=lastname + e['year']
        print (" ==> Proposed key for \""+ e['title'] +"\": \"" + candidate_key + "\"")
        for ex_e in existing_entries:
            if ex_e['ID'] == candidate_key:
                print ("   !!! Proposed key exists already")
                #TODO crawl existing entries to find first available or create hash 

output_library_file_final = library_file
# for debug reasons write to another file
# os.system("touch ./temp.bib")
# output_library_file_final = "./temp.bib"

print ("Dumping "+str(len(new_bibtex_database.entries))+" entrie(s) from the bibtex DB to \""+output_library_file_final +"\"")

#Removes the entries markes as "to_delete"
new_bibtex_database_clean = new_bibtex_database 
new_bibtex_database_clean.entries = list(filter(lambda x: not x['to_delete'], new_bibtex_database.entries))


#Removes the temp "to_delete" attribute
for e in new_bibtex_database.entries:
    del e['to_delete']
    # if 'ID' in e:
    #     del e['ID']
    # json_string = json.dumps(e)
    # print json_string

#TODO
# pause
# print instructions to update the mendeley library from the mendeley app
# compare again the new vs. the full library
# print out all the changes in keys you need to do (if needed)


# print (bibtexparser.dumps(new_bibtex_database_clean))
# print (bibtexparser.dumps(new_bibtex_database))

with open(output_library_file_final,'wb') as bibtex_output:
    bibtex_output.write(bibtexparser.dumps(new_bibtex_database_clean).encode('UTF-8'))
 


