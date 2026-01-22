## Usage

Note, this guide expects `.env` file with OPENAI_API_KEY defined. To use a different model, please adjust the model configuration.

```
lf app add -f app.yaml
lf switch playground-app

lf dataset add -f datasets/seed-dataset.yaml
lf dataset-generator add -f datasets/dataset-generator-from-template.yaml

lf dataset generation-preview datasets/qa-generated-from-template.yaml --num-samples 4
```