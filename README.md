# FailTale: Automated Test Failure Reviewer for Uyuni test environments

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

### Configure `.env` for a specific failed test

FailTale reads test failure inputs from environment variables in `src/failtale/main.py`.
To analyze one specific failure, point these values to failure-specific files:

```dotenv
# Existing provider key
GOOGLE_API_KEY=your_google_api_key

# Inputs consumed by get_inputs()
CONFIG_PATH=examples/uyuni/config.yaml
TEST_REPORT_PATH=tmp/failtale/2026-04-14_123045/report.txt
TEST_FAILURE_PATH=tmp/failtale/2026-04-14_123045/failure.txt
SCREENSHOT_PATH=tmp/failtale/2026-04-14_123045/screenshot.png
```

Notes:
- `CONFIG_PATH` must include exactly one host with `role: "server"`.
- Uyuni MCP connection env vars are derived automatically from the config file (`uyuni_mcp` + server host) before the crew is created.
- PDF knowledge source settings are also derived from config (`knowledge.pdf.file_paths` and `knowledge.pdf.collection_name`) with defaults to the Uyuni example docs.
- If any of these variables are missing, FailTale falls back to files in `examples/uyuni/`.

### `config.yaml` reference

FailTale loads `examples/uyuni/config.yaml` in `src/failtale/main.py` and uses it in two ways:

- **Direct/runtime usage in Python code:** values are read and transformed into env vars or crew inputs.
- **Agent-guidance usage:** full sections are stringified and passed to task prompts so the `data_collector` agent knows which commands/credentials to use.

#### 1) `ssh_defaults`

Example keys:
- `username`
- `private_key_path`
- `port`
- `connection_timeout`
- `command_timeout`

Usage:
- `main.py:get_inputs()` passes this section as `ssh_credentials` into `crew.kickoff(inputs=...)`.
- In `src/failtale/config/tasks.yaml` (`collect_data_task`), `{ssh_credentials}` is injected into the prompt so the agent can call `execute_remote_ssh_command` with the expected SSH settings.
- The Python code does **not** parse individual `ssh_defaults` keys itself; the agent consumes them from prompt context.

#### 2) `components`

Example keys:
- Role blocks such as `server`, `minion`, `proxy`, `build_host`
- Per-role `useful_data[]` with `description` and `command`

Usage:
- `main.py:get_inputs()` passes this section as `components_config` into crew inputs.
- `collect_data_task` injects `{components_config}` into the task instructions so the `data_collector` agent executes role-specific commands (Uyuni MCP first for `server`, SSH for fallback/other roles).
- As with `ssh_defaults`, Python code does not enforce or execute these commands directly; the agent uses them.

#### 3) `hosts`

Example keys per host:
- `hostname`
- `role`
- optional host credentials such as `user`, `password`

Usage:
- **Direct/runtime usage:** `_configure_uyuni_mcp_env()` requires exactly one host with `role: "server"` and reads that host's `hostname` to build `UYUNI_MCP_SERVER=<hostname>:<port>`.
- **Agent-guidance usage:** `get_inputs()` also passes full `hosts` as `hosts_inventory`, which is used by `select_hosts_task` prompt (`Available hosts in the environment: {hosts_inventory}`).

#### 4) `uyuni_mcp`

Keys used by code:
- `port` (default `443`)
- `uyuni_user` (default `admin`)
- `uyuni_pass` (default `admin`)
- `image_version` (default `latest`)
- `ssl_verify` (default `true`)

Usage:
- `_configure_uyuni_mcp_env()` maps these values to env vars:
  - `UYUNI_MCP_SERVER` (from server `hostname` + `port`)
  - `UYUNI_MCP_USER`
  - `UYUNI_MCP_PASS`
  - `UYUNI_MCP_IMAGE_VERSION`
  - `UYUNI_MCP_SSL_VERIFY`
- In `src/failtale/crew.py`, `data_collector()` reads those env vars to start the Uyuni MCP Docker server (`ghcr.io/uyuni-project/mcp-server-uyuni:<image_version>`).

#### 5) `knowledge.pdf`

Keys used by code:
- `file_paths`
- `collection_name`

Usage:
- `_configure_knowledge_env()` reads `knowledge.pdf.file_paths` and `knowledge.pdf.collection_name`.
- It exports `KNOWLEDGE_PDF_PATHS` and `KNOWLEDGE_PDF_COLLECTION_NAME`.
- In `crew.py`, `_build_pdf_knowledge_source()` reads those env vars and builds the `PDFKnowledgeSource` used by the crew knowledge system.

#### Notes about keys not currently consumed directly

- Host fields like `hosts[*].user` / `hosts[*].password` are not read directly by Python helper functions today; they are available to agents through `hosts_inventory` prompt context.
- For SSH execution, the actual tool call arguments are chosen by the agent at runtime based on task instructions plus `components_config` and `ssh_credentials`.

### Cucumber integration (`After` hook on scenario failure)

The example below captures failure context, writes files for FailTale, and runs analysis only when the scenario fails.

```ruby
# features/support/failtale_after_hook.rb
require "fileutils"
require "open3"
require "time"

After do |scenario|
  next unless scenario.failed?

  ts = Time.now.utc.strftime("%Y%m%d_%H%M%S")
  safe_name = scenario.name.gsub(/[^a-zA-Z0-9_-]/, "_")
  out_dir = File.join("tmp", "failtale", "#{ts}_#{safe_name}")
  FileUtils.mkdir_p(out_dir)

  report_path = File.join(out_dir, "test_report.txt")
  failure_path = File.join(out_dir, "test_failure.txt")
  screenshot_path = File.join(out_dir, "screenshot.png")

  File.write(report_path, <<~REPORT)
	Feature: #{scenario.feature.name}
	Scenario: #{scenario.name}
	Location: #{scenario.location}
	Status: failed
	Tags: #{scenario.source_tag_names.join(", ")}
  REPORT

  File.write(failure_path, scenario.exception&.message.to_s)

  # Replace this with your UI framework screenshot method.
  # Example for Capybara/Selenium:
  page.save_screenshot(screenshot_path) if defined?(page)

  env = {
	"CONFIG_PATH" => "examples/uyuni/config.yaml",
	"TEST_REPORT_PATH" => report_path,
	"TEST_FAILURE_PATH" => failure_path,
	"SCREENSHOT_PATH" => screenshot_path
  }

  stdout, stderr, status = Open3.capture3(env, "crewai", "run")

  puts "[FailTale] Output:\n#{stdout}"
  warn "[FailTale] Errors:\n#{stderr}" unless status.success?
end
```

If you prefer a pure `.env` workflow, write these same paths to `.env` before calling `crewai run`.


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
