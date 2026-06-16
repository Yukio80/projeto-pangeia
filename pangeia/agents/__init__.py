from pangeia.agents.citizen import Citizen
from pangeia.agents.entrepreneur import Entrepreneur
from pangeia.agents.researcher import Researcher
from pangeia.agents.governor import Governor
from pangeia.agents.journalist import Journalist
from pangeia.agents.military import Military
from pangeia.agents.philosopher import Philosopher
from pangeia.agents.moltbook import MoltbookAgent
from pangeia.agents.teacher import Teacher
from pangeia.agents.conservative import Conservative

AGENT_CLASSES = {
    "citizen": Citizen,
    "entrepreneur": Entrepreneur,
    "researcher": Researcher,
    "governor": Governor,
    "journalist": Journalist,
    "military": Military,
    "philosopher": Philosopher,
    "moltbook": MoltbookAgent,
    "teacher": Teacher,
    "conservative": Conservative,
}

__all__ = [
    "Citizen", "Entrepreneur", "Researcher", "Governor",
    "Journalist", "Military", "Philosopher", "MoltbookAgent", "Teacher",
    "Conservative",
    "AGENT_CLASSES",
]
