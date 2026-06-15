# LangSmith Model

## Overview

This guide shows an example integration of a model hosted by LangSmith.

## Usage

Configure the `config.env` file by suppying your LangSmith endpoint URL, agent ID and API key.

```bash
lf add app -f app.yaml
lf switch playground-app
lf --env config.env add -f run.yaml
lf test model langsmith-model
```
