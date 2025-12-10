from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool, FunctionTool, MCPTool
from openai.types.responses.response_input_param import FunctionCallOutput, McpApprovalResponse
from tools import calculate_pizza_for_people
from dotenv import load_dotenv
import os, json

load_dotenv()

# Function registry
FUNCTIONS = {"calculate_pizza_for_people": calculate_pizza_for_people}

def handle_tool_calls(response):
    """Handle function calls and MCP approvals."""
    inputs = []
    for item in response.output:
        if item.type == "function_call":
            func = FUNCTIONS.get(item.name)
            result = func(**json.loads(item.arguments)) if func else {"error": "Unknown"}
            inputs.append(FunctionCallOutput(call_id=item.call_id, 
            output=json.dumps({"result": result})))
        elif item.type == "mcp_approval_request":
            inputs.append(McpApprovalResponse(approve=True, approval_request_id=item.id))
    return inputs

# Initialize clients
project_client = AIProjectClient(endpoint=os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
openai_client = project_client.get_openai_client()

# Create vector store and upload file
vector_store = openai_client.vector_stores.create(name="pizza-vector-store")
with open("workshop/documents/contoso_pizza_sofia.md", "rb") as f:
    openai_client.vector_stores.files.upload_and_poll(vector_store_id=vector_store.id, file=f)

# Define tools
tools = [
    FileSearchTool(vector_store_ids=[vector_store.id]),
    FunctionTool(
        name="calculate_pizza_for_people",
        description="Calculate pizzas needed for a group",
        parameters={"type": "object", "properties": {
            "people_count": {"type": "integer", "description": "Number of people"},
            "appetite_level": {"type": "string", "enum": ["light", "normal", "heavy"], "description": "Appetite level"}
        }, "required": ["people_count", "appetite_level"], "additionalProperties": False},
        strict=True,
    ),
    MCPTool(
        server_label="contosopizza",
        server_url="https://ca-pizza-mcp-sc6u2typoxngc.graypond-9d6dd29c.eastus2.azurecontainerapps.io/sse",
        require_approval="always",
        allowed_tools=["get_pizzas", "get_pizza_by_id", "get_toppings", "get_topping_by_id", 
                       "get_topping_categories", "get_orders", "get_order_by_id", "place_order", "delete_order_by_id"],
        project_connection_id="contosopizza",
    ),
]

# Create agent
agent = project_client.agents.create_version(
    agent_name=os.environ["AZURE_AI_FOUNDRY_AGENT_NAME"],
    definition=PromptAgentDefinition(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        instructions=open("instructions.txt").read(),
        tools=tools,
    ),
)
print(f"Agent ready: {agent.name} v{agent.version}")

# Chat loop
conversation = openai_client.conversations.create()
print(f"Conversation created: {conversation.id}")

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
        print(f"  → Processing {len(inputs)} tool call(s)...")
        response = openai_client.responses.create(
            input=inputs,
            previous_response_id=response.id,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )

    print(f"Agent: {response.output_text}")
