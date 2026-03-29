import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import VisionTool
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from failtale.tools import SSHMCPTool

#llm = LLM(
#    api_key="ollama",
#    model="openai/llama3.2-vision",
#    base_url="http://localhost:11434/v1"
#)

llm = LLM(
    api_key="your_api",
    model="gemini/gemini-3.1-flash-lite-preview"
)

user_prefs_source = TextFileKnowledgeSource(
    file_paths=["user_preference.txt"]
)

vision_tool = VisionTool()

@CrewBase
class FailTale():
    """FailTale Test Failure Analysis"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def host_selector(self) -> Agent:
        return Agent(
            llm=llm,
            config=self.agents_config['host_selector'],
            verbose=True
        )

    @agent
    def data_collector(self) -> Agent:
        return Agent(
            llm=llm,
            config=self.agents_config['data_collector'],
            tools=[SSHMCPTool()],
            verbose=True
        )

    @agent
    def screenshot_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['screenshot_analyzer'],
            tools=[vision_tool],
            llm=llm,
            verbose=True
        )

    @agent
    def failure_analyst(self) -> Agent:
        return Agent(
            llm=llm,
            config=self.agents_config['failure_analyst'],
            verbose=True
        )

    @task
    def select_hosts_task(self) -> Task:
        return Task(
            config=self.tasks_config['select_hosts_task']
        )

    @task
    def collect_data_task(self) -> Task:
        return Task(
            config=self.tasks_config['collect_data_task']
        )

    @task
    def analyze_screenshot_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_screenshot_task']
        )

    @task
    def analyze_failure_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_failure_task'],
            output_file='root_cause_hint.md'
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            knowledge_sources=[user_prefs_source],
            verbose=True,
        )
