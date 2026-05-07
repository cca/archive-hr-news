# Apps Script Email Archiving

Google Apps Script to search my gmail inbox for particular emails worth archiving and save them to a Drive folder. There is a preset function for saving years of HR newsletters or President's Office emails at a time, or a more targeted `archiveEmails` function can be employed with different parameters.

## Setup

- Go to script.google.com and create a project
- Copy-paste code.js in the project's default code file
- Under **Services**, add the **Gmail API** & **Drive API**
- **Deploy** the project which causes it to ask for Gmail & Drive permissions

## Usage

Edit the `archiveHRYear(2025)` function at the top to capture a year of newsletters then **Run**. They will be saved to a folder named "HR News Archive" in your Drive, which is created if it does not exist. I have not tried moving the folder to a Shared Drive to see if files continue to be saved to it or if that causes the script to create another folder instead.

## CLI Usage

[Google's `clasp`](https://developers.google.com/apps-script/guides/clasp) utility can update and execute apps scripts from the command line. To use it, you must [enable the Apps Script API](https://script.google.com/home/usersettings) for your Google account.

```sh
pnpm install --global @google/clasp # install globally
clasp login # authenticate with Google account
clasp clone $SCRIPT_ID # clone the script to local directory
clasp push # push local changes to the script
clasp pull # pull changes from script locally
```

tl;dr — it is a lot of Google Cloud configuration to make `clasp run` work and I recommend sticking to the commands above and ignoring the below unless you are comfortable with GCP.

`clasp run run` (where "run" is the function name) _should_ execute the function, but there are a lot of steps to make it work. The Apps Script has to be associated with a GCP project. The project also needs to be deployed as an "API Executable". The GCP project needs Apps Script API enabled under "APIs & Services" as well as all APIs the script uses (e.g. Drive & Gmail). Finally, the project needs an OAuth client ID (APIs & Services > Credentials), then `clasp` need to authenticate _using those credentials_ like `clasp login --creds creds.json --use-project-scopes --include-clasp-scopes`.

## Files

The script creates PDF, HTML, and EML files for each email. It also downloads attachments. Embedded images are included in the HTML and PDF files. Note that external image references `<img src="https://example.com/image.png">` will still break if the external image is deleted. Perhaps we should be downloading and replacing these with local content, too.
