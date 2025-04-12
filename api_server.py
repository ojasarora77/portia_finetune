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
    print(f"Received contract code: {request.contract_code[:100]}...")
    
    try:
        # Create a specific prompt that will generate the expected structure
        prompt = f"""
        Analyze this smart contract for security vulnerabilities and best practices:
        
        {request.contract_code}
        
        Generate a comprehensive security analysis with the following structure:
        - overall_score: A number between 0-100 representing the security score
        - complexity analysis with score, details array, and risk level
        - vulnerabilities analysis with score, details array, and risk level
        - upgradability analysis with score, details array, and risk level
        - behavior analysis with score, details array, and risk level
        
        Focus on important security aspects like reentrancy, overflow/underflow, access control, etc.
        """
        
        # Generate the plan for contract analysis
        analysis_plan = portia.plan(prompt)
        
        # Execute the plan
        plan_run = portia.run_plan(analysis_plan)
        
        # Return both the plan and results
        return {
            "plan": analysis_plan.model_dump(),
            "results": plan_run.model_dump()
        }
    except Exception as e:
        print(f"Error in analyze_contract: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)