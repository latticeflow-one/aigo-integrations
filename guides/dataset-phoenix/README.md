# Arize Phoenix Traces Dataset

## Overview

This guide shows how to create a dataset by ingesting traces from an
[Arize Phoenix](https://docs.arize.com/phoenix) project. The `phoenix` dataset source
type connects to the Phoenix API and imports traces as dataset samples.

This source type requires the `traces` extra to be installed:

```bash
pip install 'latticeflow-go-sdk[traces]'
```

## Usage

Configure the required environment variables by creating a `.env` file.

```bash
PHOENIX_API_KEY=<PHOENIX_API_KEY>
PHOENIX_BASE_URL=<PHOENIX_BASE_URL>
PHOENIX_PROJECT=<PHOENIX_PROJECT>
```

```bash
lf add app -f app.yaml
lf switch playground-app
lf add dataset -f datasets/phoenix_traces.yaml
```
