# LangSmith Model

## Overview

This guide shows an example integration of an agent hosted by OpenCode. 

## Usage

Configure the `config.env` file by suppying your OpenCode URL, as well as the ID of the
model and model provider to use.

```bash
lf app add -f app.yaml
lf switch playground-app
lf --env config.env add -f run.yaml
lf test model opencode-agent
```
