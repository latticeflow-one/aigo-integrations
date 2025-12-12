# LatticeFlow AI GO! Integration Examples

## Purpose of Repository

Welcome to the **LatticeFlow AI GO! Integrations** repository. This codebase serves as the central hub for connecting your Generative AI and LLM ecosystem with the LatticeFlow AI GO! platform.

Designed for AI Engineers, this repository provides the necessary blueprints, adapters, and configuration schemas to seamlessly import LLMs, prompt datasets, and evaluation logic. Whether you are benchmarking a new Open Weight model, connecting a custom RAG pipeline, or defining safety guardrails, this repository contains the integration patterns required to make your assets native to the AI GO! environment.

Use this repository to:
- **Standardize LLM Integration**: Leverage pre-built templates for chat models and prompt datasets to ensure compatibility.
- **Accelerate GenAI Deployment**: Quickly adapt existing inference endpoints to work with LatticeFlow’s robust evaluation engine.
- **Extend Functionality**: Contribute new model adapters and synthetic data generators to broaden support for diverse NLP tasks.

## Platform Overview

<img width="1526" height="637" alt="image" src="https://github.com/user-attachments/assets/e42bde36-4dc1-4177-bb90-60bd8a018bcc" />


## Repository Structure

This repository is structured to modularize the different components in AI GO!. We use **YAML** as the primary configuration language to define entity metadata, prompt templates, and runtime requirements.

- [**apps/**](./apps)
  - Contains application-level configurations that tie multiple components (models, datasets, evaluators) together into cohesive workflows.
  - Example, to create an AI App:
    ```shell
    lf app create airline_chatbot.yaml
    ```

- [**tasks/**](./tasks)
  - Defines the evaluation tasks that test your GenAI application. To define a task, it includes to specify the dataset, solver, and scoring metrics.
  - Example, to create a Task:
    ```shell
    lf task create sentiment_analysis_task.yaml
    ```

- [**models/**](./models)
  - YAML definitions for specific GenAI models. This is where you register your model identity and reference its artifacts or API endpoints.
  - Example, to create a Model:
    ```shell
    lf model create model_with_api_key_auth.yaml
    ```

- [**model_adapters/**](./model_adapters)
  - The integration glue code. These scripts or containers wrap your raw model inference code (or API calls to providers like OpenAI/Anthropic) to communicate with the LatticeFlow platform's standard interfaces.
  - Example, to create a Model Adapter:
    ```shell
    lf model-adapter create openai_chat_completion.yaml
    ```

- [**datasets/**](./datasets)
  - Configurations for registered datasets, including metadata about prompt-response pairs, splits, and source locations.
  - Example, to create a Dataset:
    ```shell
    lf dataset create country_bias.yaml
    ```

- [**dataset_generators/**](./dataset_generators)
  - Scripts and configs for generating synthetic prompts or processing raw text corpora into ingestion-ready formats.
  - Example, to create a Dataset Generator:
    ```shell
    lf dataset-generator create question_generator.yaml
    ```

- [**evaluations/**](./evaluations)
  - Definitions for custom metrics (e.g., correctness, hallucinations, toxicity) and evaluation loops used to score model performance.
  - Example, to run an Evaluation:
    ```shell
    lf evaluation run toxicity_evaluator.yaml
    ```

