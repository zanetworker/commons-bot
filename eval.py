import time

from llama_index.llms.openai import OpenAI
from llama_index.core import ServiceContext 
from llama_index.core.evaluation import FaithfulnessEvaluator, RelevancyEvaluator,  DatasetGenerator

from index import IndexManager
from loaders import YouTubeLoader, QdrantClientManager, EnvironmentConfig
from query_engine import QueryEngineManager, QueryEngineToolsManager

class ResponseEvaluator:
    def __init__(self, service_context):
        """
        Initializes the evaluator with configured llm (e.g., GPT-4) based Faithfulness and Relevancy evaluators.

        Args:
            service_context (ServiceContext): The service context configured for llm (e.g.,GPT-4).
        """
        self.faithfulness_evaluator = FaithfulnessEvaluator(service_context=service_context)
        self.relevancy_evaluator = RelevancyEvaluator(service_context=service_context)
        self.service_context = service_context

    def evaluate(self, eval_questions):
        """
        Evaluates the performance of the system by calculating three key metrics: 
        average response time, faithfulness, and relevancy.

        Average Response Time:
        This metric measures the average time it takes for the system to respond to a given input or request. 
        It is calculated by summing the response times for all requests and dividing by the total number of requests. 
        A lower average response time generally indicates better performance.

        Faithfulness:
        This metric assesses the accuracy or correctness of the system's output or response. 
        It is calculated based on the proportion of responses that meet a certain accuracy threshold. 
        A high faithfulness score indicates that the system is producing accurate and reliable outputs.

        Relevancy:
        This metric evaluates the degree to which the system's output or response is relevant to the given input or context. 
        It is calculated based on the proportion of responses that meet a certain relevancy threshold. 
        A high relevancy score indicates that the system is producing relevant and valuable outputs.

        Args:
            chunk_size (int): The size of data chunks being processed.
            eval_questions (list): A list of questions to evaluate.
            eval_documents (list): A list of documents to build the vector index from.

        Returns:
            tuple: A tuple containing the average response time, faithfulness, and relevancy metrics.
        """
        total_response_time = 0
        total_faithfulness = 0
        total_relevancy = 0

        config = EnvironmentConfig()
        qdrant_manager = QdrantClientManager(config, collection_name="commons")
        qdrant_client = qdrant_manager.client


        index_manager = IndexManager(qdrant_client, self.service_context)
        index = index_manager.create_or_load_index()

        query_engine_manager = QueryEngineManager(index)
        
        # we can change these parameters to optimize response time, faithfulness, and relevancy
        query_engine = query_engine_manager.create_query_engine(similarity_top_k=2, streaming=False)

        agentContext = query_engine_manager.get_agent_context()
        query_engine_tools_manager = QueryEngineToolsManager(query_engine)
        query_engine_tools = query_engine_tools_manager.query_engine_agent_tools


        num_questions = len(eval_questions)

        for question in eval_questions:
            start_time = time.time()
            response_vector = query_engine.query(question)
            elapsed_time = time.time() - start_time

            faithfulness_result = self.faithfulness_evaluator.evaluate_response(response=response_vector).passing
            relevancy_result = self.relevancy_evaluator.evaluate_response(query=question, response=response_vector).passing

            total_response_time += elapsed_time
            total_faithfulness += faithfulness_result
            total_relevancy += relevancy_result

        average_response_time = total_response_time / num_questions
        average_faithfulness = total_faithfulness / num_questions
        average_relevancy = total_relevancy / num_questions

        return average_response_time, average_faithfulness, average_relevancy


import random

def generate_questions_from_nodes(nodes, num=40):
    random.shuffle(nodes)  # Shuffle the list of nodes
    # Rest of the function implementation goes here
                
def main():
    llm = OpenAI(model="gpt-4", temperature=0.0, stop_symbols=["\n"])
    chunk_sizes = [128, 256, 512, 1024, 2048]

    for chunk_size in chunk_sizes:
        service_context = ServiceContext.from_defaults(llm=llm)

        # generate questions from nodes
        evaluator = ResponseEvaluator(service_context=service_context)
        eval_documents = YouTubeLoader().yttranscripts
        data_generator = DatasetGenerator.from_documents(documents=eval_documents)
        eval_questions = data_generator.generate_questions_from_nodes(num = 40)
        print(f"Eval questions: {eval_questions}")

        avg_response_time, avg_faithfulness, avg_relevancy = evaluator.evaluate(eval_questions)
        print(f"Chunk size {chunk_size} - Average Response time: {avg_response_time:.2f}s, Average Faithfulness: {avg_faithfulness:.2f}, Average Relevancy: {avg_relevancy:.2f}")



if __name__ == "__main__":
    main()