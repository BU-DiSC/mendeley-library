#!/bin/bash

git pull

echo "#########################"
echo "# Updating Main Library #"
echo "#########################"
python3 ./scripts/get_mendeley_library.py
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
git commit -m "auto updating bib library"
git push

