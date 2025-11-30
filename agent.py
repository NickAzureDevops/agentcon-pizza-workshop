from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool
import os
from datetime import datetime
from tools import calculate_pizza_for_people
from dotenv import load_dotenv
load_dotenv()

# Initialize the project client
project_client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# 1. Create a vector store
openai_client = project_client.get_openai_client()
vector_store = openai_client.vector_stores.create(name="agentcon-pizza-vector-store")
print(f"Vector store created (id: {vector_store.id})")

# 2. Create a function to upload file to vector store
file_path = "workshop/documents/contoso_pizza_sofia.md"
with open(file_path, "rb") as f:
    uploaded_file = openai_client.vector_stores.files.upload_and_poll(
        vector_store_id=vector_store.id,
        file=f
    )
print(f"File uploaded to vector store (id: {uploaded_file.id})")
    
# 3. Upload file to vector store
file_path = "workshop/documents/contoso_pizza_sofia.md"
print(f"File uploaded to vector store (id: {uploaded_file.id})")

# Configure FileSearchTool
file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])

# Create the agent with FileSearchTool
agent = project_client.agents.create_version(
    agent_name=os.environ["AZURE_AI_FOUNDRY_AGENT_NAME"],
    definition=PromptAgentDefinition(
        model=os.environ["AZURE_AI_FOUNDRY_MODEL_DEPLOYMENT_NAME"],
        instructions=open("instructions.txt").read(),
        tools=[file_search_tool],  # Attach the FileSearchTool instance
        top_p=0.7,
        temperature=0.7,
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

# Create a conversation for multi-turn interactions
conversation = openai_client.conversations.create()
print(f"Created conversation (id: {conversation.id})")

while True:
    user_input = input("You: ")
    if user_input.lower() in ("exit", "quit"):
        break

    # Send user input to the agent
    response = openai_client.responses.create(
        conversation=conversation.id,  # Pass conversation ID for context
        extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        input=user_input,
    )
    print(f"Agent: {response.output_text}")

print("Conversation ended.")