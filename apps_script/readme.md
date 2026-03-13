# Apps Script Email Archiving

Google Apps Script to search my gmail inbox for particular emails worth archiving and save them to a Drive folder. There is a preset function for saving years of HR newsletters or President's Office emails at a time, or a more targeted `archiveEmails` function can be employed with different parameters.

## Setup

- Go to script.google.com and create a project
- Copy-paste code.js in the project's default code file
- Under **Services**, add the **Gmail API**
- **Deploy** the project which causes it to ask for Gmail & Drive permissions

## Usage

Edit the `archiveHRYear(2025)` function at the top to capture a year of newsletters then **Run**. They will be saved to a folder named "HR News Archive" in your Drive, which is created if it does not exist. I have not tried moving the folder to a Shared Drive to see if files continue to be saved to it or if that causes the script to create another folder instead.

## Files

The script creates PDF, HTML, and EML files for each email. It also downloads attachments. Embedded images are included in the HTML and PDF files. Note that external image references `<img src="https://example.com/image.png">` will still break if the external image is deleted. Perhaps we should be downloading and replacing these with local content, too.
