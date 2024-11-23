# mendeley-library

## Automation
A github workflow is updatnig all libraries once per day. You can also manually run the workflow by going to Actions. 

## Working locally

### Setting up
Run `./setup.sh` to get things going.
Once python3 and all packages are installed, make sure you have the credentials from https://github.com/BU-DiSC/main/wiki/Mendeley into the file ./scripts/credentials.json (do not commit this file)

### Updating the libraries from Mendeley
Just give:
```
./update_all_libs.sh
```
and all library files will be updated from the latest library in Mendeley 

### Adding new files
Make sure you first update_all_libs.sh
Copy-paste the bibtex code you want in new.bib, and then give:
```
./prepare_upload_new_bibtex.sh
```
it will check if papers exist and ultimately ask you to upload them to Mendeley!
