# mendeley-library

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

### Deploy
Use this URL for direct access: 
```
https://raw.githubusercontent.com/BU-DiSC/mendeley-library/refs/heads/master/library.bib
```

### Adding the library to Overleaf
Link the library to your Overleaf project once; you can then pull in new entries with one click.

1. In your Overleaf project, click **New File** or **Upload** (the icons at the top of the file tree).
2. Choose **From external URL**.
3. Paste this URL:
   ```
   https://raw.githubusercontent.com/BU-DiSC/mendeley-library/refs/heads/master/library.bib
   ```
4. Name the file `library.bib` and click **Create**.
5. Cite from it in your `.tex` file as usual, e.g.:
   ```latex
   \bibliographystyle{plain}
   \bibliography{library}        % BibTeX (no .bib extension)
   % or, with biblatex:
   % \addbibresource{library.bib}
   ```

**Getting new entries:** Overleaf does not update linked files on its own. When the library has changed (the GitHub workflow updates it every 2 hours), open `library.bib` in Overleaf and click **Refresh**.

**Other versions of the library:** to link a different version, use the same URL but replace `library.bib` at the end with one of the file names below:

| File | Contents |
|------|----------|
| `library.bib` | Full library (all fields) |
| `library-no-doi.bib` | DOI fields removed (URLs kept) |
| `library-no-url.bib` | URL and DOI fields removed |
| `library-short.bib` | Venue names shortened to their acronyms (e.g., `ICDE`, `FAST`) |
| `library-no-url-short.bib` | Short venue names; URL and DOI fields removed |
| `library-no-url-no-pages-short.bib` | Short venue names; URL, DOI, and page fields removed |
| `library-no-url-no-pages-clean.bib` | Full venue names without the trailing acronym in parentheses; URL, DOI, and page fields removed |


# Automation
A github workflow is updating all libraries every 2 hours. You can also manually run the workflow by going to [Actions](https://github.com/BU-DiSC/mendeley-library/actions). 
