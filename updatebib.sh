#! /bin/bash

git pull
pushd ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley
./populate_additional_libraries.sh
popd
cp ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley/library-no-url-short.bib .
cp ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley/library-no-url.bib .
cp ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley/library-short.bib .
cp ~/Dropbox/Professional/Professorship/W-Lab/Bibliography-Mendeley/library.bib .

git add -f library-no-url.bib library.bib library-no-url-short.bib library-short.bib
git commit -m "auto updating bib library"
git push

