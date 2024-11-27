#!/usr/local/bin/python3


import sys
import bibtexparser
import re
import argparse
import os
from fuzzywuzzy import fuzz


# if (len(sys.argv) == 0):
# 	print "Do not run me as a standalone script! Use ./create_short_library.sh"
# 	exit(-1)

# if (len(sys.argv) == 2):
# 	if (sys.argv[1]=="-f"):
# 		print "Running shorten_papers from create_short_library.sh."
# 	else:
# 		print "Do not run me as a standalone script! Use ./create_short_library.sh"
# 		exit(-1)
# else:
# 	print "Do not run me as a standalone script! Use ./create_short_library.sh"
# 	exit(-1)

def printFullEntry(e):
	msg=""
	if 'ID' in e.keys():
		msg+=(e['ID']+": ") 
	if 'title' in e.keys():
		msg+=(""+e['title']+"\n") 
	if 'author' in e.keys():
		msg+=("\tby "+e['author']+"\n") 
	if 'booktitle' in e.keys():
		msg+=("\tat "+e['booktitle']) 
	elif 'journal' in e.keys():
		msg+=("\tat "+e['journal']) 
	elif 'school' in e.keys():
		msg+=("\tat "+e['school']) 
	elif 'type' in e.keys():
		msg+=("\tat "+e['type']) 
	if 'year' in e.keys():
		msg+=(", "+e['year']) 
	if 'type' in e.keys():
		msg+=(" ("+e['type']+")") 
	print (msg)

parser = argparse.ArgumentParser(description='Searching in the bibtex library.')
parser.add_argument('-k','--search-key', help='Search with an authorname or a bibtex key', required=False, dest='key', default='')
parser.add_argument('-t','--title', help='Search in title', required=False, dest='titlekey', default='')
parser.add_argument('-a','--second-author', help='Search with a secondary authorname', required=False, dest='secondary_author', default='')
parser.add_argument('-F','--print-full', help='Print full entry', action='store_true', required=False, dest='print_full_entry', default=False)
parser.add_argument('-S','--search-in-short', help='Search in library short', action='store_true', required=False, dest='search_in_library_short', default=False)

args = vars(parser.parse_args())

search_in_key = (args['key']!="")
key = args['key']
search_in_title = (args['titlekey']!="")
titlekey = args['titlekey']
search_secondary_author = (args['secondary_author']!="")
secondary_author = args['secondary_author']
print_full_entry = args['print_full_entry']
search_in_library_short = args['search_in_library_short']

if search_in_key == False and search_in_title == False:
	print 
	print ("***********************************************")
	print ("You should give at least one of (-t) or (-k) ")
	print ("See below for full usage details")
	print ("***********************************************")
	print
	# print usage 
	parser.print_help()
	quit()

foundLibrary=False
try:
	stat = os.stat("library.bib")
	print ("Found library.bib in "+os.getcwd())
	foundLibrary=True
except: 
    os.chdir("..")
	
if foundLibrary	== False:
	try:
		stat = os.stat("library.bib")
		print ("Found library.bib in "+os.getcwd())
	except: 
		print ("Cannot find library.bib. Giving up!")
		quit()


# if len(sys.argv) == 2:
# 	key = sys.argv[1]
# elif len(sys.argv) == 3:
# 	key = sys.argv[1]
# 	search_in_title = True
# 	titlekey = sys.argv[2]
# elif len(sys.argv) == 4:
# 	key = sys.argv[1]
# 	search_in_title = True
# 	titlekey = sys.argv[2]
# 	search_secondary_author = True
# 	secondary_author = sys.argv[3]

print
print ("***********************************************")
print ("Searching in bibtex libraries: ")
print ("***********************************************")
if search_in_key:
	print ("Search authorname/bibtex key: \""+key+"\"")
	print ("***********************************************")
if search_in_title:
	print ("Search keyword in title: \""+titlekey+"\"")
	print ("***********************************************")
if search_secondary_author:
	print ("Search for secondary author: \""+secondary_author+"\"")
	print ("***********************************************")

p = re.compile('.*'+key+'.*',flags=re.IGNORECASE)
ptitle = re.compile('.*'+titlekey+'.*',flags=re.IGNORECASE)
pauthor = re.compile('.*'+secondary_author+'.*',flags=re.IGNORECASE)

if search_in_library_short:
	input_library_file = 'library-short.bib'
else:
	input_library_file = 'library.bib'

with open(input_library_file) as bibtex_file:
	bibtex_database = bibtexparser.load(bibtex_file)	

print
print ("************************************************")
print ("Entries in the main file, "+input_library_file) 
print ("************************************************")

for e in bibtex_database.entries:
	if search_in_key:
		if 'ID' in e.keys():
			m = p.match(e['ID'])
		if 'author' in e.keys():
			n = p.match(e['author'])
		mtest = False
		ntest = False
		if m:
			mtest = True
		if n:
			ntest = True
	else:
		mtest = ntest = True
	if mtest | ntest:
		ttest = not search_in_title
		atest = not search_secondary_author
		if search_in_title:
			t = ptitle.match(e['title'])
			if t:
				ttest = True
		if (search_secondary_author & ('author' in e.keys())):
			a = pauthor.match(e['author'])
			if a:
				atest = True
		# print
		# print (e['author'])
		# print (str(ttest) + ":" + str(atest))
		if ttest & atest:
			if print_full_entry:
				printFullEntry(e)
			else:
				print (e['ID'] + ": " + e['title'])


print ("************************************************")
print

input_library_file = 'to-be-added.bib'
try:
	with open(input_library_file) as bibtex_file:
		bibtex_database = bibtexparser.load(bibtex_file)
except FileNotFoundError:
	print(f"Cannot find {input_library_file}. Skipping this file!")
	bibtex_database = bibtexparser.bibdatabase.BibDatabase()

print
print ("************************************************")
print ("Entries in the to be added file, "+input_library_file) 
print ("************************************************")

for e in bibtex_database.entries:
	if search_in_key:
		if 'ID' in e.keys():
			m = p.match(e['ID'])
		if 'author' in e.keys():
			n = p.match(e['author'])
		mtest = False
		ntest = False
		if m:
			mtest = True
		if n:
			ntest = True
	else:
		mtest = ntest = True
	if mtest | ntest:
		ttest = not search_in_title
		atest = not search_secondary_author
		if search_in_title:
			t = ptitle.match(e['title'])
			if t:
				ttest = True
		if (search_secondary_author & ('author' in e.keys())):
			a = pauthor.match(e['author'])
			if a:
				atest = True
		# print
		# print e['author']
		# print str(ttest) + ":" + str(atest)
		if ttest & atest:
			if print_full_entry:
				printFullEntry(e)
			else:
				print (e['ID'] + ": " + e['title'])


# try:
#     input("Press enter to continue")
# except SyntaxError:
#     pass


# print
# print "***********************************"
# print "Printing including full authorlists"
# print "***********************************"



# for e in bibtex_database.entries:
# 	if 'ID' in e.keys():
# 		m = p.match(e['ID'])
# 	if 'author' in e.keys():
# 		n = p.match(e['author'])
# 	mtest = False
# 	ntest = False
# 	if m:
# 		mtest = True
# 	if n:
# 		ntest = True
# 	if mtest | ntest:
# 		print e['ID'] + ": " + e['title'] + "\n\t\t(authorlist: " + e['author'] + ")"
