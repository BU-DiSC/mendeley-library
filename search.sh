#! /bin/sh

CUR_PATH=`pwd`
echo "Executing from \"$CUR_PATH\""

if [ -f "library.bib" ]; 
then
	echo "library.bib exists in current path" 
else
	cd ..
	CUR_PATH=`pwd`
	echo "Swithcing to \"$CUR_PATH\""
	if [ -f "library.bib" ]; 
	then
		echo "library.bib exists in current path" 
	else
		echo "Failed to find libarary.bib. Exiting ..."
		exit
	fi
fi
#Now we know we are in the path of the library.bib

PYTHON="python3"

PYTHON_VERSION=`$PYTHON --version 2>&1  | awk '{print substr($2,1,1)}'`

$PYTHON --version 2>&1 >  /dev/null
if [ $? -ne 0 ]
then
	echo "Unkown python version, or python does not exist"
	exit
fi


if [ $PYTHON_VERSION -ne 3 ]
then
	echo "Please use python 3"
	exit
fi
	
MSG=`$PYTHON --version 2>&1`
echo "Using $MSG ..."

$PYTHON scripts/search_author.py $@ 

