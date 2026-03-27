# Dataset Generator: Combinations + Template Synthesizer

## Overview

This guide shows how to generate a dataset from all pairwise combinations of two source
datasets using a template synthesizer.

The generator combines a `cities` dataset and a `distances` dataset, then renders a
prompt template for each city-distance combination, with additional field permutations
for travel direction.

## Usage

```sh
lf app add -f app.yaml
lf switch playground-app
lf run -f run.yaml
```
