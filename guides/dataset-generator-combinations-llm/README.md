# Dataset Generator: Combinations + LLM Synthesizer

## Overview

This guide shows how to generate a dataset from all pairwise combinations of two source
datasets using an LLM synthesizer.

The generator combines a `cities` dataset and a `languages` dataset, then uses an LLM
to produce a question-answer pair for each city-language combination.

## Column collisions

Each combination is a single source sample holding the columns of all its input
datasets. Both datasets here define a `language` column — the local language of the
city, and the language to write the question in — so the two collide. The datasets are
merged in the order they are listed under `dataset_keys`, so the last one wins:
`languages_dataset` overrides the `language` of `cities_dataset`.

```text
cities_dataset:    | country | city   | language |
                   | Germany | Berlin | German   |

languages_dataset: | language |
                   | English  |

source sample:     | country | city   | language |
                   | Germany | Berlin | English  |
```

## Usage

Requires OpenAI integration (UI or `OPENAI_API_KEY` env var).

```sh
lf integration add --provider openai --api-key $OPENAI_API_KEY
lf run -f run.yaml
```
