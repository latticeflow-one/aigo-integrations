# OpenCode Model

## Overview

This guide shows an example integration of an OpenCode agent.

## Usage

Configure the `config.env` file by providing your OpenCode URL, as well as the ID of the
model and model provider to use.

```bash
lf --env config.env add -f run.yaml
lf test model opencode-agent
```
