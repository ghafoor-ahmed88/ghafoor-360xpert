import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY missing in .env")

llm = LLM(
    model="openrouter/deepseek/deepseek-chat",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


researcher = Agent(
    role="Researcher",
    goal="Find simple information",
    backstory="You are a helpful researcher who explains things simply.",
    llm=llm,
)

writer = Agent(
    role="Writer",
    goal="Write clear and easy text",
    backstory="You write in very simple and clear language.",
    llm=llm,
)

# --------------------------------
# Tasks
# --------------------------------
task1 = Task(
    description="AI ke 5 simple points research karo.",
    expected_output="5 bullet points.",
    agent=researcher,
)

task2 = Task(
    description="In points ko ek simple paragraph me likho.",
    expected_output="One easy paragraph.",
    agent=writer,
)

# --------------------------------
# Crew
# --------------------------------
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    verbose=True,
)

print("\nFINAL RESULT:\n")
print(crew.kickoff())
