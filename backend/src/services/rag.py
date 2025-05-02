import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize HuggingFace embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)
logger.info("HuggingFace embeddings initialized.")

# Connect to ChromaDB
chroma_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
logger.info("Connected to ChromaDB.")

# Custom tool to retrieve content
class ChromaRetrieverTool(BaseTool):
    name: str = "ChromaRetrieverTool"
    description: str = "Retrieve relevant content from ChromaDB vector store."

    def _run(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Searching ChromaDB with query: {query}")
            docs = chroma_db.similarity_search(query, k=top_k)
            return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
        except Exception as e:
            logger.error(f"ChromaRetrieverTool error: {str(e)}")
            return [{"content": "Error retrieving content. Try again.", "metadata": {}}]

# RAG orchestrator with 2 agents only
class RAGOrchestrator:
    def __init__(self, model_name="groq/deepseek-r1-distill-llama-70b"):
        self.llm = ChatGroq(
            model_name=model_name,
            temperature=0.5,
            max_tokens=800,
            api_key=groq_api_key
        )
        logger.info(f"LLM initialized with model: {model_name}")

        self.retriever_tool = ChromaRetrieverTool()
        self._create_agents()
        self._create_tasks()

        self.crew = Crew(
            agents=[self.router_agent, self.retriever_agent],
            tasks=[self.routing_task, self.retrieval_task],
            verbose=True,
            memory=True,
            cache=True
        )

    def _create_agents(self):
        self.router_agent = Agent(
            role="Marketing Query Router",
            goal="Interpret marketing-related queries and extract focused search terms related to startup strategies, growth tactics, or investment insights",
            backstory="Expert in analyzing marketing and venture capital questions to distill focused queries.",
            llm=self.llm,
            max_iter=2,
            verbose=True
        )

        self.retriever_agent = Agent(
            role="Marketing Content Retriever",
            goal="Retrieve actionable startup and marketing insights from ChromaDB",
            backstory=(
                "Specialist in surfacing valuable insights from startup and VC content like 20VC. "
                "Focus on finding relevant information from founders, operators, or investors."
            ),
            tools=[self.retriever_tool],
            llm=self.llm,
            max_iter=2,
            verbose=True
        )

    def _create_tasks(self):
        self.routing_task = Task(
            description="Analyze the user query and generate 3–5 optimized search terms for retrieving startup and marketing insights from ChromaDB.",
            agent=self.router_agent,
            expected_output=(
                "Generate precise marketing or startup-relevant search queries.\n"
                "Example: ['early stage GTM SaaS', 'product-led growth founders', 'CAC vs LTV', 'fundraising in seed stage']"
            )
        )

        self.retrieval_task = Task(
            description=(
                "Use the optimized search terms from the previous step to retrieve detailed startup, growth, or investment insights "
                "from ChromaDB. Output only the relevant insights."
            ),
            agent=self.retriever_agent,
            expected_output=(
                "A concise but useful response with insights extracted from retrieved documents only.\n"
                "Your task is to find the most relevant and practical information from content. "
                "Only use retrieved content to answer. Be specific and actionable.\n\n"
                "Examples:\n"
                "- Q: How do SaaS founders scale GTM early?\n"
                "- A: 'GTM should start with founder-led efforts, focusing on ICP validation. David Sacks recommends...'\n\n"
                "- Q: What are signs to fire a VP Marketing?\n"
                "- A: 'Harry Stebbings says if there's no traction within 90 days or pipeline progress, it’s a red flag.'"
      ),
            context=[self.routing_task]
        )

    def process_query(self, query: str) -> Dict[str, Any]:
        try:
            logger.info(f"Processing query: {query}")
            result = self.crew.kickoff(inputs={"query": query})
            return {"answer": result, "status": "success"}
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            return {"error": str(e), "status": "failed"}

# Singleton pattern for reuse
_rag_instance = None

def get_rag_instance(model_name: str = "groq/deepseek-r1-distill-llama-70b") -> RAGOrchestrator:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGOrchestrator(model_name)
    return _rag_instance

def process_query(query: str, output_format: str = None) -> Dict[str, Any]:
    try:
        rag = get_rag_instance()
        return rag.process_query(query)
    except Exception as e:
        logger.error(f"Error in process_query: {str(e)}")
        return {"error": str(e), "status": "failed"}

__all__ = ['process_query', 'RAGOrchestrator']
