---
name: sticky-notes
description: Read and update tasks or notes in a user-selected Markdown notes folder. Use when the user asks to check, add, organize, or complete items in their sticky notes.
---

# Sticky Notes

Work with plain Markdown notes in the directory the user selected. No notes app
is required; this skill does not install or control a floating-notes UI.

## Find the right note

- Use the directory named in the request or configured in the user's workspace
  instructions. If neither identifies it, ask for the notes directory. Do not
  guess a personal path or search the user's entire home directory.
- List the Markdown files, choose the note relevant to the request, and read its
  headings and surrounding text before editing. If several notes fit, ask which
  one the user means.
- Create a new note when requested. Otherwise prefer the relevant existing note
  and ask before creating a separate one if no note clearly fits.

Notes record user intent and task state. Verify engineering facts against code,
issues, Git state, or the running product before reporting them as current.

## Make the requested change

- Preserve headings, links, encoding, list structure, and wording outside the
  requested change. Add tasks under the relevant existing heading, using
  unchecked Markdown checkboxes (`- [ ]`) unless the note uses another format.
- Mark a task complete only after verifying its underlying result. A plan,
  partial implementation, or passing build does not prove a deployment or a
  working user flow. If the result cannot be checked, leave it open and report
  what remains unverified.
- Preserve completed items unless asked to reopen them. Do not rename, delete,
  rewrite, or reorganize notes without authorization for that operation.
- Treat personal writing and lists as read-only unless the user names them for
  editing. Keep secrets, credentials, and sensitive customer data out of notes.
- Keep decomposition light: record the next action, owner, or dependency when
  useful rather than duplicating an entire project plan.

## Verify the note

Re-read the edited section and inspect the narrow diff against its prior text.
If the folder is not tracked in Git, compare the text read before the edit with
the result; do not initialize a repository just to obtain a diff. Confirm that
unrelated content stayed intact. Report the note and section changed, and
whether it records intent, work in progress, or a verified outcome.
