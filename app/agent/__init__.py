from typing import Dict, Any, List
from .config import AgentState
from .graph import create_graph

class DataAnalysisAgent:
    """Agent for analyzing data based on natural language queries"""
    
    def __init__(self):
        self.graph = create_graph()
    
    async def analyze(self, project_id: str, query: str, datasets: List[Dict[str, Any]], past_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze data based on user query
        
        Args:
            project_id: The project ID containing the datasets
            query: Natural language query from user
            
        Returns:
            Analysis results
        """
        # Initialize state
        state = AgentState(
            project_id=project_id,
            current_query=query,
            datasets=datasets,
            past_messages=past_messages
        )
        print(state)
        
        # Run the graph using run_sync
        result = await self.graph.ainvoke(state)
        print("FINAL RESULT")
        print(result)
        return {
            "query": query,
            "result": result.get("formatted_response", None),
            "code_generated": result.get("generated_code", None)
        }
