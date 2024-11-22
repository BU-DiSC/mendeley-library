import fileinput
import sys
import shutil
import bibtexparser

if (len(sys.argv) == 0):
	print ("Do not run me as a standalone script! Use ./create_short_library.sh")
	exit(-1)

if (len(sys.argv) == 2):
	if (sys.argv[1]=="-f"):
		print ("Running shorten_papers from create_short_library.sh.")
	else:
		print ("Do not run me as a standalone script! Use ./create_short_library.sh")
		exit(-1)
else:
	print ("Do not run me as a standalone script! Use ./create_short_library.sh")
	exit(-1)

def replaceAll(filename,searchExp,replaceExp):
    for line in fileinput.input(filename, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)

def replaceUsingDictionary(filename,dictionary):
	no_short = 0
	short = 0
	with open(dictionary, 'r') as f:
	    for line in f:
		    if line.startswith('#'): #discard it is a comment
		        continue
		    if line.endswith('\n'): #remove trailing \n
		        line = line[:-1]
		    if line:
		        conf_name = line.split('|')
		        if len(conf_name) > 1:
		            #print conf_name[1] #short name
		            #print conf_name[0] #full name of the conference
		            #msg = "Replacing all instances of \"" + conf_name[0] + "\" with \"" + conf_name[1] + "\"."
		            #msg = "\"" + conf_name[0] + "\" --> \"" + conf_name[1] + "\""
		            #print msg
		            #print "."
		            replaceAll(filename,conf_name[0],conf_name[1])
		            short+=1
		        else:
		        	#msg = "No short name for: \"" + line + "\""
		        	#print msg
		        	#print ":"
		        	no_short+=1
	msg = "Info: Shortened " + str(short) + " types (no short form for " + str(no_short) + " types)."
	print (msg)



short_names_file = 'scripts/short_names'
additional_recipies_file = 'scripts/additional_recipes'
input_library_file = 'library.bib'
output_library_file = 'library-short.bib'

shutil.copyfile(input_library_file, output_library_file)

print ("Replacing long entries ... ")
replaceUsingDictionary(output_library_file, short_names_file)


print ("Using additional recipies")
replaceUsingDictionary(output_library_file, additional_recipies_file)


# print ("Removing pages from conferene entries")
# with open(output_library_file) as bibtex_file:
# 	# bibtex_database = bibtexparser.load(bibtex_file)	
# 	s = bibtex_file.read()
# 	s.decode('UTF-8').encode('ascii','ignore')
# 	print s

with open(output_library_file) as bibtex_file:
	bibtex_database = bibtexparser.load(bibtex_file)	

#Removes pages from conference proceedings
print ("Removing pages from conference proceedings ... ")
print ("Allowing up to two authors ... ")
print ("Converting conference proceedings to articles only for the short version ...")
for e in bibtex_database.entries:
	if 'author' in e:
		# print (e['author'])
		# print (e['author'].count('and'))
		if e['author'].count('and') > 100:
			# print(e['author'].find(' and'))
			# print(e['author'][0:e['author'].find(' and')]+" and others")
			# print("\n")
			e['author']=e['author'][0:e['author'].find(' and')]+" and others"
	if e['ENTRYTYPE'] == "inproceedings":
		if 'pages' in e:
			del e['pages']
			#print e.keys()
	if e['ENTRYTYPE'] == "inproceedings":
		if 'booktitle' in e:
			if 'journal' in e:
				print ("Unexpected journal attribute in inproceedings element")
				exit(-1)
			proceedings_title = e['booktitle']
			e['journal'] = proceedings_title
			e['ENTRYTYPE'] = "article"
			del e['booktitle']


output_library_file_final = output_library_file
print ("Dumping the bibtex DB to "+output_library_file_final)
with open(output_library_file_final,'w') as bibtex_output:
 	#print bibtexparser.dumps(bibtex_database)
 	bibtex_output.write(bibtexparser.dumps(bibtex_database))
