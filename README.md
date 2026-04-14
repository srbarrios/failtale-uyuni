# FailTale: Automated Test Failure Reviewer

![fail-tale-image](https://github.com/user-attachments/assets/4d5f62f3-32bb-4c52-8258-7e802e190072)

Welcome to the FailTale project, powered by [crewAI](https://crewai.com). This project is a second Proof of Concept (PoC) for an intelligent Test Reviewer (First PoC [here](https://github.com/srbarrios/FailTale)). Its goal is to automate the collection of relevant debugging data from multiple product components when an automated test fails, analyze that data, and provide insights into the root cause.

By leveraging the powerful and flexible multi-agent framework provided by crewAI, FailTale enables AI agents to collaborate effectively on complex debugging tasks, maximizing their collective intelligence.

## Key Features

* **Targeted Collection:** Uses configuration files to define which logs and data are useful for each product component.
* **Agentic Collaboration:** Multiple AI agents take on specific roles (e.g., target identifier, data collector, root cause analyst) to intelligently process test failures.
* **Secure Data Retrieval:** Connects to hosts via SSH using minimal privileges and applies on-source filtering (`tail`, `grep`) to reduce data volume securely.
* **Local & Cloud LLM Integration:** Designed to interact with models from OpenAI, Gemini, or local models like Ollama.

## Architecture & Workflow

The FailTale is composed of multiple AI agents, each with unique roles, goals, and tools. Instead of a traditional linear script, the system operates as a collaborative workflow:

1. **Trigger:** The crew receives a test failure report and contextual data (defined via inputs in `src/failtale/main.py`).
2. **Targeting:** An agent analyzes the failure and identifies the specific hosts and components that need debugging.
3. **Execution & Collection:** Using custom tools, agents connect to the identified hosts and execute targeted, filtered commands to collect state data and logs.
4. **Analysis:** The collected data is analyzed by the crew to formulate root cause hints.
5. **Output:** The final insights are formatted and can be injected back into the client or test report.

These agents and their specific tasks are defined in `src/failtale/config/agents.yaml` and `src/failtale/config/tasks.yaml`.

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```
### Runtime prerequisites

- `GOOGLE_API_KEY` set in `.env` (Gemini is the default model provider).
- `docker` available in `PATH` (required by `UyuniMCPTool`).
- `npx` available in `PATH` (required by `SSHMCPTool`).
- Ollama running locally with `nomic-embed-text` pulled for knowledge embeddings.


### Uyuni TLS / Certificates

- If the Uyuni server uses an untrusted certificate by default, you can adjust `uyuni_mcp.ssl_verify` in `examples/uyuni/config.yaml`.
- `ssl_verify: true` (recommended in production) validates TLS certificates.
- `ssl_verify: false` disables TLS validation and prevents errors such as `CERTIFICATE_VERIFY_FAILED` in lab environments.

### Customizing

- Modify `src/failtale/config/agents.yaml` to define your agents.
- Modify `src/failtale/config/tasks.yaml` to define your tasks.
- Modify `src/failtale/crew.py` to add your own logic, tools and specific args.
- Modify `src/failtale/main.py` to add custom inputs for your agents and tasks.

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ crewai run
```

This command initializes FailTale Crew, assembling the agents and assigning them tasks as defined in your configuration.
