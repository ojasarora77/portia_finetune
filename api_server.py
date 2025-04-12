from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import os
import requests
import json
import re
from portia import Config, LogLevel, Portia, StorageClass
from portia.open_source_tools.registry import example_tool_registry

load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Venice API configuration
VENICE_API_KEY = os.getenv("VENICE_API_KEY")
VENICE_API_URL = "https://api.venice.ai/api/v1"

# Define request models with Pydantic
class ContractRequest(BaseModel):
    contract_code: str

class TranslateRequest(BaseModel):
    source_code: str
    target_language: str

class InsuranceRequest(BaseModel):
    contract_code: str
    tvl: float

class RecommendationRequest(BaseModel):
    contract_code: str
    analysis: dict

# Configure Portia
my_config = Config.from_default(
    storage_class=StorageClass.DISK, 
    storage_dir='blockchain_runs',
    default_log_level=LogLevel.DEBUG,
)

# Instantiate Portia
portia = Portia(config=my_config, tools=example_tool_registry)

# Function to call Venice API
def call_venice_api(messages, temperature=0.1, max_tokens=2000):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VENICE_API_KEY}"
    }
    
    payload = {
        "model": "default",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "venice_parameters": {
            "include_venice_system_prompt": False
        }
    }
    
    try:
        response = requests.post(f"{VENICE_API_URL}/chat/completions", 
                                headers=headers, 
                                json=payload)
        return response.json()
    except Exception as e:
        print(f"Error calling Venice API: {e}")
        return None

@app.get("/")
async def root():
    return {"message": "Portia API with Venice integration is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/analyze-contract")
async def analyze_contract(request: ContractRequest):
    print(f"Received contract code: {request.contract_code[:100]}...")
    
    try:
        # Try using Portia first for the plan generation
        analysis_plan = portia.plan(
            f"""Analyze this smart contract for security vulnerabilities:
            {request.contract_code}
            
            Provide a comprehensive security analysis with scores and details.
            """
        )
        
        # Now use Venice for the actual analysis
        venice_messages = [
            {
                "role": "system",
                "content": """You are a smart contract security analyzer. Analyze the following contract for vulnerabilities and security issues. 
                Respond with a JSON object that has the following structure:
                {
                  "overall_score": number from 0-100,
                  "complexity": {
                    "score": number from 0-100,
                    "details": array of strings with findings,
                    "risk_level": "Low", "Medium", or "High"
                  },
                  "vulnerabilities": {
                    "score": number from 0-100,
                    "details": array of strings describing vulnerabilities,
                    "risk_level": "Low", "Medium", or "High"
                  },
                  "upgradability": {
                    "score": number from 0-100,
                    "details": array of strings with findings,
                    "risk_level": "Low", "Medium", or "High"
                  },
                  "behavior": {
                    "score": number from 0-100,
                    "details": array of strings with findings,
                    "risk_level": "Low", "Medium", or "High"
                  }
                }"""
            },
            {
                "role": "user",
                "content": f"Analyze this smart contract:\n\n{request.contract_code}"
            }
        ]
        
        venice_response = call_venice_api(venice_messages, temperature=0.1, max_tokens=3000)
        
        # Check if Venice response is valid
        if venice_response and "choices" in venice_response and len(venice_response["choices"]) > 0:
            content = venice_response["choices"][0]["message"]["content"]
            
            # Extract JSON from content if needed
            try:
                json_match = re.search(r'```json\n([\s\S]*?)\n```', content) or re.search(r'```\n([\s\S]*?)\n```', content) or re.search(r'{[\s\S]*?}', content)
                if json_match:
                    json_str = json_match.group(0).replace('```json\n', '').replace('```\n', '').replace('```', '')
                    parsed_content = json.loads(json_str)
                else:
                    parsed_content = {"raw_response": content}
            except Exception as e:
                print(f"Error parsing JSON content: {e}")
                parsed_content = {"raw_response": content}
            
            # Return both Portia plan and Venice analysis
            return {
                "plan": analysis_plan.model_dump(),
                "results": {
                    "outputs": {
                        "final_output": {
                            "value": parsed_content,
                            "summary": content[:500] + "..." if len(content) > 500 else content
                        }
                    }
                },
                "venice_used": True
            }
        else:
            # Fallback to Portia if Venice fails
            plan_run = portia.run_plan(analysis_plan)
            return {
                "plan": analysis_plan.model_dump(),
                "results": plan_run.model_dump(),
                "venice_used": False
            }
    except Exception as e:
        print(f"Error in analyze_contract: {str(e)}")
        return {"error": str(e)}

@app.post("/translate-contract")
async def translate_contract(request: TranslateRequest):
    print(f"Translating contract to {request.target_language}")
    try:
        # Generate plan with Portia
        translation_plan = portia.plan(
            f"""Translate this smart contract from its original language to {request.target_language}:
            
            {request.source_code}
            
            Provide detailed comments explaining the key differences between the platforms
            and any important implementation details.
            """
        )
        
        # Try to use Venice API if available
        venice_messages = [
            {
                "role": "system",
                "content": f"""You are an expert in blockchain development across multiple platforms. 
                Translate the provided smart contract code into {request.target_language} with appropriate 
                equivalent functionality. Include comments explaining key differences between the platforms."""
            },
            {
                "role": "user",
                "content": f"Translate this smart contract to {request.target_language}:\n\n{request.source_code}"
            }
        ]
        
        try:
            venice_response = call_venice_api(venice_messages, temperature=0.1, max_tokens=3000)
            
            if venice_response and "choices" in venice_response and len(venice_response["choices"]) > 0:
                content = venice_response["choices"][0]["message"]["content"]
                
                return {
                    "plan": translation_plan.model_dump(),
                    "results": {
                        "outputs": {
                            "final_output": {
                                "value": content,
                                "summary": content[:500] + "..." if len(content) > 500 else content
                            }
                        }
                    },
                    "venice_used": True
                }
        except Exception as e:
            print(f"Venice API error: {e}. Falling back to Portia.")
        
        # Fallback to Portia if Venice fails
        plan_run = portia.run_plan(translation_plan)
        return {
            "plan": translation_plan.model_dump(),
            "results": plan_run.model_dump(),
            "venice_used": False
        }
    except Exception as e:
        print(f"Error translating contract: {str(e)}")
        return {"error": str(e)}

@app.post("/assess-insurance")
async def assess_insurance(request: InsuranceRequest):
    try:
        # Generate plan with Portia
        assessment_plan = portia.plan(
            f"""Assess the insurance risk for this smart contract with a Total Value Locked (TVL) of ${request.tvl}:
            
            {request.contract_code}
            
            Provide a comprehensive assessment including:
            1. Risk score from 0-100
            2. Premium percentage recommendation
            3. Coverage limit recommendation
            4. Detailed risk factors
            5. Overall risk level (Low, Medium, High)
            6. Policy recommendations
            7. Exclusions that should not be covered
            
            Format your response as a JSON structure with these fields.
            """
        )
        
        # Try to use Venice API if available
        venice_messages = [
            {
                "role": "system",
                "content": f"""You are an expert in smart contract risk assessment and insurance. 
                Analyze the provided contract to determine its risk level and appropriate insurance premium 
                recommendations. Consider factors like reentrancy, access control, overflow/underflow, and 
                overall code quality. For a contract with TVL (Total Value Locked) of ${request.tvl}, 
                recommend an appropriate premium percentage and coverage terms.
                
                Respond with a JSON object with this structure:
                {{
                  "risk_score": number from 0-100,
                  "premium_percentage": number (e.g., 2.5 for 2.5%),
                  "coverage_limit": string (e.g., "$1,000,000"),
                  "risk_factors": array of strings describing risk factors,
                  "risk_level": "Low", "Medium", or "High",
                  "policy_recommendations": array of strings with policy details,
                  "exclusions": array of strings listing what wouldn't be covered
                }}"""
            },
            {
                "role": "user",
                "content": f"Assess the insurance risk and premium for this smart contract with TVL of ${request.tvl}:\n\n{request.contract_code}"
            }
        ]
        
        try:
            venice_response = call_venice_api(venice_messages, temperature=0.1, max_tokens=3000)
            
            if venice_response and "choices" in venice_response and len(venice_response["choices"]) > 0:
                content = venice_response["choices"][0]["message"]["content"]
                
                # Try to parse JSON response
                try:
                    json_match = re.search(r'```json\n([\s\S]*?)\n```', content) or re.search(r'```\n([\s\S]*?)\n```', content) or re.search(r'{[\s\S]*?}', content)
                    if json_match:
                        json_str = json_match.group(0).replace('```json\n', '').replace('```\n', '').replace('```', '')
                        parsed_content = json.loads(json_str)
                    else:
                        parsed_content = {"raw_response": content}
                except Exception as e:
                    print(f"Error parsing JSON content: {e}")
                    parsed_content = {"raw_response": content}
                
                return {
                    "plan": assessment_plan.model_dump(),
                    "results": {
                        "outputs": {
                            "final_output": {
                                "value": parsed_content,
                                "summary": content[:500] + "..." if len(content) > 500 else content
                            }
                        }
                    },
                    "venice_used": True
                }
        except Exception as e:
            print(f"Venice API error: {e}. Falling back to Portia.")
        
        # Fallback to Portia if Venice fails
        plan_run = portia.run_plan(assessment_plan)
        return {
            "plan": assessment_plan.model_dump(),
            "results": plan_run.model_dump(),
            "venice_used": False
        }
    except Exception as e:
        print(f"Error assessing insurance: {str(e)}")
        return {"error": str(e)}

@app.post("/generate-recommendation")
async def generate_recommendation(request: RecommendationRequest):
    try:
        overall_score = request.analysis.get('overall_score', 75)
        risk_level = request.analysis.get('vulnerabilities', {}).get('risk_level', 'Medium')
        
        # Generate plan with Portia
        recommendation_plan = portia.plan(
            f"""Based on the following smart contract code and its security analysis, 
            generate recommendations for a tokenomics model:
            
            Contract Code:
            {request.contract_code[:1000]}... (truncated)
            
            Security Analysis:
            Overall Score: {overall_score}/100
            Risk Level: {risk_level}
            
            Please recommend:
            1. An appropriate token name
            2. A token symbol (3-5 characters)
            3. Initial supply
            4. Token distribution strategy
            5. Vesting schedules if applicable
            
            Format your response with clear sections for each recommendation.
            """
        )
        
        # Try to use Venice API if available
        venice_messages = [
            {
                "role": "system",
                "content": f"""You are an expert in smart contract analysis and tokenomics. Based on the provided smart contract 
                analysis, generate recommendations for a tokenomics model that would be appropriate for this contract.
                Include suggested name, symbol, initial supply, and distribution strategy. The contract has a security score
                of {overall_score}/100 and risk level of {risk_level}."""
            },
            {
                "role": "user",
                "content": f"Generate tokenomics recommendations for this contract:\n\n{request.contract_code[:1000]}...\n\nAnalysis: {json.dumps(request.analysis)}"
            }
        ]
        
        try:
            venice_response = call_venice_api(venice_messages, temperature=0.7, max_tokens=3000)
            
            if venice_response and "choices" in venice_response and len(venice_response["choices"]) > 0:
                content = venice_response["choices"][0]["message"]["content"]
                
                return {
                    "plan": recommendation_plan.model_dump(),
                    "results": {
                        "outputs": {
                            "final_output": {
                                "value": content,
                                "summary": content[:500] + "..." if len(content) > 500 else content
                            }
                        }
                    },
                    "venice_used": True
                }
        except Exception as e:
            print(f"Venice API error: {e}. Falling back to Portia.")
        
        # Fallback to Portia if Venice fails
        plan_run = portia.run_plan(recommendation_plan)
        return {
            "plan": recommendation_plan.model_dump(),
            "results": plan_run.model_dump(),
            "venice_used": False
        }
    except Exception as e:
        print(f"Error generating recommendation: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)