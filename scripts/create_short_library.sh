#! /bin/sh

CUR_PATH=`pwd`
>&2 echo "Executing \"$0\" from \"$CUR_PATH\""

if [ -f "library.bib" ]; 
then
	>&2 echo "library.bib exists in current path" 
else
	cd ..
	CUR_PATH=`pwd`
	>&2 echo "Swithcing to \"$CUR_PATH\""
	if [ -f "library.bib" ]; 
	then
		>&2 echo "library.bib exists in current path" 
	else
		>&2 echo "Failed to find libarary.bib. Exiting ..."
		exit
	fi
fi
#Now we know we are in the path of the library.bib



PYTHON="python3"

# if [ $# -eq 1 ]
# then
# 	PYTHON="python$1"	
# fi

PYTHON_VERSION=`$PYTHON --version 2>&1  | awk '{print substr($2,1,1)}'`

$PYTHON --version 2>&1 >  /dev/null
if [ $? -ne 0 ]
then
	echo "Unkown python version, or python does not exist"
	exit
fi


# if [ $PYTHON_VERSION -eq 3 ]
# then
# 	pushd scripts
# 	mv bibtexparser bibtexparser2
# 	popd
# fi
	
MSG=`$PYTHON --version 2>&1`
echo "Using $MSG ..."

echo "Saving normal recipes:"
scripts/find_long_names.sh > scripts/short_names 

$PYTHON scripts/shorten_papers.py -f
# TMP_FILE=`mktemp library.temp.XXXXXXXXXX`
# echo "Adding doule brackets back to titles ... "
# cat library-short.bib | awk '
# {
# 	if (match($0,/ title =/)) 
# 	{
# 		gsub(/{/,"{{",$0); 
# 		gsub(/}/,"}}",$0);
# 		print $0;
# 	} 
# 	else 
# 		print $0;
# }' > $TMP_FILE
# rm library-short.bib
# mv $TMP_FILE library-short.bib


 
# if [ $PYTHON_VERSION -eq 3 ]
# then
# 	pushd scripts
# 	mv bibtexparser2 bibtexparser
# 	popd
# fi
