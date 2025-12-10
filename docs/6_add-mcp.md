# Integrating MCP (Model Context Protocol)

In earlier chapters, your agent learned to follow instructions, ground itself in your data (RAG/File Search), and call custom tools.  
In this final chapter, you'll connect your agent to an **MCP server** so it can use **external capabilities** (like live menus, toppings, and order management) over a standard protocol.


## What is MCP and why use it?

**MCP (Model Context Protocol)** is an open protocol for connecting AI models to tools, data sources, and services through interoperable **MCP servers**.  
Instead of tightly coupling your agent to each API, you connect **once** to an MCP server and gain access to all tools it exposes.

**Benefits:**
- **Interoperability:** a consistent way to expose tools from any service to any MCP‑aware agent.
- **Separation of concerns:** keep business logic and integrations in the server; keep the agent simple.
- **Security & governance:** centrally manage what tools are available and how they're approved.
- **Scalability:** add or update tools on the server without redeploying your agent code.


## Prerequisites

Before using MCP, you need to:

1. **Create a project connection** in the Azure AI Foundry portal for the MCP server
2. **Import the MCPTool** from the Azure AI Projects SDK


## Step 1: Create the MCP Connection in the Portal

1. Go to the [Microsoft Foundry portal](https://ai.azure.com) (make sure **New Foundry** toggle is ON)
2. Click **Operate** → **Admin** in the top navigation
3. Select your project from the list (e.g., `ai-agentcon-sofia`)
4. Click the **Connected resources** tab
5. Click **Add connection**
6. In the "Choose a connection" dialog, select **API Key** (Custom)
7. Configure:
   - **Name**: `contosopizza`
   - **API Key**: Enter a placeholder value (e.g., `none`)
8. Click **Continue** to create the connection


## Step 2: Update the Imports

Add `MCPTool` to your imports in `agent.py`:

\`\`\`python
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool, FunctionTool, MCPTool
\`\`\`

Also add the `McpApprovalResponse` import for handling MCP approvals:

\`\`\`python
from openai.types.responses.response_input_param import FunctionCallOutput, McpApprovalResponse
\`\`\`

Your imports should look like this:

\`\`\`python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool, FunctionTool, MCPTool
from openai.types.responses.response_input_param import FunctionCallOutput, McpApprovalResponse
from tools import calculate_pizza_for_people
from dotenv import load_dotenv
import os, json
\`\`\`


## The Contoso Pizza MCP Server

For Contoso Pizza, the MCP server exposes APIs for pizzas, toppings, and order management.  
We'll connect your agent to this server and **allow** a curated set of tools so the agent can fetch live information and place orders.


## Step 3: Add the MCP Tool

Add the `MCPTool` to your tools list in `agent.py`:

\`\`\`python
MCPTool(
    server_label="contosopizza",
    server_url="<!--@include: ./variables/mcp-url.md-->",
    require_approval="always",
    allowed_tools=["get_pizzas", "get_pizza_by_id", "get_toppings", "get_topping_by_id", 
                   "get_topping_categories", "get_orders", "get_order_by_id", "place_order", "delete_order_by_id"],
    project_connection_id="contosopizza",
),
\`\`\`

### MCPTool Parameters

| Parameter | Description |
|-----------|-------------|
| `server_label` | A friendly name for the MCP server (used in logs/telemetry) |
| `server_url` | The [MCP server endpoint](./pizza-mcp.md) |
| `require_approval` | Set to `"always"` to require approval for each tool call, or `"never"` to auto-approve |
| `allowed_tools` | A safety allowlist - only these tools are callable by the agent |
| `project_connection_id` | The name of the connection you created in Step 1 |


## Step 4: Handle MCP Approvals

When using `require_approval="always"`, you need to handle approval requests in your code. Update the `process_function_calls` function from the previous chapter to also handle MCP approvals:

\`\`\`python
def handle_tool_calls(response):
    """Handle function calls and MCP approvals."""
    inputs = []
    for item in response.output:
        if item.type == "function_call":
            func = FUNCTIONS.get(item.name)
            result = func(**json.loads(item.arguments)) if func else {"error": "Unknown"}
            inputs.append(FunctionCallOutput(call_id=item.call_id, output=json.dumps({"result": result})))
        elif item.type == "mcp_approval_request":
            inputs.append(McpApprovalResponse(approve=True, approval_request_id=item.id))
    return inputs
\`\`\`

Then update your chat loop to use this function:

\`\`\`python
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ("exit", "quit"):
        break

    response = openai_client.responses.create(
        conversation=conversation.id,
        input=user_input,
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
    )

    # Process tool calls until we get final text
    while (inputs := handle_tool_calls(response)):
        response = openai_client.responses.create(
            input=inputs,
            previous_response_id=response.id,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )

    print(f"Agent: {response.output_text}")
\`\`\`


## Get a User ID

To order pizza you need a **User ID**. You can get one by navigating to this URL:  
[<-az@include: ./variables/customer-registration.md-->](<-az@include: ./variables/customer-registration.md-->).

Next, add the following section to your `instructions.txt` file:

\`\`\`txt
## User details:
Name: <YOUR NAME>
UserId: <USER GUID>
\`\`\`

This should now look like:

\`\`\`
## Tools & Data Access
- Use the **Contoso Pizza Store Information Vector Store** to search get information about stores, like address and opening times.
    - **Tool:** \`file_search\`
    - Only return information found in the vector store or uploaded files.
    - If the information is ambiguous or not found, ask the user for clarification.

## User details:
Name: <YOUR NAME>
UserId: <USER GUID>

## Response
You will interact with users primarily through voice, so your responses should be natural, short and conversational. 
1. **Only use plain text**
2. No emoticons, No markup, No markdown, No html, only plain text.
3. Use short and conversational language.
\`\`\`

By adding this the agent will make orders using your userid.

::: tip
You can see your orders: 
[<-az@include: ./variables/pizza-dashboard.md-->](<-az@include: ./variables/pizza-dashboard.md-->).
:::


## Trying It Out

Ask your agent questions that should hit the MCP server tools, for example:

\`\`\`
Show me the available pizzas.
\`\`\`

\`\`\`
What is the price for a pizza hawai?
\`\`\`

\`\`\`
Place an order for 2 large pepperoni pizzas.
\`\`\`

The agent will call the allowed MCP tools, then summarize their responses in natural language—while still following your **instructions.txt** rules (tone, currency/time conversions, etc.).


## Best Practices

- **Principle of least privilege:** only allow tools your agent truly needs.
- **Observability:** log tool calls and handle failures gracefully.
- **Versioning:** pin server URLs or versions where possible to avoid breaking changes.
- **Human‑in‑the‑loop:** use `require_approval="always"` for sensitive actions like placing orders.
- **Resilience:** the agent should explain transient errors and suggest retries when remote tools fail.


## Recap

In this chapter, you:
- Learned what **MCP** is and why it's useful.
- Created a **project connection** for the MCP server in the Foundry portal.
- Configured an **MCPTool** to connect to the Contoso Pizza server.
- Added approval handling for MCP tool calls.
- Tested the setup with example prompts.

---

🎉 **You've completed the workshop!** Your agent now has instructions, knowledge (RAG), custom tools, and MCP‑powered capabilities.
