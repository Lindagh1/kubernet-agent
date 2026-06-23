import os
from typing import Any

import streamlit as st
from llama_stack_client import LlamaStackClient
from metrics import monitored, start_metrics_server

LLAMA_STACK_URL = os.environ["LLAMA_STACK_URL"]
MODEL_NAME = os.environ["MODEL_NAME"]
KUBERNETES_MCP_URL = os.environ["KUBERNETES_MCP_URL"]
SLACK_MCP_URL = os.environ["SLACK_MCP_URL"]

start_metrics_server()


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
You are an OpenShift AI operations assistant.

You have access to:

1. Kubernetes-MCP-Server
Use it for OpenShift and Kubernetes resources such as namespaces,
pods, deployments, services, routes, logs, events and cluster status.

2. Slack-MCP-Server
Use it for Slack channels and messages.

When a request requires both systems:
1. Retrieve the Kubernetes information.
2. Summarize it accurately.
3. Post the summary to Slack.

Never invent Kubernetes information.
Never claim a Slack message was sent unless the Slack tool succeeded.
Keep your answers concise and professional.
"""


def select_tools(prompt: str) -> list[dict[str, Any]]:
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
        "node",
        "nodes",
    }

    slack_keywords = {
        "slack",
        "channel",
        "canal",
        "message",
        "send",
        "post",
        "poste",
        "poster",
        "publie",
        "publier",
    }

    tools = []

    if any(keyword in text for keyword in kubernetes_keywords):
        tools.append(KUBERNETES_TOOL)

    if any(keyword in text for keyword in slack_keywords):
        tools.append(SLACK_TOOL)

    return tools


def build_conversation_prompt(user_prompt: str) -> str:
    history = st.session_state.messages[-8:]

    formatted_history = []

    for message in history:
        role = message["role"].upper()
        content = message["content"]
        formatted_history.append(f"{role}: {content}")

    formatted_history.append(f"USER: {user_prompt}")

    return "\n\n".join(formatted_history)


@monitored
def ask_agent(prompt: str) -> tuple[str, list[str]]:
    client = LlamaStackClient(base_url=LLAMA_STACK_URL)

    selected_tools = select_tools(prompt)
    full_prompt = build_conversation_prompt(prompt)

    request: dict[str, Any] = {
        "input": full_prompt,
        "model": MODEL_NAME,
        "instructions": SYSTEM_INSTRUCTIONS,
    }

    if selected_tools:
        request["tools"] = selected_tools

    response = client.responses.create(**request)

    tool_names = [
        tool["server_label"]
        for tool in selected_tools
    ]

    return response.output_text or "No response returned.", tool_names


st.set_page_config(
    page_title="OpenShift AI Agent",
    page_icon="🤖",
    layout="centered",
)

st.title("OpenShift AI Agent")
st.caption("Powered by Llama Stack, MaaS and MCP")

with st.sidebar:
    st.subheader("Runtime")

    st.code(LLAMA_STACK_URL)
    st.text(f"Model: {MODEL_NAME}")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("tools"):
            st.caption(
                "Tools: " + ", ".join(message["tools"])
            )


prompt = st.chat_input(
    "Ask about OpenShift, Kubernetes or Slack..."
)

if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is working..."):
            try:
                answer, tools_used = ask_agent(prompt)

                st.markdown(answer)

                if tools_used:
                    st.caption(
                        "Selected tools: " + ", ".join(tools_used)
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "tools": tools_used,
                    }
                )

            except Exception as error:
                error_message = f"Agent request failed: {error}"

                st.error(error_message)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )