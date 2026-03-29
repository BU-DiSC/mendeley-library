#! /bin/sh


CUR_PATH=`pwd`
echo "Executing \"$0\" from \"$CUR_PATH\""

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


cat library.bib \
	| sed 's/url =/\/\/url =/g' \
	| sed 's/doi =/\/\/doi =/g' \
	| sed 's/pages =/\/\/pages =/g' \
	| sed -E 's/ \([A-Za-z0-9]+\)(},?)$/\1/' \
	> library-no-url-no-pages-clean.bib
