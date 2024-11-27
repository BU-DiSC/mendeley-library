# mendeley-library

## Automation
A github workflow is updating all libraries every 2 hours. You can also manually run the workflow by going to [Actions](https://github.com/BU-DiSC/mendeley-library/actions). 

## Working locally

### Setting up
Run `./setup.sh` to get things going.
Once python3 and all packages are installed, make sure you have the credentials from https://github.com/BU-DiSC/main/wiki/Mendeley into the file ./scripts/credentials.json (do not commit this file)

### Updating the libraries in the repo from Mendeley
Just give `./update_all_libs.sh` and all library files will be updated from the latest library in Mendeley 

### Adding new entries
* Before adding new entries, make you update the library using `update_all_libs.sh`
* [Option 1] Copy-paste the bibtex code you want in new.bib, and then give: `./prepare_upload_new_bibtex.sh`
  * The script will check if paper exists
  * You will have the option to upload directly to Mendeley
* [Option 2] Use `add_from_dblp.sh` to search dblp using title, author (optionally), venue (optionally)
  * You will select one of the matching dblp entries
  * The script will check if paper exists
  * You will have the option to upload directly to Mendeley
