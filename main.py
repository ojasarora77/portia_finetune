from dotenv import load_dotenv
from portia import (
    Config,
    LogLevel,
    Portia,
    StorageClass,
)
from portia.open_source_tools.registry import example_tool_registry

# If you want to define custom tools, first check the available classes
# Try to inspect what's available in the portia package
import portia
print(dir(portia))  # This will print all available attributes in the portia module

load_dotenv()

# Configure Portia
my_config = Config.from_default(
    storage_class=StorageClass.DISK, 
    storage_dir='blockchain_runs',
    default_log_level=LogLevel.DEBUG,
)

# For now, let's just use the example tools
portia = Portia(config=my_config, tools=example_tool_registry)

# First, generate a plan for analyzing a smart contract
sample_contract = """
contract Test { 
    function transfer() public { 
        msg.sender.transfer(100); 
    } 
}
"""

contract_analysis_plan = portia.plan(
    f"Analyze this Solidity smart contract for security vulnerabilities: {sample_contract}"
)

# Print the plan to see the steps
print("Smart Contract Analysis Plan:")
print(contract_analysis_plan.model_dump_json(indent=2))

# Then execute the plan if you want
plan_run = portia.run_plan(contract_analysis_plan)

# Print the results
print("\nPlan Execution Results:")
print(plan_run.model_dump_json(indent=2))