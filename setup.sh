#!/bin/bash

if ! command -v python3 &> /dev/null
then
    echo "Python3 could not be found. Please install Python3."
    echo 
fi

if [ -f "requirements.txt" ]; then
    echo "##############################"
    echo "Installing Python requirements ..."
    echo "##############################"
    pip3 install -r requirements.txt 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "An error occurred while installing Python requirements. You probably employ a different way to manage Python packages, such as a virtual environment or a package manager, but you still need to install the packages in requirements.txt."
    else    
        echo "[ok]"
    fi
    echo 
fi


echo "##############################"
echo "Credentials"
echo "##############################"
CRED_FILE=./scripts/credentials.json
if [ -f "${CRED_FILE}" ]; then
    echo "Credentials file \"${CRED_FILE}\" exists ..."
else
    echo "Creating ${CRED_FILE} ..."
    touch ${CRED_FILE}
    echo "{" >> ${CRED_FILE}
    echo "\"CLIENT_ID\": \"XXXXX\"," >> ${CRED_FILE}
    echo "\"CLIENT_SECRET\": \"XXXXXXXXXXXXXX\"" >> ${CRED_FILE}
    echo "}" >> ${CRED_FILE}
fi
echo "Make sure you use the credentials from https://github.com/BU-DiSC/main/wiki/Mendeley in ${CRED_FILE}."
echo 

echo "##############################"
echo "Usage"
echo "##############################"
echo "Just give:"
echo "./update_all_libs.sh" 
echo "to retrieve all updated libraries from Mendeley and push to the root folder of the repository."
echo 

echo "##############################"
echo "For new.bib preparation"
echo "##############################"
touch new.bib
echo "By giving:"
echo "./prepare_new_bibtex.sh" 
echo "you get a clean version of the new.bib to insert to Mendeley."
echo