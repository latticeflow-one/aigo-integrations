# LangSmith Traces Dataset

## Overview

This guide shows how to create a dataset by ingesting traces from a
[LangSmith](https://docs.smith.langchain.com/) project. The `langsmith` dataset source
type connects to the LangSmith API and imports traces as dataset samples.

This source type requires the `traces` extra to be installed:

```bash
uv pip install 'latticeflow-go-sdk[traces]'
```

## Usage

Configure the required environment variables by creating a `.env` file.

```dotenv
LANGSMITH_API_KEY=<LANGSMITH_API_KEY>
LANGSMITH_ENDPOINT_URL=<LANGSMITH_ENDPOINT_URL>
LANGSMITH_PROJECT=<LANGSMITH_PROJECT>
```

```bash
lf add dataset -f datasets/langsmith_traces.yaml
```
