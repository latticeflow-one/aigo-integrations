# LangSmith Model

## Overview

This guide shows an example integration of a model hosted by LangSmith.

## Usage

Configure the `config.env` file by providing your LangSmith endpoint URL, agent ID and API key.

```bash
lf --env config.env add -f run.yaml
lf test model langsmith-model
```
