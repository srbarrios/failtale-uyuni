import asyncio
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
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
