#!/bin/bash

PYTHON="python3"
PYTHON_VERSION=`$PYTHON --version 2>&1  | awk '{print substr($2,1,1)}'`

$PYTHON --version 2>&1 >  /dev/null
if [ $? -ne 0 ]; then
    echo "Unkown python version, or python does not exist"
    exit
fi

if [ $PYTHON_VERSION -ne 3 ]; then
    echo "Please make sure you are using python version 3.x"
    exit
fi


# Now this works with python 3
# pip3 install bibtexparser fuzzywuzzy python-Levenshtein


NEW_BIB_FILE=./new.bib

if [ $# -eq 1 ]; then
    NEW_BIB_FILE=$1
fi


CUR_PATH=`pwd`
>&2 echo "Executing from \"$CUR_PATH\""

if [ -f "${NEW_BIB_FILE}" ]; then
    >&2 echo "Found find new.bib to prepare!" 
else
    cd ..
    CUR_PATH=`pwd`
    >&2 echo "Swithcing to \"$CUR_PATH\""
    if [ -f "${NEW_BIB_FILE}" ]; then
        >&2 echo "Found new.bib!" 
    else
        >&2 echo "Failed to find new.bib. Exiting ..."
        exit
    fi
fi
#Now we know we can find bibtex.bib




#LEGACY
# if [ $# -eq 1 ]; then
#     PYTHON="python$1"   
# fi

    
MSG=`$PYTHON --version 2>&1`
echo "Using $MSG ..."

$PYTHON scripts/prepare_bibtex.py "${NEW_BIB_FILE}" -f
