# Tool Calling - Making Your Agent Act

In the previous chapters you gave your agent instructions and grounded it in your own data with File Search (RAG).  
Now, let's enable your agent to **take actions** by calling **tools** — small, well-defined functions your agent can invoke to perform tasks (e.g., calculations, lookups, API calls).

## What Are Tools (Function Calling)?

**Tools** let your agent call *your code* with structured inputs.  
When a user asks for something that matches a tool's purpose, the agent will select that tool, pass validated arguments, and use the tool's result to craft a final answer.

#### Why this matters:
- **Deterministic actions:** offload precise work (math, lookup, API call) to your code.
- **Safety & control:** you define what the agent is allowed to do.
- **Better UX:** the agent can provide concrete, actionable answers.


## Adding the Pizza Size Calculator

We'll add a tool that, given a **group size** and an **appetite level**, recommends how many and what size pizzas to order.

## Create the Function

Create a new file called **\`tools.py\`** and add the function below:

\`\`\`python
def calculate_pizza_for_people(people_count: int, appetite_level: str = "normal") -> str:
    """
    Calculate the number and size of pizzas needed for a group of people.
    
    Args:
        people_count (int): Number of people who will be eating
        appetite_level (str): Appetite level - "light", "normal", or "heavy" (default: "normal")
    
    Returns:
        str: Recommendation for pizza size and quantity
    """
    if people_count <= 0:
        return "Please provide a valid number of people (greater than 0)."
    
    appetite_multipliers = {
        "light": 0.7,
        "normal": 1.0,
        "heavy": 1.3
    }
    
    multiplier = appetite_multipliers.get(appetite_level.lower(), 1.0)
    adjusted_people = people_count * multiplier
    
    recommendations = []
    
    if adjusted_people <= 2:
        if adjusted_people <= 1:
            recommendations.append("1 Small pizza (perfect for 1-2 people)")
        else:
            recommendations.append("1 Medium pizza (great for 2-3 people)")
    elif adjusted_people <= 4:
        recommendations.append("1 Large pizza (serves 3-4 people)")
    elif adjusted_people <= 6:
        recommendations.append("1 Extra Large pizza (feeds 4-6 people)")
    elif adjusted_people <= 8:
        recommendations.append("2 Large pizzas (perfect for sharing)")
    elif adjusted_people <= 12:
        recommendations.append("2 Extra Large pizzas (great for groups)")
    else:
        extra_large_count = int(adjusted_people // 5)
        remainder = adjusted_people % 5
        
        pizza_list = []
        if extra_large_count > 0:
            pizza_list.append(f"{extra_large_count} Extra Large pizza{'s' if extra_large_count > 1 else ''}")
        
        if remainder > 2:
            pizza_list.append("1 Large pizza")
        elif remainder > 0:
            pizza_list.append("1 Medium pizza")
        
        recommendations.append(" + ".join(pizza_list))
    
    result = f"For {people_count} people with {appetite_level} appetite:\n"
    result += f"🍕 Recommendation: {recommendations[0]}\n"
    
    if appetite_level != "normal":
        result += f"(Adjusted for {appetite_level} appetite level)"
    
    return result
\`\`\`

## Update Your Imports

Update the imports in your \`agent.py\` to include the function and required modules:

\`\`\`python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool, FunctionTool
import os
import json
from tools import calculate_pizza_for_people
from dotenv import load_dotenv
from openai.types.responses.response_input_param import FunctionCallOutput
load_dotenv()
\`\`\`

## Create a Function Registry

Create a dictionary that maps function names to their Python implementations. This allows the agent to call your functions by name:

\`\`\`python
# Functions the agent can call
FUNCTIONS = {
    "calculate_pizza_for_people": calculate_pizza_for_people,
}
\`\`\`

## Create the Function Call Handler

Add a helper function to process function calls from the agent and return results:

\`\`\`python
def process_function_calls(response):
    """Process any function calls in the response and return results."""
    results = []
    for item in response.output:
        if item.type == "function_call":
            if item.name in FUNCTIONS:
                result = FUNCTIONS[item.name](**json.loads(item.arguments))
                results.append(FunctionCallOutput(
                    type="function_call_output",
                    call_id=item.call_id,
                    output=json.dumps({"result": result}),
                ))
            else:
                print(f"Warning: Unknown function call: {item.name}")
                results.append(FunctionCallOutput(
                    type="function_call_output",
                    call_id=item.call_id,
                    output=json.dumps({"error": f"Unknown function: {item.name}"}),
                ))
    return results
\`\`\`

## Define the FunctionTool with JSON Schema

Create a \`FunctionTool\` with a proper JSON schema that describes the function parameters. This tells the agent exactly what arguments to pass:

\`\`\`python
# Define the FunctionTool for pizza calculator
pizza_function_tool = FunctionTool(
    name="calculate_pizza_for_people",
    parameters={
        "type": "object",
        "properties": {
            "people_count": {
                "type": "integer",
                "description": "Number of people who will be eating",
            },
            "appetite_level": {
                "type": "string",
                "description": "Appetite level - 'light', 'normal', or 'heavy'. Use 'normal' if not specified.",
                "enum": ["light", "normal", "heavy"],
            },
        },
        "required": ["people_count", "appetite_level"],
        "additionalProperties": False,
    },
    description="Calculate the number and size of pizzas needed for a group of people.",
    strict=True,
)
\`\`\`

**Important:** When using \`strict=True\`, all properties must be listed in the \`required\` array.

## Add the Tool to Your Agent

Include the \`FunctionTool\` in the tools list when creating your agent:

\`\`\`python
# Create the agent with FileSearchTool and FunctionTool
agent = project_client.agents.create_version(
    agent_name=os.environ["AZURE_AI_FOUNDRY_AGENT_NAME"],
    definition=PromptAgentDefinition(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        instructions=open("instructions.txt").read(),
        tools=[file_search_tool, pizza_function_tool],
        top_p=0.7,
        temperature=0.7,
    ),
)
\`\`\`

## Handle Function Calls in the Conversation Loop

Update your conversation loop to process function calls and return results to the agent:

\`\`\`python
while True:
    user_input = input("You: ")
    if user_input.lower() in ("exit", "quit"):
        break

    # Send user input to the agent
    response = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        input=user_input,
    )

    # Keep processing function calls until agent returns text
    while True:
        function_results = process_function_calls(response)
        if not function_results:
            break  # No more function calls, agent has final response
        
        response = openai_client.responses.create(
            input=function_results,
            previous_response_id=response.id,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )

    print(f"Agent: {response.output_text}")
\`\`\`

**Key points:**
- The inner \`while True\` loop handles cases where the agent makes multiple function calls
- Use \`previous_response_id\` (not \`conversation\`) when sending function results back
- The loop continues until no more function calls are made

## Trying It Out

Run your agent and ask a question that should trigger the tool:

\`\`\`
We are 7 people with heavy appetite. What pizzas should we order?
\`\`\`

The agent should call the \`calculate_pizza_for_people\` tool, then reply with the recommendation it returns.

## Complete Code Example

Here's the complete \`agent.py\` with function calling:

\`\`\`python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool, FunctionTool
import os
import json
from tools import calculate_pizza_for_people
from dotenv import load_dotenv
from openai.types.responses.response_input_param import FunctionCallOutput
load_dotenv()

# Functions the agent can call
FUNCTIONS = {
    "calculate_pizza_for_people": calculate_pizza_for_people,
}

def process_function_calls(response):
    """Process any function calls in the response and return results."""
    results = []
    for item in response.output:
        if item.type == "function_call":
            if item.name in FUNCTIONS:
                result = FUNCTIONS[item.name](**json.loads(item.arguments))
                results.append(FunctionCallOutput(
                    type="function_call_output",
                    call_id=item.call_id,
                    output=json.dumps({"result": result}),
                ))
            else:
                print(f"Warning: Unknown function call: {item.name}")
                results.append(FunctionCallOutput(
                    type="function_call_output",
                    call_id=item.call_id,
                    output=json.dumps({"error": f"Unknown function: {item.name}"}),
                ))
    return results

# Initialize the project client
project_client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Get the OpenAI client
openai_client = project_client.get_openai_client()

# Create vector store and upload file (from previous chapter)
vector_store = openai_client.vector_stores.create(name="agentcon-pizza-vector-store")
file_path = "workshop/documents/contoso_pizza_sofia.md"
with open(file_path, "rb") as f:
    uploaded_file = openai_client.vector_stores.files.upload_and_poll(
        vector_store_id=vector_store.id,
        file=f
    )

# Configure FileSearchTool
file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])

# Define the FunctionTool for pizza calculator
pizza_function_tool = FunctionTool(
    name="calculate_pizza_for_people",
    parameters={
        "type": "object",
        "properties": {
            "people_count": {
                "type": "integer",
                "description": "Number of people who will be eating",
            },
            "appetite_level": {
                "type": "string",
                "description": "Appetite level - 'light', 'normal', or 'heavy'. Use 'normal' if not specified.",
                "enum": ["light", "normal", "heavy"],
            },
        },
        "required": ["people_count", "appetite_level"],
        "additionalProperties": False,
    },
    description="Calculate the number and size of pizzas needed for a group of people.",
    strict=True,
)

# Create the agent with both tools
agent = project_client.agents.create_version(
    agent_name=os.environ["AZURE_AI_FOUNDRY_AGENT_NAME"],
    definition=PromptAgentDefinition(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        instructions=open("instructions.txt").read(),
        tools=[file_search_tool, pizza_function_tool],
        top_p=0.7,
        temperature=0.7,
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai_client.conversations.create()
print(f"Created conversation (id: {conversation.id})")

while True:
    user_input = input("You: ")
    if user_input.lower() in ("exit", "quit"):
        break

    response = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        input=user_input,
    )

    # Process function calls
    while True:
        function_results = process_function_calls(response)
        if not function_results:
            break
        
        response = openai_client.responses.create(
            input=function_results,
            previous_response_id=response.id,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )

    print(f"Agent: {response.output_text}")

print("Conversation ended.")
\`\`\`

## Tips & Best Practices

- **JSON Schema:** Provide a clear schema with types, enums, and descriptions.
- **Strict mode:** Use \`strict=True\` and include all properties in \`required\` for reliable parsing.
- **Validate inputs:** Your tool should handle bad or missing data gracefully.
- **Keep tools single-purpose:** Small functions are easier for the agent to select and compose.
- **Use a registry:** The \`FUNCTIONS\` dict pattern makes it easy to add more tools.

## Recap

In this chapter you:
- Created a **pizza calculator** function in \`tools.py\`.
- Defined a **FunctionTool** with a JSON schema describing the parameters.
- Created a **function registry** (\`FUNCTIONS\` dict) to map names to implementations.
- Added a **function call handler** (\`process_function_calls\`) to execute tools.
- Updated the **conversation loop** to handle function calls and return results.
- Verified tool calling by prompting your agent.
