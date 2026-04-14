import os
import sys
import yaml
from dotenv import load_dotenv

load_dotenv()


def _configure_uyuni_mcp_env(config: dict) -> None:
    """
    Extract the Uyuni MCP connection details from config and expose them as
    environment variables so that UyuniMCPTool can be initialised at crew
    construction time.

    The Uyuni server hostname is taken from the single host whose role is
    "server". Port and credentials come from the 'uyuni_mcp' section.
    """
    uyuni_mcp_cfg = config.get("uyuni_mcp", {})

    server_hosts = [h for h in config.get("hosts", []) if h.get("role") == "server"]
    if len(server_hosts) != 1:
        raise ValueError(
            "Config must define exactly one host with role 'server' for UyuniMCPTool "
            f"(found {len(server_hosts)})."
        )
    server_host = server_hosts[0]

    hostname = server_host["hostname"]
    port = uyuni_mcp_cfg.get("port", 443)
    ssl_verify = uyuni_mcp_cfg.get("ssl_verify", True)

    os.environ.setdefault("UYUNI_MCP_SERVER", f"{hostname}:{port}")
    os.environ.setdefault("UYUNI_MCP_USER", str(uyuni_mcp_cfg.get("uyuni_user", "admin")))
    os.environ.setdefault("UYUNI_MCP_PASS", str(uyuni_mcp_cfg.get("uyuni_pass", "admin")))
    os.environ.setdefault("UYUNI_MCP_IMAGE_VERSION", str(uyuni_mcp_cfg.get("image_version", "latest")))
    os.environ.setdefault("UYUNI_MCP_SSL_VERIFY", str(ssl_verify).lower())


def get_inputs():
    """Helper function to load files and prepare inputs based on environment variables."""

    # Read from environment variables, fallback to defaults
    config_path = os.getenv('CONFIG_PATH', 'examples/uyuni/config.yaml')
    test_report_path = os.getenv('TEST_REPORT_PATH', 'examples/uyuni/test_report.txt')
    test_failure_path = os.getenv('TEST_FAILURE_PATH', 'examples/uyuni/test_failure.txt')
    screenshot_path = os.getenv('SCREENSHOT_PATH', 'examples/uyuni/screenshot.png')

    # Load the YAML configuration
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Configure Uyuni MCP env vars from the loaded config
    _configure_uyuni_mcp_env(config)

    # Load the Test Report text file
    if not os.path.exists(test_report_path):
        raise FileNotFoundError(f"Test report file '{test_report_path}' not found.")
    with open(test_report_path, 'r') as f:
        test_report_content = f.read()

    # Load the Test Failure text file
    if not os.path.exists(test_failure_path):
        raise FileNotFoundError(f"Test failure file '{test_failure_path}' not found.")
    with open(test_failure_path, 'r') as f:
        test_failure_content = f.read()

    # Prepare the inputs dictionary for the Crew
    return {
        'test_report': test_report_content,
        'test_failure': test_failure_content,
        'screenshot_path': screenshot_path,
        'hosts_inventory': str(config.get('hosts', [])),
        'components_config': str(config.get('components', {})),
        'ssh_credentials': str(config.get('ssh_defaults', {})),
    }

def run():
    """
    Run the crew.
    """

    try:
        from failtale.crew import FailTale

        inputs = get_inputs()
        FailTale().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise RuntimeError("An error occurred while running the crew") from e

def train():
    """
    Train the crew for a given number of iterations.
    """
    try:
        from failtale.crew import FailTale

        inputs = get_inputs()
        FailTale().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise RuntimeError("An error occurred while training the crew") from e

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        from failtale.crew import FailTale

        FailTale().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise RuntimeError("An error occurred while replaying the crew") from e

def test():
    """
    Test the crew execution and returns the results.
    """
    try:
        from failtale.crew import FailTale

        inputs = get_inputs()
        FailTale().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise RuntimeError("An error occurred while testing the crew") from e
