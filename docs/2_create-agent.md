# Create Your First Agent  

In this chapter, we'll walk through the process of creating your very first AI agent using the **Azure AI Foundry Agent Service**.  
By the end, you'll have a simple agent running locally that you can interact with in real time.  

First switch back to the Github codespace environment you created earlier. Make sure the terminal pane is still opened on the **workshop** folder.

## Login to Azure  

Before you can use the Azure AI Foundry Agent Service, you need to sign in to your Azure subscription.  

Run the following command and follow the on-screen instructions. Use credentials that have access to your Azure AI Foundry resource:  

```shell
az login --use-device-code
```

---

## Install Required Packages  

Next, install the Python packages needed to work with Azure AI Foundry and manage environment variables:  

```shell
pip install azure-identity
pip install azure-ai-projects
pip install openai
pip install python-dotenv
```

---

### Create a `.env` File  

We'll store secrets (such as your project endpoint) in an environment file for security and flexibility.  

1. **Create a file named `.env` in the root of your project directory.**

2. **Add the following lines to the file:**

   ```env
   AZURE_AI_FOUNDRY_PROJECT_ENDPOINT="https://<your-foundry-resource>.services.ai.azure.com/api/projects/<your-project-name>"
   AZURE_AI_FOUNDRY_AGENT_NAME="my-pizza-agent"
   AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME="gpt-4o"
   ```

Replace the values with the actual values from your Azure AI Foundry project.

3. **Where to find your project endpoint:**

   - Go to the **Azure AI Foundry portal**
   - Navigate to your project
   - Click on **Overview**
   - The endpoint will be displayed on the homepage of your project

---

### 📝 Notes

- Make sure there are **no spaces** around the `=` sign in the `.env` file.

---

## Create a Basic Agent  

We'll now create a simple Python script that defines and runs an agent.  

- Start by creating a new file called: **`agent.py`** in the **workshop** folder

---

### Add Imports to `agent.py`  

These imports bring in the Azure SDK, environment handling, and helper classes:  

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
import os
from dotenv import load_dotenv
```

### Load the `.env` File  

Load environment variables into your script by adding this line to `agent.py`:  

```python
load_dotenv()
```

---

### Create an `AIProjectClient` Instance  

This client connects your script to the Azure AI Foundry service using the project endpoint and your Azure credentials.  

```python
project_client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
```

---

### Get the OpenAI Client  

The Azure AI Foundry SDK provides an OpenAI-compatible client for interacting with your agent:

```python
openai_client = project_client.get_openai_client()
```

---

### Create the Agent  

Now, let's create the agent itself using `PromptAgentDefinition`. This creates a versioned agent with the specified model and instructions.  

```python
agent = project_client.agents.create_version(
    agent_name=os.environ["AZURE_AI_FOUNDRY_AGENT_NAME"],
    definition=PromptAgentDefinition(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        instructions="You are a helpful assistant.",
        top_p=0.7,
        temperature=0.7,
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")
```

---

### Create a Conversation  

Agents interact within conversations. A conversation stores all messages exchanged between the user and the agent.  

```python
conversation = openai_client.conversations.create()
print(f"Created conversation (id: {conversation.id})")
```

---

### Chat Loop  

This loop lets you send messages to the agent. Type into the terminal, and the agent will respond.  

```python
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

    print(f"Agent: {response.output_text}")

print("Conversation ended.")
```

---

## Complete Formatted Code

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize the project client
project_client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Get the OpenAI client
openai_client = project_client.get_openai_client()

# Create the agent
agent = project_client.agents.create_version(
    agent_name=os.environ["AZURE_AI_FOUNDRY_AGENT_NAME"],
    definition=PromptAgentDefinition(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        instructions="You are a helpful assistant.",
        top_p=0.7,
        temperature=0.7,
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

# Create a conversation
conversation = openai_client.conversations.create()
print(f"Created conversation (id: {conversation.id})")

# Chat loop
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

    print(f"Agent: {response.output_text}")

print("Conversation ended.")
```

---

## Run the Agent  

Finally, run the Python script:  

```shell
python agent.py
```

You can now chat with your agent directly in the terminal. Type `exit` or `quit` to stop the conversation.  

---

## Debugging 

If you get an error that the principal does **not have permission** to create agents in your Azure AI Foundry project, you may be missing the required role assignment.

Here's how to fix it:

1. **Go to the Azure Portal**: [https://portal.azure.com](https://portal.azure.com)

2. **Navigate to your Azure AI Foundry resource**:
   - You can find it by searching for the name of your Foundry resource.

3. **Open the "Access Control (IAM)" panel**:
   - In the left-hand menu of the resource, click **Access Control (IAM)**.

4. **Click "Add role assignment"**:
   - Choose **Add → Add role assignment**
   - Select a role that includes the required permissions:
     - Recommended: **Cognitive Services Contributor** or **Azure AI Developer**

5. **Assign the role to your principal**:
   - Search for your user account or service principal
   - This might be a service principal, user, or managed identity depending on your setup.

6. **Save and confirm**:
   - Once assigned, wait a few minutes for the permission to propagate.
   - Retry the operation to create the agent.

---

## Recap  

In this chapter, you have:  

- Logged in to Azure  
- Set up environment variables in `.env`  
- Separated secrets from code  
- Created a basic agent with the Azure AI Foundry Agent Service using `PromptAgentDefinition`
- Used `create_version()` to create a versioned agent
- Started a conversation with the OpenAI-compatible client  
- Built a chat loop using `conversations.create()` and `responses.create()`
