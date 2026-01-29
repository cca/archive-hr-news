/**
 * Archive email in Gmail to Drive as dated PDFs.
 *
 * Notes:
 * - startDate and endDate are strings 'YYYY-MM-DD'.
 * - If folderId is null, a folder named 'email@cca.edu Email Archive' is created in your Drive root or reused if it already exists there.
 */

// Print more messages to the log
const DEBUG = true

// These folders exist in ephetteplace Drive
const folders = {
  "Email Archive Tests": "1PNkVdj0O-Ky5XOhrZ06n0qVcHrAnQ3OV",
  "HR News Archive": "1OeKtq6FnprqLo7iu8-eyqOx3HzuFBPh0",
  "President's Office Email Archive": "1z7oiwjQIwnQ_Orq2nsp80q0qx9bqoKPd",
}

// archive HR newsletters
// archiveHRYear(2025)
// Test archiving President's Office emails for 2025
archiveEmails('2025-01-01', '2026-01-01', 'presidents-office@cca.edu', null, folders["Email Archive Tests"])

function archiveEmails(startDate, endDate, sender, subjectKeyword, folderId) {
  if (!sender) throw new Error('sender email is required')
  // Note that GmailApp 'after:' includes the date given; 'before:' excludes the date.
  if (!startDate || !startDate.match(/^\d{4}\-\d{2}\-\d{2}$/)) {
    throw new Error('startDate is required (format YYYY-MM-DD). Use archiveYear(year) to archive a full year.')
  }
  if (!endDate || !endDate.match(/^\d{4}\-\d{2}\-\d{2}$/)) {
    throw new Error('endDate is required (format YYYY-MM-DD). Use archiveYear(year) to archive a full year.')
  }

  // create folder if we do not have one
  folderId = folderId || getOrCreateFolderByName(`${sender} Email Archive`).getId()
  // handle null subjectKeyword
  subjectKeyword = subjectKeyword || ''

  let query = 'from:' + sender + ' subject:"' + subjectKeyword + '" after:' + startDate + ' before:' + endDate
  log(`Gmail query: ${query}`)

  // Gmail.Users.Messages.list is an alternative approach
  let threads = GmailApp.search(query, 0, 500) // adjust limit if needed
  log(`Found ${Math.floor(threads.length)} threads`)

  let folder = DriveApp.getFolderById(folderId)
  let saved = 0

  threads.forEach(function(thread) {
    let messages = thread.getMessages()
    messages.forEach(function (msg) {
      // TODO only archive messages FROM sender
      // See 2025-01-27 Denise Newman thread; rn we're archiving staff responses to prez office email
      let msgDate = msg.getDate()
      let formattedDate = Utilities.formatDate(msgDate, Session.getScriptTimeZone(), 'yyyy-MM-dd')
      let subject = msg.getSubject() || '(no subject)'
      let safeSubject = sanitizeFilename(subject)
      let filenameBase = formattedDate + ' - ' + safeSubject
      let attachments = msg.getAttachments()
      let savedAttachmentNames = []

      // Save attachments (if any) to folder
      attachments.forEach(function(att) {
        try {
          log(`Saving attachment: ${att.getName()} ${att.getContentType()} ${att.getSize()} bytes`, true)
          // folder.CreateFile accepts blob of any size but has no other parameters
          let attFile = folder.createFile(att.copyBlob())
          attFile.setDescription('Attachment from email dated ' + formattedDate + ' with subject "' + subject + '"')
          attFile.setName(att.getName())
          // If a file with same name exists, Drive appends (1), but we still record the name
          // ! If the name we saved is different then the HTML reference will be wrong right?
          // ! Embedded images are named "image" without a file extension, or maybe named their alt text?
          // ! But that is usually "image". We should name images by hash with correct extension
          savedAttachmentNames.push(attFile.getName())
        } catch (e) {
          log(`Failed saving attachment for ${filenameBase}: ${e && e.message}`, true)
        }
      })

      // Build HTML snapshot
      let html = buildMessageHtml(msg, savedAttachmentNames)

      // Create HTML blob and convert to PDF
      try {
        let htmlBlob = Utilities.newBlob(html, 'text/html', filenameBase + '.html')
        if (DEBUG) folder.createFile(htmlBlob) // save HTML for debugging
        // Convert HTML blob to PDF
        let pdfBlob = htmlBlob.getAs('application/pdf').setName(filenameBase + '.pdf')
        let pdfFile = folder.createFile(pdfBlob)
        saved++
        log(`Saved PDF: ${pdfFile.getName()}`, true)
      } catch (e) {
        log(`Failed converting/saving PDF for ${filenameBase}: ${e && e.message}`, true)
      }
    })
  })

  log(`Saved ${saved} PDFs`)
}

/**
 * Convenience wrapper around archiveEmails() to get emails for a full year.
 * @param {number} year
 * @param {string} sender
 * @param {string} subjectKeyword
 * @param {string} folderId
 * @returns {undefined}
 */
function archiveYear(year, sender, subjectKeyword, folderId) {
  if (!year || isNaN(year)) throw new Error('Provide a numeric year, e.g. archiveYear(2024)')
  // Note that Gmail 'after:' includes the date given; 'before:' excludes the date.
  let start = year + '-01-01'
  let end = year + 1 + '-01-01'
  return archiveEmails(start, end, sender, subjectKeyword, folderId)
}

/**
 * Specifically archive HR newsletters for a given year.
 * @param {number} year
 * @returns {undefined}
 */
function archiveHRYear(year) {
  return archiveYear(year, 'hr@cca.edu', 'HR NEWS', folders["HR News Archive"])
}

/* ---------------------- Helper functions ---------------------- */

// Debug-aware logging, log('msg') logs 'msg'
// while log('msg', true) only logs if DEBUG is true
function log(msg, obeyDebug = false) {
  if (obeyDebug && !DEBUG) return
  Logger.log(msg)
}

function getOrCreateFolderByName(name) {
  let folders = DriveApp.getFoldersByName(name)
  if (folders.hasNext()) return folders.next()
  return DriveApp.createFolder(name)
}

function sanitizeFilename(name) {
  // remove slashes and other awkward filesystem chars, limit length
  let s = name.replace(/[\\\/:\*\?"<>\|]/g, ' ').replace(/\s+/g, ' ').trim()
  if (s.length > 120) s = s.substring(0, 120) + '…'
  return s
}

function buildMessageHtml(msg, attachmentNames) {
  // Build a simple, printable HTML snapshot. msg.getBody() returns HTML body when available.
  let headersHtml = '<div style="font-family: Arial, sans-serif; margin-bottom:12px;">' +
    '<strong>From:</strong> ' + escapeHtml(msg.getFrom()) + '<br>' +
    // "To" line is always "undisclosed recipients" which tells us nothing
    // '<strong>To:</strong> ' + escapeHtml(msg.getTo()) + '<br>' +
    '<strong>Date:</strong> ' + escapeHtml(msg.getDate().toString()) + '<br>' +
    '<strong>Subject:</strong> ' + escapeHtml(msg.getSubject() || '') + '<br>' +
    '</div>'

  // TODO We could also save the plain body while debugging? Or there could be a toggle elsewhere to save plain text only?
  // ! I don't think msg.getBody is ever false, nor is the condition below a good way to check for plain text
  let bodyHtml = msg.getBody ? msg.getBody() : escapeHtml(msg.getPlainBody ? msg.getPlainBody() : '(no body)')
  // If bodyHtml is plain-text, wrap in <pre>
  if (!/<[a-z][\s\S]*>/i.test(bodyHtml)) {
    bodyHtml = '<pre style="white-space:pre-wrap;font-family:Arial,Helvetica,sans-serif;">' + escapeHtml(bodyHtml) + '</pre>'
  }

  let attachmentsHtml = ''
  if (attachmentNames && attachmentNames.length) {
    attachmentsHtml = '<div style="margin-top:12px;"><strong>Attachments saved:</strong><ul>'
    attachmentNames.forEach(function(n) { attachmentsHtml += '<li>' + escapeHtml(n) + '</li>'; })
    attachmentsHtml += '</ul></div>'
  }

  let footer = '<div style="margin-top:16px;font-size:10px;color:#666;">Archived via Apps Script on ' + escapeHtml(new Date().toString()) + '</div>'

  return '<!doctype html><html><head><meta charset="utf-8"><title>'
    + escapeHtml(msg.getSubject() || '')
    + '</title></head><body>'
    + headersHtml + '<hr>' + bodyHtml
    + attachmentsHtml + footer + '</body></html>'
}

function escapeHtml(s) {
  if (s === null || s === undefined) return ''
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
