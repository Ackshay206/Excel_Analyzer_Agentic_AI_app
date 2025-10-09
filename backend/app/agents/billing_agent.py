from typing import Dict, Any, Optional
import pandas as pd
import logging
from pathlib import Path
import time
import hashlib
import io

from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_experimental.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent
from langchain.tools import Tool
from langchain import hub

from app.config import settings


logger = logging.getLogger(__name__)


class BillingAgent:
    """LangChain-based agent for analyzing billing Excel files"""
    
    def __init__(self):
        # Don't create default LLM here - create it lazily when needed
        self._default_llm = None
        self.loaded_files = {}
        
        # Cache for agent executors per session/api_key combination
        self._agent_cache = {}
        
        self._initialize_instructions()

    @property
    def default_llm(self) -> ChatOpenAI:
        """Lazily create default LLM only when accessed and env key exists"""
        if self._default_llm is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError(
                    "No OpenAI API key available. Either set OPENAI_API_KEY in .env "
                    "or provide an API key via the set-api-key endpoint."
                )
            self._default_llm = ChatOpenAI(
                temperature=0, 
                model=settings.OPENAI_MODEL,
                openai_api_key=settings.OPENAI_API_KEY
            )
        return self._default_llm

    def _get_llm(self, api_key: Optional[str] = None) -> ChatOpenAI:
        """Get LLM instance with optional custom API key"""
        if api_key:
            logger.info("Using custom API key for this query")
            return ChatOpenAI(
                temperature=0, 
                model=settings.OPENAI_MODEL,
                openai_api_key=api_key
            )
        
        # Try to use default LLM (will fail if no env key is set)
        try:
            return self.default_llm
        except ValueError as e:
            raise ValueError(
                "No API key available. Please provide an API key using the "
                "set-api-key endpoint or set OPENAI_API_KEY in your .env file."
            ) from e
    
    def _get_cache_key(self, api_key: Optional[str], file_name: Optional[str]) -> str:
        """
        Generate a cache key based on API key and file selection.
        
        HOW THIS CREATES SEPARATE SESSIONS:
        - Each unique API key gets a different key_hash
        - This means User A (with api_key_A) and User B (with api_key_B) 
          will have SEPARATE agent executors in the cache
        - But they all share the same loaded_files (Excel data)
        
        Example:
        - User A with sk-AAA... -> cache key: "abc12345_all_files"
        - User B with sk-BBB... -> cache key: "def67890_all_files"
        - Both use the same self.loaded_files dictionary
        """
        # Create a hash of the API key for the cache key
        if api_key:
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        else:
            key_hash = "default"
        
        # Include file selection in cache key
        file_key = file_name if file_name else "all_files"
        
        return f"{key_hash}_{file_key}"
    
    def _initialize_instructions(self):
        """Initialize the ReAct agent instructions"""
        self.instructions = """
You are a ReAct agent capable of using tools to answer user queries about billing details.
We have multiple Excel files:
- Each file contains billing data in a sheet named "Billing Invoice (BI) Detail".
- The files may have different structures and columns.

Whenever a user's question requires analyzing or retrieving information
from this file, you should use the appropriate tool.
 
Here is how you should structure your reasoning and responses:
 
- **Thought**:
  Provide your internal, step-by-step reasoning about how to approach the user's question
  (not shown to the user).
 
- **Action**:
  If you need to consult the data, specify the name of the tool
  (example "Excel Agent - August").
 
- **Action Input**:
  Provide the specific query or instructions you want to pass into the tool.
 
- **Observation**:
  The tool's response to your query. This will inform your next steps.
 
- **Final Answer**:
  The concise, direct answer you provide to the user after integrating
  all relevant information and your reasoning.
 
Remember:
1. Think carefully, plan your steps, and then provide the best final answer.
2. IMPORTANT: Do not modify, transform, or reformat any numerical values in any way. Return the exact raw values as they are found in the data. Do not assume values are in thousands or apply any scaling.
3. IMPORTANT: Always apply the tools on the data in the excel files. Do not make assumptions or fabricate data.
"""

    def load_excel_file(self, file_stream: io.BytesIO, filename: str, sheet_name: str = "Billing Invoice (BI) Detail") -> str:
        """Load an Excel file from a BytesIO stream (S3 download)"""
        try:
            # Generate a tool name based on the file
            file_name = Path(filename).stem
            tool_name = f"Excel Agent - {file_name}"
            
            # Load the Excel file from stream
            df = pd.read_excel(file_stream, sheet_name=sheet_name)
            logger.info(f"Loaded Excel file: {filename} with {len(df)} rows")
            
            # Store only the DataFrame and metadata (NO agent creation here)
            self.loaded_files[tool_name] = {
                "file_path": filename,  # Just the filename now
                "sheet_name": sheet_name,
                "dataframe": df,
                "tool_description": f"""Use this tool to analyze the Excel file: {filename}
    Sheet: {sheet_name}
    Provide your query for data analysis."""
            }
            
            # Invalidate cache since files changed
            self._invalidate_cache()
            
            logger.info(f"Successfully loaded file data for: {tool_name}")
            return tool_name
            
        except Exception as e:
            logger.error(f"Error loading Excel file {filename}: {str(e)}")
            raise

    def _invalidate_cache(self):
        """Invalidate all cached agent executors (called when files change)"""
        self._agent_cache.clear()
        logger.info("Agent executor cache cleared due to file changes")

    def _get_or_create_agent_executor(
        self, 
        llm: ChatOpenAI, 
        file_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> AgentExecutor:
        """Get cached agent executor or create new one if not exists"""
        
        # Generate cache key (unique per API key)
        cache_key = self._get_cache_key(api_key, file_name)
        
        # Check if we have a cached executor
        if cache_key in self._agent_cache:
            logger.info(f"Using cached agent executor for key: {cache_key}")
            return self._agent_cache[cache_key]
        
        # Create new agent executor
        logger.info(f"Creating new agent executor for key: {cache_key}")
        
        # Determine which files to create tools for
        if file_name:
            # Filter by file name
            files_to_process = {
                name: data for name, data in self.loaded_files.items()
                if file_name.lower() in data["file_path"].lower()
            }
            
            if not files_to_process:
                raise ValueError(f"No loaded file matches: {file_name}")
        else:
            # Use all loaded files (SHARED data)
            files_to_process = self.loaded_files
        
        # Create pandas agent tools for each file
        tools = []
        for tool_name, file_data in files_to_process.items():
            # Create pandas agent with the specified LLM (user-specific)
            excel_agent_executor = create_pandas_dataframe_agent(
                llm=llm,
                df=file_data["dataframe"],
                verbose=True,
                allow_dangerous_code=True,
            )
            
            # Wrap in a Tool
            tool = Tool(
                name=tool_name,
                func=excel_agent_executor.invoke,
                description=file_data["tool_description"]
            )
            
            tools.append(tool)
            logger.info(f"Created pandas agent tool: {tool_name}")
        
        # Create the ReAct agent executor
        base_prompt = hub.pull("langchain-ai/react-agent-template")
        prompt = base_prompt.partial(instructions=self.instructions)
        
        grand_agent = create_react_agent(
            prompt=prompt,
            llm=llm,
            tools=tools,
        )
        
        agent_executor = AgentExecutor(
            agent=grand_agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=60,
            return_intermediate_steps=True
        )
        
        # Cache the executor (user-specific cache)
        self._agent_cache[cache_key] = agent_executor
        logger.info(f"Cached new agent executor with key: {cache_key}")
        
        return agent_executor

    def invalidate_session_cache(self, api_key: Optional[str] = None):
        """
        Invalidate cache for a specific session (called when API key is removed).
        If api_key is None, invalidates default session cache.
        """
        keys_to_remove = []
        
        if api_key:
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        else:
            key_hash = "default"
        
        # Find all cache entries for this session
        for cache_key in self._agent_cache.keys():
            if cache_key.startswith(key_hash):
                keys_to_remove.append(cache_key)
        
        # Remove them
        for key in keys_to_remove:
            del self._agent_cache[key]
            logger.info(f"Removed cached agent executor: {key}")

    async def query(
        self, 
        question: str, 
        file_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a query using cached or new agent executor"""
        start_time = time.time()
        
        try:
            # If no files loaded, try to load default file
            if not self.loaded_files:
                default_file = Path(settings.DATA_DIRECTORY)
                if default_file.exists():
                    self.load_excel_file(str(default_file))
            
            # If still no files, raise error
            if not self.loaded_files:
                raise ValueError("No Excel files loaded. Please upload a file first.")
            
            # Get LLM with optional custom API key
            try:
                llm = self._get_llm(api_key)
            except ValueError as e:
                # No API key available
                return {
                    "answer": str(e),
                    "reasoning": "No API key configured",
                    "execution_time": 0,
                    "tools_used": 0
                }
            
            # Get or create cached agent executor (user-specific)
            agent_executor = self._get_or_create_agent_executor(llm, file_name, api_key)
            
            # Execute the query (this is the only heavy operation now)
            logger.info(f"Processing query: {question}")
            result = agent_executor.invoke({"input": question})

            execution_time = time.time() - start_time

            # Extract reasoning as a single string
            reasoning_text = ""
            
            if "intermediate_steps" in result and result["intermediate_steps"]:
                for i, step in enumerate(result["intermediate_steps"], 1):
                    # step is a tuple: (AgentAction, observation)
                    agent_action, observation = step
                    
                    # Extract from AgentAction.log
                    if hasattr(agent_action, 'log') and agent_action.log:
                        log = agent_action.log
                        
                        # Add each line that starts with Thought: or Action:
                        for line in log.split('\n'):
                            line = line.strip()
                            if line.startswith('Thought:') or line.startswith('Action:'):
                                reasoning_text += line + '\n'
                        
                        reasoning_text += '\n'
            
            return {
                "answer": result.get("output", "No answer provided"),
                "reasoning": reasoning_text.strip(),
                "execution_time": round(execution_time, 2),
                "tools_used": len(agent_executor.tools)
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error processing query: {str(e)}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "reasoning": "",
                "execution_time": round(execution_time, 2),
                "tools_used": 0
            }

    def get_loaded_files_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about loaded files"""
        info = {}
        for tool_name, file_data in self.loaded_files.items():
            info[tool_name] = {
                "file_path": file_data["file_path"],
                "sheet_name": file_data["sheet_name"],
                "rows": len(file_data["dataframe"]),
                "columns": list(file_data["dataframe"].columns)
            }
        return info
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached agent executors (for debugging)"""
        return {
            "cached_executors": list(self._agent_cache.keys()),
            "cache_size": len(self._agent_cache)
        }

    def clear_loaded_files(self):
        """Clear all loaded files and reset agent"""
        self.loaded_files = {}
        self._agent_cache.clear()
        logger.info("Cleared all loaded files and agent cache")