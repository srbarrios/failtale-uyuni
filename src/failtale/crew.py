import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.mcp import MCPServerStdio
# from crewai.mcp.filters import create_static_tool_filter  # Uncomment to restrict specific Uyuni tools
# Built-in VisionTool commented because doesn't work properly through Gemini
#from crewai_tools import VisionTool
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
from failtale.tools import SSHMCPTool
from failtale.tools.custom_tools import vision_tool

#llm = LLM(
#    api_key="ollama",
#    model="openai/llama3.2-vision",
#    base_url="http://localhost:11434/v1"
#)

gemini_llm = LLM(
    model="gemini/gemini-3-flash-preview", 
    api_key=os.getenv("GOOGLE_API_KEY")
)

user_prefs_source = TextFileKnowledgeSource(
    file_paths=["user_preference.txt"],
    collection_name="ollama_user_prefs"
)

#TODO: Parametrize this content. For now I'm trying with an example
pdf_source = PDFKnowledgeSource(
    file_paths=[
        "examples/uyuni/uyuni_administration_guide.pdf"
    ],
    collection_name="ollama_uyuni_docs"
)

# vision_tool = VisionTool(llm=gemini_llm)

@CrewBase
class FailTale():
    """FailTale Test Failure Analysis"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def host_selector(self) -> Agent:
        return Agent(
            config=self.agents_config['host_selector'],  # type: ignore[index]
            llm=gemini_llm,
            verbose=True
        )

    @agent
    def data_collector(self) -> Agent:
        """
        System Investigator agent with MCP integration.

        Uses two MCP servers:
        1. Uyuni MCP server (via Docker) for authoritative API data on the Uyuni server host
        2. SSH MCP server (via npx) as fallback for other hosts and raw system data

        The Uyuni server connection is configured via environment variables set in main.py
        before crew construction. SSH parameters are passed dynamically during task execution.
        """
        # Uyuni MCP server configuration (Docker-based).
        # Values are resolved at agent construction time from env vars previously
        # set by main.py::_configure_uyuni_mcp_env(). Using f-strings here because
        # Python list args are NOT processed by a shell, so ${VAR} syntax would be
        # passed literally to Docker — os.getenv() is the correct approach.
        uyuni_mcp = MCPServerStdio(
            command="docker",
            args=[
                "run", "-i", "--rm",
                "-e", f"UYUNI_SERVER={os.getenv('UYUNI_MCP_SERVER', '')}",
                "-e", f"UYUNI_USER={os.getenv('UYUNI_MCP_USER', 'admin')}",
                "-e", f"UYUNI_PASS={os.getenv('UYUNI_MCP_PASS', 'admin')}",
                "-e", f"UYUNI_MCP_SSL_VERIFY={os.getenv('UYUNI_MCP_SSL_VERIFY', 'true')}",
                f"ghcr.io/uyuni-project/mcp-server-uyuni:{os.getenv('UYUNI_MCP_IMAGE_VERSION', 'latest')}",
            ],
            cache_tools_list=True,
        )

        return Agent(
            config=self.agents_config['data_collector'],  # type: ignore[index]
            llm=gemini_llm,
            mcps=[
                # Uyuni MCP listed FIRST (preferred) for Uyuni server node
                uyuni_mcp,
            ],
            # SSH tool as fallback for non-server roles (minion, proxy, build_host, etc.)
            tools=[SSHMCPTool()],
            verbose=True
        )

    @agent
    def screenshot_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['screenshot_analyzer'],  # type: ignore[index]
            tools=[vision_tool],
            llm=gemini_llm,
            verbose=True
        )

    @agent
    def failure_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['failure_analyst'],  # type: ignore[index]
            llm=gemini_llm,
            verbose=True
        )

    @task
    def select_hosts_task(self) -> Task:
        return Task(
            config=self.tasks_config['select_hosts_task']  # type: ignore[index]
        )

    @task
    def collect_data_task(self) -> Task:
        return Task(
            config=self.tasks_config['collect_data_task'],  # type: ignore[index]
            context=[self.select_hosts_task()],
        )

    @task
    def analyze_screenshot_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_screenshot_task']  # type: ignore[index]
        )

    @task
    def analyze_failure_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_failure_task'],  # type: ignore[index]
            output_file='root_cause_hint.md'
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            knowledge_sources=[user_prefs_source, pdf_source],
            embedder={
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text"
                }
            },
            llm=gemini_llm,
            verbose=True,
        )
