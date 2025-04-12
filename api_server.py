from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from portia import Config, LogLevel, Portia, StorageClass
from portia.open_source_tools.registry import example_tool_registry

load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your React app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define a request model
class ContractRequest(BaseModel):
    contract_code: str

# Configure Portia
my_config = Config.from_default(
    storage_class=StorageClass.DISK, 
    storage_dir='blockchain_runs',
    default_log_level=LogLevel.DEBUG,
)

# Instantiate Portia
portia = Portia(config=my_config, tools=example_tool_registry)

@app.get("/")
async def root():
    return {"message": "Portia API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/analyze-contract")
async def analyze_contract(request: ContractRequest):
    try:
        # Create a clear prompt that requests structured JSON output
        prompt = f"""
        Analyze this smart contract for security vulnerabilities:

        {request.contract_code}

        Respond with a structured JSON object containing:
        1. overall_score: A number between 0-100
        2. complexity: Object with score (0-100), details array with at least 3 findings, and risk_level
        3. vulnerabilities: Object with score (0-100), details array with at least 3 findings, and risk_level
        4. upgradability: Object with score (0-100), details array with at least 3 findings, and risk_level
        5. behavior: Object with score (0-100), details array with at least 3 findings, and risk_level
        6. recommendations: Array of specific recommendations

        Format your response as a single JSON object.
        """
        
        # Generate and run the plan
        analysis_plan = portia.plan(prompt)
        plan_run = portia.run_plan(analysis_plan)
        
        # Extract the result and try to process it as JSON
        final_output = plan_run.outputs.final_output.value if hasattr(plan_run, 'outputs') and plan_run.outputs.final_output else None
        
        if isinstance(final_output, str):
            # Try to extract JSON from the string response
            import re
            import json
            
            # Look for JSON patterns in the response
            json_match = re.search(r'({[\s\S]*})', final_output)
            if json_match:
                try:
                    # Parse the JSON found in the response
                    structured_data = json.loads(json_match.group(1))
                    return {
                        "plan": analysis_plan.model_dump(),
                        "results": plan_run.model_dump(),
                        "structured_analysis": structured_data
                    }
                except json.JSONDecodeError:
                    pass
        
        # If we couldn't extract structured data, return the raw results
        return {
            "plan": analysis_plan.model_dump(),
            "results": plan_run.model_dump()
        }
        
    except Exception as e:
        print(f"Error in analyze_contract: {str(e)}")
        return {"error": str(e)}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)