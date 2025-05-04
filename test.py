from app.agent.config import AgentState

user1 = AgentState(project_id="123", current_query="What is the average price of the product?")
user2 = AgentState(project_id="1233", current_query="What is the average price of the product?")

user1.messages.append("Hello")
print(user2.messages)  # ['Hello'] 😱