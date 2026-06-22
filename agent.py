import os
import sys
from typing import Any

from llama_stack_client import LlamaStackClient


LLAMA_STACK_URL = os.getenv(
    "LLAMA_STACK_URL",
    "http://agent-llama-stack-service.wksp-user1.svc.cluster.local:8321",
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "maas-vllm-inference-1/qwen3-4b-instruct",
)

KUBERNETES_MCP_URL = os.getenv(
    "KUBERNETES_MCP_URL",
    "http://ocp-mcp-server.lls-demo.svc.cluster.local:8080/mcp",
)

SLACK_MCP_URL = os.getenv(
    "SLACK_MCP_URL",
    "http://slack-mcp-server.lls-demo.svc.cluster.local/mcp",
)


KUBERNETES_TOOL = {
    "type": "mcp",
    "server_label": "Kubernetes-MCP-Server",
    "server_url": KUBERNETES_MCP_URL,
}

SLACK_TOOL = {
    "type": "mcp",
    "server_label": "Slack-MCP-Server",
    "server_url": SLACK_MCP_URL,
}


SYSTEM_INSTRUCTIONS = """
You are an OpenShift operations agent.

You have access to a Kubernetes/OpenShift MCP server and a Slack MCP
server.

Rules:
- Use Kubernetes-MCP-Server to inspect namespaces, pods, deployments,
  services, routes, logs, events and other OpenShift resources.
- Use Slack-MCP-Server to inspect Slack channels or post Slack messages.
- When a request requires both systems, first retrieve the Kubernetes
  information and then post an accurate summary to Slack.
- Never invent Kubernetes results or claim that a Slack message was sent
  unless the corresponding MCP tool completed successfully.
- Keep final answers concise and state which actions were completed.
"""


def select_tools(prompt: str) -> list[dict[str, Any]]:
    """Select only the MCP servers relevant to the request."""

    text = prompt.lower()

    kubernetes_keywords = {
        "kubernetes",
        "openshift",
        "cluster",
        "namespace",
        "project",
        "pod",
        "pods",
        "deployment",
        "deployments",
        "service",
        "services",
        "route",
        "routes",
        "log",
        "logs",
        "event",
        "events",
        "nœud",
        "node",
        "nodes",
    }

    slack_keywords = {
        "slack",
        "channel",
        "canal",
        "message",
        "poste",
        "poster",
        "publie",
        "publier",
        "send",
        "post",
    }

    needs_kubernetes = any(word in text for word in kubernetes_keywords)
    needs_slack = any(word in text for word in slack_keywords)

    selected: list[dict[str, Any]] = []

    if needs_kubernetes:
        selected.append(KUBERNETES_TOOL)

    if needs_slack:
        selected.append(SLACK_TOOL)

    return selected


def verify_runtime(client: LlamaStackClient) -> None:
    """Verify that the configured model is registered in Llama Stack."""

    models = client.models.list()
    available_models = {model.identifier for model in models}

    print("Available models:")
    for model in models:
        print(f"  - {model.identifier} ({model.model_type})")

    if MODEL_NAME not in available_models:
        raise RuntimeError(
            f"Model {MODEL_NAME!r} is not registered in Llama Stack."
        )


def run_agent(client: LlamaStackClient, prompt: str) -> str:
    selected_tools = select_tools(prompt)

    request: dict[str, Any] = {
        "input": prompt,
        "model": MODEL_NAME,
        "instructions": SYSTEM_INSTRUCTIONS,
    }

    # Do not send an empty tools list for ordinary model questions.
    if selected_tools:
        request["tools"] = selected_tools

    labels = [tool["server_label"] for tool in selected_tools]
    print("Selected tools:", labels or ["none"])

    response = client.responses.create(**request)
    return response.output_text or "The agent returned no text output."


def main() -> None:
    client = LlamaStackClient(base_url=LLAMA_STACK_URL)

    try:
        verify_runtime(client)
    except Exception as error:
        print(f"Runtime verification failed: {error}")
        sys.exit(1)

    while True:
        prompt = input("\nAsk the agent> ").strip()

        if not prompt:
            continue

        if prompt.lower() in {"exit", "quit", "q"}:
            print("bye")
            break

        try:
            result = run_agent(client, prompt)
            print("\nagent>", result)

        except Exception as error:
            print("\nAgent request failed:")
            print(repr(error))

            response = getattr(error, "response", None)
            if response is not None:
                print("Server response:", response.text)


if __name__ == "__main__":
    main()