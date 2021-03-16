#! /bin/bash

if [ ! -f .disc-library-config ];then
    echo "Please create in this directory a file named \".disc-library-config\" that contains only the full path of the shared mendeley library file."
    echo "As an example, the only contents of the file may be:"
    echo "  /Users/mathan/Dropbox/W-Lab/Bibliography-Mendeley"
    exit
fi

DISC_MENDELEY_LIB_PATH=`cat .disc-library-config`


git pull
pushd ${DISC_MENDELEY_LIB_PATH}
./populate_additional_libraries.sh
popd
cp ${DISC_MENDELEY_LIB_PATH}/library-no-url-short.bib .
cp ${DISC_MENDELEY_LIB_PATH}/library-no-url.bib .
cp ${DISC_MENDELEY_LIB_PATH}/library-short.bib .
cp ${DISC_MENDELEY_LIB_PATH}/library.bib .


git add -f library-no-url.bib library.bib library-no-url-short.bib library-short.bib
git commit -m "auto updating bib library"
git push

