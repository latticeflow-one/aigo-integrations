# Converting Agent Conversation Logs into AI GO Datasets

This tutorial shows how to convert agent conversation logs from an external system into AI GO's Trace format and package them as a dataset. The example uses tau2bench simulation logs, but the approach applies to any system that records multi-turn conversations with tool use.

By the end, you will have a working conversion script that reads a JSON file of agent conversations, transforms each one into an AI GO `Trace`, and writes a dataset ready for upload.

## What you will build

A Python script that:

1. Reads a JSON file containing agent conversations (tau2bench format)
2. Converts each conversation into AI GO's `Trace` entity
3. Writes a `.jsonl` dataset and a `.yaml` dataset spec

The key challenge is mapping from your source format -- whatever shape your logs happen to be in -- to the four trace item types that AI GO understands. Once that mapping is in place, the rest is mechanical.

---

## Step 1: Understand the source data

The tau2bench JSON file contains an array of simulations, each representing one agent conversation:

```json
{
  "simulations": [
    {
      "id": "6d215f9f-934d-4c11-98af-2cb3251f5087",
      "task_id": "[service_issue]airplane_mode_on|break_apn_settings|...",
      "messages": [ ... ],
      "trial": 0,
      "duration": 33.44,
      "agent_cost": 0.0157,
      "user_cost": 0.0047
    }
  ]
}
```

Each simulation's `messages` array is a standard chat-format log. Messages have a `role` (`"user"`, `"assistant"`, or `"tool"`), optional `content`, and optional `tool_calls`.

### User message

A plain text turn from the user:

```json
{
  "role": "user",
  "content": "Hi -- my phone's been showing \"No Service\" for the past few hours..."
}
```

### Assistant message with tool calls

The assistant can respond with text, tool calls, or both. When it calls tools, `content` is null and `tool_calls` lists each invocation:

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_23b00ac7d12c473...",
      "name": "get_customer_by_phone",
      "arguments": { "phone_number": "555-123-2002" }
    }
  ]
}
```

### Tool result

The result of a tool call. In tau2bench's Gemini traces, these messages lack an `id` field -- the converter must match them to their calls by position:

```json
{
  "role": "tool",
  "content": "{\"customer_id\": \"C1001\", \"full_name\": \"John Smith\", ...}"
}
```

Your own logs will look different, but the concepts map: user turns, assistant turns, tool invocations, and tool results.

---

## Step 2: Understand AI GO's Trace format

A `Trace` is a flat list of typed items representing a conversation. There are four item types:

| Item type | Description | Key fields |
|-----------|-------------|------------|
| `UserMessage` | A user's text turn | `id`, `content` |
| `AssistantMessage` | An assistant's text turn | `id`, `content` |
| `FunctionCall` | A tool invocation | `call_id`, `name`, `arguments`, `created_by` |
| `FunctionCallOutput` | The result of a tool call | `call_id`, `output`, `status` |

`FunctionCall` and `FunctionCallOutput` are linked by a shared `call_id`. The `created_by` field on `FunctionCall` records who issued the call -- both users and assistants can invoke tools.

Here is the same conversation from Step 1, after conversion:

```
[0]  assistant_message:     "Hi! How can I help you today?"
[1]  user_message:          "Hi -- my phone's been showing \"No Service\"..."
[2]  function_call:         get_customer_by_phone (call_id=b6c8b2a6bdaf, created_by=assistant)
[3]  function_call_output:  call_id=b6c8b2a6bdaf, output={"customer_id": "C1001", ...}
[4]  function_call:         get_details_by_id (call_id=e714949f8b50, created_by=assistant)
[5]  function_call:         get_details_by_id (call_id=2958920b00d5, created_by=assistant)
[6]  function_call:         get_details_by_id (call_id=125e3ea9b472, created_by=assistant)
[7]  function_call_output:  call_id=e714949f8b50, output={"line_id": "L1001", ...}
[8]  function_call_output:  call_id=2958920b00d5, output={"line_id": "L1002", ...}
[9]  function_call_output:  call_id=125e3ea9b472, output={"line_id": "L1003", ...}
[10] function_call:         get_bills_for_customer (call_id=e031d1d0c176, created_by=assistant)
[11] function_call_output:  call_id=e031d1d0c176, output=[{"bill_id": "B1003", ...}]
[12] function_call:         transfer_to_human_agents (call_id=f8dc3e0c5843, created_by=assistant)
[13] function_call_output:  call_id=f8dc3e0c5843, output=Transfer successful
[14] assistant_message:     "I've investigated your account and found that line 555-123-2002..."
[15] user_message:          "###TRANSFER###"
```

Notice how messages [4-6] are three `function_call` items followed by their three `function_call_output` items [7-9]. The `call_id` links each output back to its call, even though they are not adjacent.

---

## Step 3: Convert messages to trace items

This is the core of the conversion. We define a `Tau2BenchMessageConverter` class that walks the source messages and emits trace items. The class maintains two pieces of state: the growing list of items, and a dict of pending tool calls awaiting their results.

### Imports and class setup

```python
import hashlib
import json
import uuid
from typing import Any

from latticeflow.core.dtypes import AssistantMessage
from latticeflow.core.dtypes import SYNTHETIC_MESSAGE_STATUS
from latticeflow.core.dtypes import Trace
from latticeflow.core.dtypes import TraceItem
from latticeflow.core.dtypes import UserMessage
from latticeflow.core.dtypes import FunctionCall
from latticeflow.core.dtypes import FunctionCallOutput
from latticeflow.core.dtypes import FunctionCallOutputStatusEnum
from latticeflow.core.dtypes import FunctionCallStatus
from latticeflow.core.dtypes import InputTextContent
from latticeflow.core.dtypes import OutputTextContent


class Tau2BenchMessageConverter:

    def __init__(self) -> None:
        self.items: list[TraceItem] = []
        self.pending_calls: dict[str, str] = {}  # original_call_id -> role
```

`self.items` accumulates the converted trace items. `self.pending_calls` maps each tool call's original ID to the role that issued it, so we can match results back to their calls later.

### User and assistant text messages

These are straightforward one-to-one mappings:

```python
def convert_user_content(self, content: str) -> None:
    self.items.append(
        UserMessage(
            id=str(uuid.uuid4()),
            status=SYNTHETIC_MESSAGE_STATUS,
            content=[InputTextContent(text=content)],
        )
    )

def convert_assistant_content(self, content: str) -> None:
    self.items.append(
        AssistantMessage(
            id=str(uuid.uuid4()),
            status=SYNTHETIC_MESSAGE_STATUS,
            content=[OutputTextContent(text=content, annotations=[])],
        )
    )
```

`SYNTHETIC_MESSAGE_STATUS` marks these as imported traces rather than live model outputs. The `content` field wraps text in `InputTextContent` or `OutputTextContent` -- AI GO's content types for user and assistant messages respectively.

### Tool calls

When an assistant (or user) message carries `tool_calls`, each one becomes a `FunctionCall` item:

```python
@staticmethod
def short_call_id(call_id: str) -> str:
    """Hash a long call_id to a 12-char hex string."""
    return hashlib.sha256(call_id.encode()).hexdigest()[:12]

def convert_tool_calls(self, tool_calls: list[dict[str, Any]], role: str) -> None:
    for tool_call in tool_calls:
        arguments = tool_call["arguments"]
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments)

        original_call_id = tool_call["id"]
        short_id = self.short_call_id(original_call_id)
        self.pending_calls[original_call_id] = role

        self.items.append(
            FunctionCall(
                id=short_id,
                call_id=short_id,
                name=tool_call["name"],
                arguments=arguments,
                status=FunctionCallStatus.completed,
                original_call_id=original_call_id,
                created_by=role,
            )
        )
```

Two things to note:

- **`created_by=role`**: Both user and assistant messages can carry tool calls in tau2bench. User-side calls are device operations (toggling airplane mode); assistant-side calls are backend operations (looking up accounts). The `created_by` field preserves this distinction.
- **`self.pending_calls[original_call_id] = role`**: Each call is registered so that when the tool result arrives, we can link it back to the right call and know who issued it.

The `short_call_id` helper hashes long provider-generated call IDs down to a 12-character hex string for use as the `call_id` in the trace.

### Tool results

Tool result messages become `FunctionCallOutput` items. The main challenge is matching each result to its originating call:

```python
def convert_tool_result(self, message: dict[str, Any]) -> None:
    content = message.get("content")
    original_call_id = message.get("id")

    if original_call_id is None:
        if not self.pending_calls:
            original_call_id = str(uuid.uuid4())
        else:
            # Pop the oldest pending call (FIFO).
            original_call_id = next(iter(self.pending_calls))

    created_by = self.pending_calls.pop(original_call_id, "assistant")

    short_id = self.short_call_id(original_call_id)
    output = content if isinstance(content, str) else json.dumps(content)
    is_error = message.get("error") is True

    self.items.append(
        FunctionCallOutput(
            id=short_id,
            call_id=short_id,
            output=output,
            status=FunctionCallOutputStatusEnum.incomplete
            if is_error
            else FunctionCallOutputStatusEnum.completed,
            original_call_id=original_call_id,
            created_by=created_by,
        )
    )
```

The ID-matching logic handles a real-world quirk: some providers omit the `id` field on tool result messages. When the `id` is present, we use it directly. When it is missing, we fall back to FIFO order -- the oldest pending call gets matched first. This works because chat APIs return tool results in the same order the calls were issued.

The `call_id` on the output matches the `call_id` on the corresponding `FunctionCall`, which is how AI GO links them together.

### The orchestrator

The `convert` method drives the dispatch:

```python
def convert(self, messages: list[dict[str, Any]]) -> list[TraceItem]:
    for message in messages:
        role = message["role"]
        content = message.get("content")
        tool_calls = message.get("tool_calls")

        if role == "user" and content is not None:
            self.convert_user_content(content)
        elif role == "assistant" and content is not None:
            self.convert_assistant_content(content)
        elif role == "tool":
            self.convert_tool_result(message)

        if tool_calls:
            self.convert_tool_calls(tool_calls, role)

    return self.items
```

Note that `tool_calls` is checked independently from `content` -- a single message can have both text and tool calls.

---

## Step 4: Build the dataset row

Each simulation becomes one row in the output dataset. The `convert_simulation` function wraps the converter and assembles the row:

```python
def convert_simulation(simulation: dict[str, Any]) -> dict[str, Any]:
    converter = Tau2BenchMessageConverter()
    trace_items = converter.convert(simulation["messages"])
    trace = Trace.from_items(items=trace_items)

    return {
        "trace": trace.model_dump(mode="json"),
        "simulation_id": simulation["id"],
        "task_id": simulation["task_id"],
        "trial": simulation["trial"],
        "agent_cost": simulation.get("agent_cost", 0.0),
        "user_cost": simulation.get("user_cost", 0.0),
    }
```

`Trace.from_items()` constructs an AI GO `Trace` from the list of items, and `model_dump(mode="json")` serializes it to a JSON-compatible dict.

The `trace` field is the only one AI GO requires. The remaining fields -- `simulation_id`, `task_id`, `trial`, `agent_cost`, `user_cost` -- are custom metadata columns. You can include whatever metadata is useful for your use case: model name, latency, token counts, experiment tags, etc. These columns appear alongside the trace in the AI GO UI and can be used for filtering and analysis.

---

## Step 5: Write the output files

With the converter and row builder in place, the remaining work is reading the input, converting every simulation, and writing two output files -- a `.jsonl` dataset and a `.yaml` dataset spec.

### Write the dataset

Each simulation becomes one JSON line:

```python
import json
from pathlib import Path

input_path = Path("tau2bench-log.json")

with open(input_path) as f:
    data = json.load(f)

simulations = data["simulations"]
lines = [json.dumps(convert_simulation(sim)) for sim in simulations]

jsonl_path = Path("tau2bench-traces.jsonl")
jsonl_path.write_text("\n".join(lines) + "\n")
```

Each line is one JSON object containing a `trace` field and any metadata columns. AI GO reads this as a dataset where each line is one sample.

### Create the dataset spec

Create a YAML file that tells AI GO where to find the data:

```yaml
key: tau2bench-traces
display_name: tau2bench-traces
source:
  type: local
  file_path: ./tau2bench-traces.jsonl
```

- `key` is a unique identifier (alphanumeric, hyphens, underscores)
- `display_name` is what appears in the UI
- `source.file_path` points to the `.jsonl` file relative to the YAML file
