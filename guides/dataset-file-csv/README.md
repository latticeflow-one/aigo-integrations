# Dataset in CSV Format

## Overview

This guide shows an example integration of a dataset in CSV format, and how to
filter it using the three available filter operators. All examples are built on
the same `test_cases.csv` file of airline passenger authentication records.

### Basic dataset

- **`dataset.yaml`** — Loads the full `test_cases.csv` dataset without any
  filtering.

### Filtered datasets

- **`completed_bookings.yaml`** — Filters the dataset to only include rows where the
  `Complete (True / False)` column is `True`. Demonstrates `op: "is_true"` (`FilterUnary`).

- **`departures_on_date.yaml`** — Filters the dataset to only include rows where
  `Departure Date` equals `2025-07-04`. Demonstrates `op: "equals"` (`FilterComparison`).

- **`excluded_departures.yaml`** — Filters the dataset to exclude the `2025-07-04` and
  `2025-07-29` departure dates. Demonstrates `op: "not_in"` (`FilterMembership`).

## Usage

```bash
lf add app -f app.yaml
lf switch playground-app
lf add dataset -f datasets/dataset.yaml
lf add dataset -f datasets/completed_bookings.yaml
lf add dataset -f datasets/departures_on_date.yaml
lf add dataset -f datasets/excluded_departures.yaml
```
