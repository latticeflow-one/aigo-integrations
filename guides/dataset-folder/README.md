# Folder Dataset

## Overview

This guide shows an example integration of a dataset built from every file in a
local folder. The folder is scanned recursively, and each file becomes one row
with three columns:

- **`sample_id`** — SHA-256 hash of the file's content.
- **`file_name`** — path of the file relative to `directory_path` (nested files
  keep their leading subdirectories, e.g. `refunds/refund_policy.md`).
- **`content`** — the file's UTF-8 decoded content.

The optional `extension` field restricts the scan to files with a given
extension (here, `md`). PDF files are always skipped since their binary content
cannot be loaded as text.

## Metadata headers

Files with a YAML front matter header — a `---` delimited block at the top of
the file, as used by the example documents — contribute one extra column per
metadata key. For example, the following document adds `title` and `category`
columns, and its `content` excludes the header:

```md
---
title: Baggage Policy
category: baggage
---

# Baggage Policy
...
```

If a header is present but not valid YAML, a warning is logged and the file is
still included with its original content, but without metadata columns.

## Usage

```bash
lf add app -f app.yaml
lf switch dataset-folder
lf add dataset -f datasets/dataset.yaml
```
