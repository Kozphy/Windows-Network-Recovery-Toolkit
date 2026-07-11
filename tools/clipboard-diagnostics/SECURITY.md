# Security Policy

## Privacy model

This project does not intentionally persist clipboard contents. Diagnostic evidence records hashes, lengths, timing, status, and error metadata.

The script restores readable text clipboard content after the test when possible. It cannot guarantee preservation of non-text clipboard formats such as images, files, HTML, or rich text. Users should finish any important paste operation before running the diagnostic.

## Reporting a vulnerability

Open a GitHub security advisory or private report rather than posting sensitive clipboard contents in a public issue.
