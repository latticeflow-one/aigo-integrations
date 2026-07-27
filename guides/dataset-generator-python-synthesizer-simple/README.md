# Dataset Generator with a Simple Python Synthesizer

## Overview

This guide shows the smallest useful Python synthesizer: it reads each sample of a seed
dataset and derives new samples from it. The seed dataset holds one temperature per
city, and the synthesizer turns every seed sample into two temperature conversion
questions.

A Python synthesizer is the right choice here because the answers have to be *computed*
(Celsius to Fahrenheit), which a Jinja template cannot do. For a version that generates
samples from scratch, without a seed dataset, see the
[dataset-generator-python-synthesizer](../dataset-generator-python-synthesizer) guide.

## Seed dataset

```csv
city,temperature_celsius
Berlin,21
Paris,17
Tokyo,26
```

## Resulting dataset

Each seed sample yields the two samples returned by `synthesize`, so the 3 seed samples
produce 6 output samples:

```text
| question                                           | answer  |
| :------------------------------------------------- | :------ |
| It is 21 °C in Berlin. What is that in Fahrenheit? | 69.8 °F |
| It is 69.8 °F in Berlin. What is that in Celsius?  | 21 °C   |
| It is 17 °C in Paris. What is that in Fahrenheit?  | 62.6 °F |
| It is 62.6 °F in Paris. What is that in Celsius?   | 17 °C   |
| It is 26 °C in Tokyo. What is that in Fahrenheit?  | 78.8 °F |
| It is 78.8 °F in Tokyo. What is that in Celsius?   | 26 °C   |
```

## Usage

```bash
lf add app -f app.yaml
lf switch dataset-generator-python-synthesizer-simple
lf add -f run.yaml
```

If you want to iterate on the dataset generation, try:

```bash
lf test dataset -f run.yaml --key unit-conversion-qa --num-samples 2
```
