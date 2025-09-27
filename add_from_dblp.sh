#!/bin/bash

NEW_BIB_FILE=""
function ctrl_c() {
    echo "******************************"
    echo "\nCleaning up ... \nDeleting ${NEW_BIB_FILE}."
    if [ -f "$NEW_BIB_FILE" ]; then 
        rm ${NEW_BIB_FILE}
    fi
    # Perform cleanup or other actions here
    echo "******************************"
    exit 0
}

PYTHON="python3"
PYTHON_VERSION=`$PYTHON --version 2>&1  | awk '{print substr($2,1,1)}'`

$PYTHON --version 2>&1 >  /dev/null
if [ $? -ne 0 ]; then
    echo "Unknown python version, or python does not exist"
    exit
fi

if [ $PYTHON_VERSION -ne 3 ]; then
    echo "Please make sure you are using python version 3.x"
    exit
fi


# Now this works with python 3
# pip3 install bibtexparser fuzzywuzzy python-Levenshtein
more_entries="y"
total_entries=0
until [[ "$more_entries" != "y" ]]
do 
    NEW_BIB_FILE=`mktemp temp_library.bib.XXXXXXXXX`
    trap ctrl_c INT

    $PYTHON scripts/get_bibtex_from_dblp.py --output ${NEW_BIB_FILE}

    entries_found=`wc -l ${NEW_BIB_FILE} | awk '{print $1}'`

    if [ $entries_found -gt 0 ]; then
        CUR_PATH=`pwd`
        >&2 echo "Executing from \"$CUR_PATH\""

        if [ -f "${NEW_BIB_FILE}" ]; then
            >&2 echo "Found ${NEW_BIB_FILE} to prepare!" 
        else
            cd ..
            CUR_PATH=`pwd`
            >&2 echo "Swithcing to \"$CUR_PATH\""
            if [ -f "${NEW_BIB_FILE}" ]; then
                >&2 echo "Found ${NEW_BIB_FILE}!" 
            else
                >&2 echo "Failed to find ${NEW_BIB_FILE}. Exiting ..."
                exit
            fi
        fi
        #Now we know we can find bibtex.bib


            
        MSG=`$PYTHON --version 2>&1`
        echo "Using $MSG ..."

        # echo "##########################################"
        # echo "Ensuring we have the latest library  ... "
        # echo "##########################################"
        # $PYTHON scripts/get_mendeley_library.py
        # git pull
        # git add library.bib
        # git commit -m "Making sure we have the last library"
        # git push
        # echo "##########################################"
        # echo "[ok]"
        # echo "##########################################"
        # echo

        echo "##########################################"
        echo "Prepare and upload ${NEW_BIB_FILE}  ... "
        echo "##########################################"
        $PYTHON scripts/prepare_upload_bibtex.py "${NEW_BIB_FILE}" -f
        entried_added=$?
        total_entries=$((total_entries + entried_added))
        echo "[ok]"
        echo
    else
        echo "##########################################"
        echo "No entries found in ${NEW_BIB_FILE}  ... "
        echo "##########################################"
        echo "[ok]"
        echo
    fi

    echo "##########################################"
    echo "Cleaning up ${NEW_BIB_FILE}  ... "
    echo "##########################################"
    rm $NEW_BIB_FILE
    echo "[ok]"
    echo


    read -p "Do you want to add another entry? (y/n): " more_entries
done 

if [ $total_entries -gt 0 ]; then
    echo "##########################################"
    echo "Total entries added: ${total_entries}  ... "
    echo "##########################################"

    read -p "Do you want to run ./update_all_libs.sh? (y/n): " response

    echo "##########################################"
    echo "Updating main library ... "
    echo "##########################################"
    if [[ "$response" == "y" ]]; then
        ./update_all_libs.sh
    fi
    echo "[ok]"
    echo
    echo "##########################################"
    echo "If you are working using Overleaf, please refresh the bibliography file there."
    echo "##########################################"
    echo


else
    echo "##########################################"
    echo "No entries were added. Exiting ... "
    echo "##########################################"
    echo
    echo "##########################################"
    echo "Updating main library NOT needed. "
    echo "##########################################"
fi

