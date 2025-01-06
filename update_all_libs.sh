#!/bin/bash

git pull

MESSAGE="Updating all libraries through a manual call"

echo "#########################"
echo "# Updating Main Library #"
echo "#########################"
if [ "$#" -eq 4 ]; then
    python3 ./scripts/get_mendeley_library.py "$1" "$2" "$3" "$4"
    MESSAGE="Updating all libraries through a GitHub workflow"
else
    python3 ./scripts/get_mendeley_library.py
fi
echo "[ok]"
echo 

echo "##########################"
echo "# Updating Short Library #"
echo "##########################"
scripts/create_short_library.sh
echo "[ok]"
echo 


echo "###########################"
echo "# Updating No-URL Library #"
echo "###########################"
scripts/create-no-url.sh
echo "[ok]"
echo 

echo "#####################################"
echo "# Updating No-DOI (has URL) Library #"
echo "#####################################"
scripts/create-no-doi.sh
echo "[ok]"
echo 


echo "#################################"
echo "# Updating No-URL short Library #"
echo "#################################"
scripts/create-no-url-short.sh
echo "[ok]"
echo 

git add -f library-no-url.bib library-no-doi.bib library.bib library-no-url-short.bib library-short.bib
git commit -m "${MESSAGE}"
git push

