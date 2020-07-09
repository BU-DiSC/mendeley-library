#! /bin/bash

pushd ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley
./populate_additional_libraries.sh
popd
cp ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley/library*.bib .

git pull
git add -f library-no-url.bib library.bib library-no-url-short.bib library-short.bib
git commit -m "auto updating bib library"
git push

