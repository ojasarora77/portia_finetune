from dotenv import load_dotenv
from portia import (
    Config,
    LogLevel,
    Portia,
    StorageClass,
)
from portia.open_source_tools.registry import example_tool_registry

load_dotenv()

# Load the default config with specified storage and logging options
my_config = Config.from_default(
    storage_class=StorageClass.DISK, 
    storage_dir='demo_runs', # Amend this based on where you'd like your plans and plan runs saved!
    default_log_level=LogLevel.DEBUG,
    )

# Instantiate a Portia instance. Load it with the default config and with some example tools
portia = Portia(config=my_config, tools=example_tool_registry)

# Execute the plan run from the user query
output = portia.run('Which stock price grew faster in 2024, Amazon or Google?')

# Serialise into JSON and print the output
print(output.model_dump_json(indent=2))