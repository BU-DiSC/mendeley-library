#! /bin/sh

CUR_PATH=`pwd`
>&2 echo "Executing from \"$CUR_PATH\""

if [ -f "library.bib" ]; 
then
	>&2 echo "library.bib exists in current path" 
else
	cd ..
	CUR_PATH=`pwd`
	>&2 echo "Swithcing to \"$CUR_PATH\""
	if [ -f "library.bib" ]; 
	then
		>&2 echo "library.bib exists in current path" 
	else
		>&2 echo "Failed to find libarary.bib. Exiting ..."
		exit
	fi
fi
#Now we know we are in the path of the library.bib

cat library.bib  | grep -E "journal =|booktitle =" | sort | uniq | awk -F " = " '{print $2}' | grep -v http | sed 's/},/}/g' | sed 's/{//g' | sed 's/}//g' | awk '
{if (match($0,/\(.+\)/)) 
	printf("%s|%s\n",$0,substr($0,RSTART+1,RLENGTH-2)); 
 else 
 	print $0;}' 


