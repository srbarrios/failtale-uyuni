import asyncio
import base64
import json
import os
import litellm
from pydantic import BaseModel, Field
from typing import Optional
from crewai.tools import BaseTool, tool
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

class SSHCommandInput(BaseModel):
    hostname: str = Field(..., description="Target hostname or IP address")
    username: str = Field(..., description="SSH username")
    private_key_path: str = Field(..., description="Path to the private SSH key")
    command: str = Field(..., description="The shell command to execute")

class SSHMCPTool(BaseTool):
    name: str = "execute_remote_ssh_command"
    description: str = "Executes a shell command on a remote Linux server using the ssh-mcp protocol."
    args_schema: type[BaseModel] = SSHCommandInput

    def _run(self, hostname: str, username: str, private_key_path: str, command: str) -> str:
        async def run_mcp_command():
            # Spin up the ssh-mcp standard IO server for the target host
            server_params = StdioServerParameters(
                command="npx",
                args=[
                    "-y", "ssh-mcp", "--", 
                    f"--host={hostname}", 
                    f"--user={username}", 
                    f"--key={private_key_path}", 
                    "--maxChars=none"
                ]
            )
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        # Execute the 'exec' tool exposed by ssh-mcp
                        result = await session.call_tool("exec", arguments={"command": command})
                        return result.content[0].text
            except Exception as e:
                return f"Failed to execute command on {hostname}: {str(e)}"
        
        return asyncio.run(run_mcp_command())


# ---------------------------------------------------------------------------
# Uyuni MCP Tool — calls tools exposed by the mcp-server-uyuni Docker image
# ---------------------------------------------------------------------------

class UyuniMCPInput(BaseModel):
    tool_name: str = Field(
        ...,
        description=(
            "Name of the Uyuni MCP tool to invoke. "
            "Pass the special value 'list_tools' to discover all tools "
            "available on the Uyuni MCP server before choosing one."
        )
    )
    tool_args: Optional[str] = Field(
        default="{}",
        description=(
            "Arguments for the tool as a JSON-encoded object string, e.g. "
            '\'{"sid": 1000010000}\'. Leave as \'{}\'  when calling \'list_tools\'.'
        )
    )


class UyuniMCPTool(BaseTool):
    name: str = "call_uyuni_mcp_tool"
    description: str = (
        "Calls any tool exposed by the Uyuni MCP server running on the Uyuni "
        "SUSE Manager host. Use this tool FIRST for any information about "
        "systems, activation keys, software channels, salt keys, patches, "
        "and other Uyuni-managed resources — it provides authoritative data "
        "straight from the Uyuni API. "
        "Start with tool_name='list_tools' to discover what is available, "
        "then call the relevant tool with the required tool_args."
    )
    args_schema: type[BaseModel] = UyuniMCPInput

    # Connection details — injected at construction time from env vars
    uyuni_server: str = Field(
        default_factory=lambda: os.getenv("UYUNI_MCP_SERVER", "")
    )
    uyuni_user: str = Field(
        default_factory=lambda: os.getenv("UYUNI_MCP_USER", "admin")
    )
    uyuni_pass: str = Field(
        default_factory=lambda: os.getenv("UYUNI_MCP_PASS", "admin")
    )
    image_version: str = Field(
        default_factory=lambda: os.getenv("UYUNI_MCP_IMAGE_VERSION", "latest")
    )
    ssl_verify: str = Field(
        default_factory=lambda: os.getenv("UYUNI_MCP_SSL_VERIFY", "true")
    )

    def _run(self, tool_name: str, tool_args: Optional[str] = "{}") -> str:
        async def run_uyuni_mcp():
            server_params = StdioServerParameters(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "-e", f"UYUNI_SERVER={self.uyuni_server}",
                    "-e", f"UYUNI_USER={self.uyuni_user}",
                    "-e", f"UYUNI_PASS={self.uyuni_pass}",
                    "-e", f"UYUNI_MCP_SSL_VERIFY={self.ssl_verify}",
                    f"ghcr.io/uyuni-project/mcp-server-uyuni:{self.image_version}",
                ],
            )
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        # Special case: let the agent discover available tools
                        if tool_name == "list_tools":
                            tools_response = await session.list_tools()
                            tools_info = [
                                {
                                    "name": t.name,
                                    "description": t.description,
                                    "inputSchema": t.inputSchema,
                                }
                                for t in tools_response.tools
                            ]
                            return json.dumps(tools_info, indent=2)

                        # Parse tool_args from JSON string to dict
                        try:
                            arguments = json.loads(tool_args or "{}")
                        except json.JSONDecodeError as e:
                            return f"Invalid tool_args JSON: {e}"

                        result = await session.call_tool(tool_name, arguments=arguments)
                        # Concatenate all text content blocks
                        texts = [
                            block.text
                            for block in result.content
                            if hasattr(block, "text")
                        ]
                        return "\n".join(texts) if texts else "(no output)"
            except Exception as e:
                return f"UyuniMCPTool failed ({self.uyuni_server}): {str(e)}"

        return asyncio.run(run_uyuni_mcp())


@tool("Analyze Local Screenshot Tool")
def vision_tool(image_path: str) -> str:
    """
    Use this tool to read and extract text from local screenshot images. 
    Pass the relative or absolute file path to the image as the argument.
    """
    # 1. Catch bad paths before they hit the LLM
    if not os.path.exists(image_path):
        return f"Error: Could not find image at path {image_path}"

    try:
        # 2. Read and encode the local image to Base64
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
        # 3. Manually format the payload so LiteLLM/Gemini can't misunderstand it
        response = litellm.completion(
            model="gemini/gemini-3-flash-preview", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "You are a visual QA analyst. Review this screenshot and extract any visible text, especially red error banners, form validation errors, and the page title/state."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Vision processing failed: {str(e)}"
