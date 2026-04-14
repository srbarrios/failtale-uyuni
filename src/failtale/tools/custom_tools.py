import asyncio
import base64
import os
import litellm
from pydantic import BaseModel, Field
from crewai.tools import BaseTool, tool
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession


class SSHCommandInput(BaseModel):
    """Input schema for SSH command execution via ssh-mcp."""
    hostname: str = Field(..., description="Target hostname or IP address")
    username: str = Field(..., description="SSH username")
    private_key_path: str = Field(..., description="Path to the private SSH key")
    command: str = Field(..., description="The shell command to execute")


class SSHMCPTool(BaseTool):
    """
    Executes shell commands on remote Linux servers via the ssh-mcp protocol.

    This tool is a fallback for hosts that are not managed by Uyuni, or for
    direct SSH access to specific system data not available through the Uyuni API.

    Prerequisites:
    - npx is available in $PATH (Node.js/npm installed)
    - ssh-mcp is available via npm (installed on-demand via npx -y)
    - SSH private key exists at the specified path
    """
    name: str = "execute_remote_ssh_command"
    description: str = "Executes a shell command on a remote Linux server using the ssh-mcp protocol."
    args_schema: type[BaseModel] = SSHCommandInput

    def _run(self, hostname: str, username: str, private_key_path: str, command: str) -> str:
        """Execute a remote SSH command and return the output."""
        async def run_mcp_command():
            # Create ssh-mcp stdio server connection
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



@tool("Analyze Local Screenshot Tool")
def vision_tool(image_path: str) -> str:
    """
    Use this tool to read and extract text from local screenshot images. 
    Pass the relative or absolute file path to the image as the argument.

    This tool uses Google's Gemini model via litellm for vision analysis.
    It extracts visible UI errors, text, banners, and application state from screenshots.
    """
    # 1. Validate the image path before processing
    if not os.path.exists(image_path):
        return f"Error: Could not find image at path {image_path}"

    try:
        # 2. Read and encode the local image to Base64
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
        # 3. Send to Gemini with explicit vision payload structure
        response = litellm.completion(
            model="gemini/gemini-3-flash-preview", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": (
                                "You are a visual QA analyst. Review this screenshot and extract "
                                "any visible text, especially red error banners, form validation errors, "
                                "stack traces, and the page title/state. Focus on identifying visible "
                                "UI problems that would explain a test failure."
                            )
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


