# Missing-issue investigation — 2026-10-13

## Local evidence

All eight supplied ISO-format MDF images were inventoried. Nine catalog dates have no corresponding issue file in the ISO 9660 file trees. Independent 7-Zip listings confirm the relevant gaps on discs 2 and 7. The original catalog assigns all eight 1989 gaps to disc 2 and the 1947 gap to disc 7. These are missing file references, not decoding errors. No bulk raw-sector carving or comparison with a different physical pressing has been performed.

| Date | Original disc | Expected scan pages |
| --- | --- | --- |
| 1947-09-06 | 7 | 92 |
| 1989-02-20 | 2 | 124 |
| 1989-04-03 | 2 | 120 |
| 1989-07-03 | 2 | 100 |
| 1989-08-14 | 2 | 96 |
| 1989-08-28 | 2 | 100 |
| 1989-10-09 | 2 | 140 |
| 1989-10-16 | 2 | 136 |
| 1989-11-27 | 2 | 148 |

## Online evidence

- Stephen Osborne's first-hand review of the DVD set explicitly identifies September 6, 1947 as missing: https://www.geist.com/fact/the-complete-new-yorker . This corroborates that date's omission in the original product; it does not explain its cause.
- A first-hand owner review on ThriftBooks reports inability to access February 20, 1989, while other issues on its disc work. The reviewer explicitly does not know whether the defect affects every copy: https://www.thriftbooks.com/w/the-complete-new-yorker-eighty-years-of-the-nations-greatest-magazine-book--8-dvd-roms_david-remnick/270528/item/ . This corroborates one 1989 access problem, not all eight omissions or their cause.
- Every missing date has an official issue index at https://www.newyorker.com/magazine/YYYY/MM/DD . Each exact URL was opened during this investigation. These index pages establish the issues are represented online, not that their entire scanned editions were downloaded or inspected.
- The publisher's current FAQ says its subscriber replica edition presents every print issue since 1925 and provides a Print toolbar for selected pages: https://www.newyorker.com/about/faq (sections: online replica edition / printing articles). Replica access: https://archives.newyorker.com/ . Authenticated page availability for these nine dates remains unverified.
- Targeted searches for missing issues, exact dates, and DVD patches did not locate a verified publisher patch supplying all nine. This is a bounded negative search, not proof no patch exists.

## Recovery choices

1. Use subscriber replica access to retrieve needed pages through its supported print function, save them as PDFs, and add local PDF/image replacement support to this app. The app would remain standalone after importing local files. The current app does not yet support PDF replacement ingestion.
2. Compare another original DVD pressing or later hard-drive edition. This may recover the eight 1989 dates if they were corrected; no alternate edition has been verified to contain them.
3. Obtain scans of physical/library copies and import them locally. Replacement pagination must be reconciled with the original catalog because inserts/cover scans can change offsets.

No replacement issue files were downloaded, no accounts were accessed, and no app availability flags were changed in this investigation.
