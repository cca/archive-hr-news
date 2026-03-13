/**
 * Archive email in Gmail to Drive as dated PDFs.
 *
 * Notes:
 * - startDate and endDate are strings 'YYYY-MM-DD'.
 * - If folderId is null, a folder named 'email@cca.edu Email Archive' is created in your Drive root or reused if it already exists there.
 * Google API References:
 * - Drive App: https://developers.google.com/apps-script/reference/drive/drive-app
 * - Folder Class: https://developers.google.com/apps-script/reference/drive/folder
 * - Gmail App: https://developers.google.com/apps-script/reference/gmail
 * - GmailMessage Class: https://developers.google.com/apps-script/reference/gmail/gmail-message
 * - Advanced Gmail API: https://developers.google.com/workspace/gmail/api/reference/rest
 */

// Print more messages to the log
const DEBUG = true

// These folders exist in ephetteplace Drive
const folders = {
  "Tests": "1PNkVdj0O-Ky5XOhrZ06n0qVcHrAnQ3OV",
  "HR News": "1OeKtq6FnprqLo7iu8-eyqOx3HzuFBPh0",
  "President's Office": "1z7oiwjQIwnQ_Orq2nsp80q0qx9bqoKPd",
}

// archive HR newsletters
// archiveHRYear(2025)
// Test archiving President's Office emails for 2025
archiveEmails('2025-08-11', '2025-08-13', 'presidents-office@cca.edu', null, folders["Tests"])

/**
 * Archive emails from your Gmail inbox to Drive as dated PDFs, along with EML and HTML files.
 * The function arguments are used to filter emails.
 * @param {string} startDate - inclusive start date (YYYY-MM-DD)
 * @param {string} endDate - exclusive end date (YYYY-MM-DD)
 * @param {string} sender - email address
 * @param {(string|null|undefined)} subjectKeyword - optional subject keyword(s)
 * @param {(string|null|undefined)} folderId - optional Drive folder ID to save files into
 * @returns {undefined}
 */
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

  // Gmail.Users.Messages.list is an alternative approach, since we already need the advanced API
  // https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
  let threads = GmailApp.search(query, 0, 500) // adjust limit if needed
  log(`Found ${Math.floor(threads.length)} threads`)

  let folder = DriveApp.getFolderById(folderId)
  let saved = 0

  threads.forEach(function(thread) {
    let messages = thread.getMessages()
    messages.forEach(function (msg) {
      // Only archive messages from sender, e.g. 2025-01-27 Denise Newman thread w/ staff replies
      if (msg.getFrom().toLowerCase().indexOf(`<${sender.toLowerCase()}>`) === -1) {
        return log(`Skipping mail from ${msg.getFrom()}`, true)
      }

      let formattedDate = Utilities.formatDate(msg.getDate(), Session.getScriptTimeZone(), 'yyyy-MM-dd')
      let subject = msg.getSubject() || '(no subject)'
      let safeSubject = sanitizeFilename(subject)
      let filenameBase = formattedDate + ' - ' + safeSubject
      let savedAttachments = []
      let contentIdMap = {} // map of contentId to saved attachment File
      // Use Advanced Gmail API to get the MIME parts, necessary for CIDs to embed images
      // https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get
      const advancedMessage = Gmail.Users.Messages.get('me', msg.getId())
      // Every message has a payload = parent MessagePart with child parts array of msg & attachments
      const parts = advancedMessage.payload.parts || []

      // Iterate over message parts, saving attachments & embedded images, while mapping CIDs for embedded images
      // Embedded image parts have a headers array like:
      // [ {value: 'image/png; name=image', name: 'Content-Type'},
      // {name: 'Content-Disposition', value: 'inline; filename=image'},
      // {name: 'Content-Transfer-Encoding', value: 'base64'},
      // {value: '<ii_me8xoqf40>', name: 'Content-ID'},
      // {value: 'ii_me8xoqf40', name: 'X-Attachment-Id'} ]
      parts.forEach(function (part) {
        if (!part.filename) return // message body lacks a filename

        // Find the base64-encoded attachment data
        // parts EITHER have body.data or body.attachmentID, in latter case we must get the attachment via API
        let data = null // byte array NOT base64 string
        if (part.body.attachmentId) {
          let attachment = Gmail.Users.Messages.Attachments.get('me', msg.getId(), part.body.attachmentId)
          data = attachment.data
        } else {
          data = Utilities.base64Decode(part.body.data)
        }
        if (!data) {
          log(`No data for attachment part: ${part.filename} ${part.mimeType}`)
          return
        }

        try {
          log(`Saving attachment: ${part.filename} ${part.mimeType} ${part.body.size} bytes`, true)

          // Save part file to Drive
          const blob = Utilities.newBlob(data, part.mimeType, part.filename)
          // folder.CreateFile accepts blob of any size but has no other parameters
          let file = folder.createFile(blob)
          file.setDescription('Attachment from email dated ' + formattedDate + ' with subject "' + subject + '"')

          // Embedded images seem to be named "image" without a file extension, or maybe named after their
          // alt text, but that is usually "image". We rename them to disambiguate.
          if (part.filename === 'image') {
            let ext = ''
            if (part.mimeType && part.mimeType.match(/^image\//)) {
              ext = part.mimeType.split('/')[1]
            }
            // This naming convention collocates the image with the email & avoids name collisions
            const rand = Math.floor(Math.random() * 100000).toString().padStart(5, '0')
            file.setName(formattedDate + '-image-' + rand + (ext ? '.' + ext : ''))
          } else {
            file.setName(sanitizeFilename(formattedDate + ' ' + part.filename))
          }
          savedAttachments.push(file)

          // Map Content-ID to saved file for embedded images, this data is only in the part headers which
          // are only available in the advanced gmail API. It looks like an embedded image part has two CID
          // headers: [{value: '<CID>', name: 'Content-ID'}, {value: 'CID', name: 'X-Attachment-Id'}]
          let cidHeader = part.headers.find(h => h.name === 'Content-ID')
          if (!cidHeader) cidHeader = part.headers.find(h => h.name === 'X-Attachment-Id')
          if (cidHeader && file) {
            let cid = cidHeader.value.replace(/[<>]/g, '')
            contentIdMap[cid] = file
          }
        } catch (e) {
          log(`Failed saving attachment for ${filenameBase}: ${e && e.message}`)
        }
      })

      // Build HTML snapshot
      let html = buildMessageHtml(msg, savedAttachments, contentIdMap)

      // Save 3 files: HTML, EML, and a PDF created from HTML
      try {
        // Save EML file
        const rawContent = msg.getRawContent()
        const emlBlob = Utilities.newBlob(rawContent, 'message/rfc822', filenameBase + '.eml')
        folder.createFile(emlBlob)
        // Save HTML file
        const htmlBlob = Utilities.newBlob(html, 'text/html', filenameBase + '.html')
        folder.createFile(htmlBlob)
        // Convert HTML blob to PDF and save
        const pdfBlob = htmlBlob.getAs('application/pdf').setName(filenameBase + '.pdf')
        const pdfFile = folder.createFile(pdfBlob)
        saved++
        log(`Saved PDF: ${pdfFile.getName()}`, true)
      } catch (e) {
        log(`Failed converting/saving PDF for ${filenameBase}: ${e && e.message}`)
      }
    })
  })

  log(`Saved ${saved} emails`)
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
  return archiveYear(year, 'hr@cca.edu', 'HR NEWS', folders["HR News"])
}

/* ---------------------- Helper functions ---------------------- */

/**
 * Debug-aware logging, log('msg') logs 'msg'
 * while log('msg', true) only logs 'msg' if DEBUG is true
 * @param {string} msg
 * @param {boolean} obeyDebug only log if DEBUG is true
 * @returns {undefined}
 */
function log(msg, obeyDebug = false) {
  if (obeyDebug && !DEBUG) return
  console.log(msg)
}

/**
 * Get Drive folder, creating it if it does not exist.
 * @param {string} name
 * @returns {GoogleAppsScript.Drive.Folder}
 */
function getOrCreateFolderByName(name) {
  let folders = DriveApp.getFoldersByName(name)
  if (folders.hasNext()) return folders.next()
  return DriveApp.createFolder(name)
}

/**
 * Sanitize a filename by removing or replacing characters that are not allowed in filenames.
 * @param {string} name - original filename
 * @returns {string} sanitized filename
 */
function sanitizeFilename(name) {
  // remove slashes and other awkward filesystem chars, limit length
  let s = name.replace(/[\\\/:\*\?"<>\|]/g, ' ').replace(/\s+/g, ' ').trim()
  if (s.length > 120) s = s.substring(0, 120) + '…'
  return s
}

/**
 * Replace cid: references in HTML with base64-encoded data URIs for images
 * @param {string} html - HTML content
 * @param {object} contentIdMap - hash map of contentId to Drive File
 * @returns {string} HTML with cid: references swapped for data URIs
 */
function convertCIDtoBase64(html, contentIdMap) {
  return html.replace(/cid:([^'">\s]+)/g, function(match, cid) {
    let file = contentIdMap[cid]
    if (file) {
      let blob = file.getBlob()
      let base64Data = Utilities.base64Encode(blob.getBytes())
      return 'data:' + blob.getContentType() + ';base64,' + base64Data
    } else {
      return match // leave unchanged
    }
  })
}

/**
 * Decorate the email message body to be a complete HTML representation with
 * select headers, embedded images, and a list of attachments.
 * @param {object} msg - GmailMessage object https://developers.google.com/apps-script/reference/gmail/gmail-message
 * @param {array} attachments - Array of GmailAttachment objects https://developers.google.com/apps-script/reference/gmail/gmail-attachment
 * @param {object} contentIdMap - map of contentId to Drive File for embedded images
 * @returns {string} HTML email
 */
function buildMessageHtml(msg, attachments, contentIdMap) {
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

  if (contentIdMap) {
    bodyHtml = convertCIDtoBase64(bodyHtml, contentIdMap)
  }

  let attachmentsHtml = ''
  if (attachments && attachments.length) {
    attachmentsHtml = '<div style="margin-top:12px;"><strong>Attachments saved:</strong><ul>'
    attachments.forEach(function(file) { attachmentsHtml += '<li>' + escapeHtml(file.getName()) + '</li>'; })
    attachmentsHtml += '</ul></div>'
  }

  let footer = '<div style="margin-top:16px;font-size:10px;color:#666;">Archived via Apps Script on ' + escapeHtml(new Date().toString()) + '</div>'

  return '<!doctype html><html><head><meta charset="utf-8"><title>'
    + escapeHtml(msg.getSubject() || '')
    + '</title></head><body>'
    + headersHtml + '<hr>' + bodyHtml
    + attachmentsHtml + footer + '</body></html>'
}

/**
 * Escape HTML special characters to prevent HTML injection,
 * e.g. in email headers (subject, from, attachment names).
 * @param {(string|null|undefined)} s - the string to escape
 * @returns {string} escaped string
 */
function escapeHtml(s) {
  if (s === null || s === undefined) return ''
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
