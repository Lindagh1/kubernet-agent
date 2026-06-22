import os
import sys
from llama_stack_client import LlamaStackClient

# Variables injectées dynamiquement par le déploiement OpenShift
LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
VECTOR_STORE_NAME = os.getenv("VECTOR_STORE_NAME")

if not all([LLAMA_STACK_URL, MODEL_NAME, VECTOR_STORE_NAME]):
    print("Erreur : Configuration MaaS manquante.")
    sys.exit(1)

client = LlamaStackClient(base_url=LLAMA_STACK_URL)

config = {
    "input": "Post a message to the #rh1-2026 channel: 'Hi from linda'.",
    "model": MODEL_NAME,
    "instructions": "You are a helpful AI assistant.",
    "tools": [
        {
          "type": "mcp",
          "server_label": "Slack-MCP-Server",
          "server_url": "http://slack-mcp-server.lls-demo.svc.cluster.local/mcp"
        }
    ]
}

response = client.responses.create(**config)
print("agent>", response.output_text)