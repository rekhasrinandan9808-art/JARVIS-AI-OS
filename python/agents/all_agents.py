"""
all_agents.py
The ONE place that imports every concrete agent class. registry.py reads
this list to build the live system. Adding agent #40 means: write its
class, add one import line + one entry here. Nothing else changes.
"""

# =================================================
# CORE AGENTS (1-39)
# =================================================

from .memory.agent import MemoryAgent                    # 1
from .rag.agent import RAGAgent                         # 2
from .research.agent import ResearchAgent               # 3
from .coding.agent import CodingAgent                   # 4
from .debugging.agent import DebuggingAgent             # 5
from .testing.agent import TestingAgent                 # 6
from .documentation.agent import DocumentationAgent     # 7
from .browser.agent import BrowserAgent                 # 8
from .files.agent import FilesAgent                     # 9
from .windows.agent import WindowsAgent                 # 10
from .linux.agent import LinuxAgent                     # 11
from .networking.agent import NetworkingAgent           # 12
from .robotics.agent import RoboticsAgent               # 13
from .iot.agent import IoTAgent                         # 14
from .plugins.agent import PluginsAgent                 # 15
from .vision.agent import VisionAgent                   # 16
from .voice.agent import VoiceAgent                     # 17
from .ocr.agent import OCRAgent                         # 18
from .translation.agent import TranslationAgent         # 19
from .learning.agent import LearningAgent               # 20
from .security.agent import SecurityAgent               # 21
from .admin.agent import AdminAgent                     # 22
from .communications.agent import CommunicationsAgent   # 23
from .educators.math_agent import MathAgent             # 24
from .educators.physics_agent import PhysicsAgent       # 25
from .educators.chemistry_agent import ChemistryAgent   # 26
from .educators.biology_agent import BiologyAgent       # 27
from .educators.history_agent import HistoryAgent       # 28
from .educators.geography_agent import GeographyAgent   # 29
from .educators.literature_agent import LiteratureAgent # 30
from .educators.philosophy_agent import PhilosophyAgent # 31
from .educators.cs_agent import CSAgent                 # 32
from .educators.lang_agent import LangAgent             # 33
from .educators.art_agent import ArtAgent               # 34
from .educators.economics_agent import EconomicsAgent   # 35
from .educators.law_agent import LawAgent               # 36
from .educators.medical_agent import MedicalAgent       # 37
from .app_controller.agent import AppControllerAgent    # 38
from .supervisor.health_agent import SupervisorAgent    # 39

# =================================================
# ADDITIONAL AGENTS (40-41)
# =================================================

from .llm.agent import LLMAgent                         # 40 - LLM Agent
from .search.agent import SearchAgent                   # 41 - Search Agent

# =================================================
# EXTRA AGENTS (Parallel to agents/ folder)
# =================================================

from .location.agent import LocationAgent               # Location Agent (parallel to agents/)


# =================================================
# BUILD THE FULL LIST
# =================================================

ALL_AGENT_CLASSES = [
    # Core Agents (1-39)
    MemoryAgent,
    RAGAgent,
    ResearchAgent,
    CodingAgent,
    DebuggingAgent,
    TestingAgent,
    DocumentationAgent,
    BrowserAgent,
    FilesAgent,
    WindowsAgent,
    LinuxAgent,
    NetworkingAgent,
    RoboticsAgent,
    IoTAgent,
    PluginsAgent,
    VisionAgent,
    VoiceAgent,
    OCRAgent,
    TranslationAgent,
    LearningAgent,
    SecurityAgent,
    AdminAgent,
    CommunicationsAgent,
    MathAgent,
    PhysicsAgent,
    ChemistryAgent,
    BiologyAgent,
    HistoryAgent,
    GeographyAgent,
    LiteratureAgent,
    PhilosophyAgent,
    CSAgent,
    LangAgent,
    ArtAgent,
    EconomicsAgent,
    LawAgent,
    MedicalAgent,
    AppControllerAgent,
    SupervisorAgent,      # 39
    LLMAgent,             # 40
    SearchAgent,          # 41
]

# =================================================
# VERIFY COUNT
# =================================================

EXPECTED_CORE = 41  # Now 41 core agents (was 39)
assert len(ALL_AGENT_CLASSES) == EXPECTED_CORE, \
    f"Expected {EXPECTED_CORE} core agents, found {len(ALL_AGENT_CLASSES)}"

# =================================================
# EXTRA AGENTS
# =================================================

EXTRA_AGENT_CLASSES = [
    LocationAgent,  # This is in the root agents/ folder but not in the core list
]

# =================================================
# REGISTRY AGENT CLASSES (Used by registry.py)
# =================================================

REGISTRY_AGENT_CLASSES = ALL_AGENT_CLASSES + EXTRA_AGENT_CLASSES

# =================================================
# PRINT SUMMARY
# =================================================

if __name__ == "__main__":
    print(f"📋 Total Agents: {len(REGISTRY_AGENT_CLASSES)}")
    print(f"   Core Agents: {len(ALL_AGENT_CLASSES)}")
    print(f"   Extra Agents: {len(EXTRA_AGENT_CLASSES)}")
    print("\n📋 Agent List:")
    for i, cls in enumerate(REGISTRY_AGENT_CLASSES, 1):
        print(f"   {i:2}. {cls.__name__}")