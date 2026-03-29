import os
import sys
import yaml
from dotenv import load_dotenv
from failtale.crew import FailTale

load_dotenv()

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
        'selected_hosts': "TO_BE_FILLED_BY_HOST_SELECTOR"
    }

def run():
    """
    Run the crew.
    """

    try:
        inputs = get_inputs()
        FailTale().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

def train():
    """
    Train the crew for a given number of iterations.
    """
    try:
        inputs = get_inputs()
        FailTale().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        inputs = get_inputs()
        FailTale().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    try:
        inputs = get_inputs()
        FailTale().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
