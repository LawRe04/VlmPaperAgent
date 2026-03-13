import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from tools.scholar_tools import get_author_papers_by_name, get_paper_citations

# Define the tools schema for OpenAI-compatible function calling
SCHOLAR_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_author_papers_by_name",
            "description": "Search for a Google Scholar profile by author name and return a list of up to 100 top papers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "author_name": {
                        "type": "string",
                        "description": "The name of the author to search for on Google Scholar, e.g., 'Ashish Vaswani'."
                    }
                },
                "required": ["author_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper_citations",
            "description": "Given a paper title, find citing papers, their authors, and the exact sentences (contexts) where the original paper was cited. Returns up to 200 papers sorted by H-index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_title": {
                        "type": "string",
                        "description": "The title of the original paper to find citations for, e.g., 'Attention is all you need'."
                    }
                },
                "required": ["paper_title"]
            }
        }
    }
]

# Map tool names to actual Python functions
AVAILABLE_TOOLS = {
    "get_author_papers_by_name": get_author_papers_by_name,
    "get_paper_citations": get_paper_citations,
}

BATCH_SIZE = 20
MAX_PARALLEL_WORKERS = 10

# System prompt for batch summarization (each batch of 20 papers)
BATCH_SYSTEM_PROMPT = (
    "You are an intelligent academic research assistant. You will receive a batch of citing papers for a given original paper. "
    "For EACH citing paper in the batch, you MUST output in EXACTLY the following markdown format:\n\n"
    "## [global_number]. [Paper Title]\n"
    "**作者**: [Author1, Author2, ...]\n\n"
    "**引用上下文**:\n"
    "1. **英文**: \"[exact citation context sentence from the data]\"\n"
    "   **中文**: \"[Chinese translation of the sentence]\"\n"
    "   **引用序号**: [extract any citation numbers like [14], [22-24] from the context]\n\n"
    "CRITICAL RULES:\n"
    "- You MUST list EVERY paper in the batch, do NOT skip any.\n"
    "- Use the global_number provided for each paper as its heading number.\n"
    "- If there are multiple citation contexts, list each one separately as numbered items.\n"
    "- Translate each English context sentence into Chinese.\n"
    "- Extract ALL citation numbers/markers from the context sentences.\n"
    "- If no citation context is available, write '无引用上下文'.\n"
    "- Do NOT add any summary, analysis, or commentary. Only list the papers."
)

# System prompt for the orchestrator agent (decides which tools to call)
ORCHESTRATOR_SYSTEM_PROMPT = (
    "You are an intelligent academic research assistant powered by Qwen. You can find an author's papers on Google Scholar "
    "and citing papers via Semantic Scholar. When a user asks about citations or authors, call the appropriate tool. "
    "IMPORTANT: After calling a tool, simply say 'TOOL_RESULT_READY' and nothing else. Do not try to summarize the tool results yourself."
)


class PaperAgent:
    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None):
        resolved_base_url = base_url or os.environ.get("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        resolved_model = model or os.environ.get("OPENAI_MODEL") or "qwen3.5-plus"

        # Initialize an OpenAI-compatible client. Defaults point to DashScope/Qwen.
        self.client = OpenAI(
            api_key=api_key,
            base_url=resolved_base_url,
        )
        self.model = resolved_model

    def _summarize_batch(self, original_title: str, batch: list, batch_idx: int, global_start_num: int) -> str:
        """
        Summarize a single batch of citing papers using Qwen.
        This runs in a thread for parallel execution.
        global_start_num: the starting number for global paper numbering.
        """
        # Inject global numbering into each paper's data
        for i, paper in enumerate(batch):
            paper['global_number'] = global_start_num + i
        
        batch_json = json.dumps(batch, ensure_ascii=False, indent=2)
        user_msg = (
            f"以下是论文 '{original_title}' 的第 {batch_idx + 1} 批引用文（共 {len(batch)} 篇）。\n"
            f"请严格按照系统提示的格式，逐一输出每篇引用文的详细信息。每篇论文的编号请使用数据中的 global_number 字段。\n\n{batch_json}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": BATCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Batch {batch_idx + 1} Error] {str(e)}"

    def _process_citations_parallel(self, original_title: str, citations: list) -> str:
        """
        Split citations into batches of BATCH_SIZE, process each batch in parallel
        with Qwen, then directly concatenate the results (no re-summarization).
        """
        # Split into batches
        batches = []
        for i in range(0, len(citations), BATCH_SIZE):
            batches.append(citations[i:i + BATCH_SIZE])
        
        total_batches = len(batches)
        print(f"\n[Parallel Processing] Total {len(citations)} citing papers, split into {total_batches} batches of up to {BATCH_SIZE}.")
        print(f"[Parallel Processing] Processing with up to {MAX_PARALLEL_WORKERS} parallel workers...\n")
        
        # Process batches in parallel, with global numbering
        batch_results = [None] * total_batches
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            future_to_idx = {}
            for idx, batch in enumerate(batches):
                global_start = idx * BATCH_SIZE + 1  # 1-indexed global number
                future = executor.submit(self._summarize_batch, original_title, batch, idx, global_start)
                future_to_idx[future] = idx
                
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    batch_results[idx] = result
                    print(f"[Parallel Processing] Batch {idx + 1}/{total_batches} completed.")
                except Exception as e:
                    batch_results[idx] = f"[Batch {idx + 1} Error] {str(e)}"
                    print(f"[Parallel Processing] Batch {idx + 1}/{total_batches} failed: {e}")
        
        print(f"\n[Parallel Processing] All {total_batches} batches completed.\n")
        
        # Simply concatenate all batch results in order (no re-summarization)
        header = (
            f"# 论文 '{original_title}' 的引用文分析报告\n\n"
            f"共找到 **{len(citations)}** 篇引用文，按通讯作者H指数和被引次数排序。\n\n---\n"
        )
        
        body = "\n\n".join([
            result for result in batch_results if result
        ])
        
        return header + body

    def run(self, user_prompt: str):
        """
        Runs the agent:
        1. First, use the orchestrator to decide which tool(s) to call.
        2. If get_paper_citations is called, process the results in parallel batches.
        3. Otherwise, return the agent's response directly.
        """
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}
        ]
        
        messages.append({"role": "user", "content": user_prompt})
        
        # Tool execution loop
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=SCHOLAR_TOOLS_SCHEMA,
                tool_choice="auto",
            )
            
            message = response.choices[0].message
            
            # If the model does not want to call any tools, we are done
            if not message.tool_calls:
                yield message.content
                break
                
            msg_dict = {"role": message.role, "content": message.content or ""}
            if message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            messages.append(msg_dict)
            
            # Execute all tool calls
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_to_call = AVAILABLE_TOOLS[function_name]
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"[Agent] Calling {function_name} with {function_args}...")
                
                try:
                    if function_name == "get_author_papers_by_name":
                        function_response = function_to_call(author_name=function_args.get("author_name"))
                    elif function_name == "get_paper_citations":
                        function_response = function_to_call(paper_title=function_args.get("paper_title"))
                    else:
                        function_response = json.dumps({"error": "Unknown tool"})
                        
                except Exception as e:
                    function_response = json.dumps({"error": str(e)})
                
                # Check if this is a citation result that should be processed in parallel
                if function_name == "get_paper_citations":
                    cit_data = json.loads(function_response)
                    if "citations" in cit_data and len(cit_data["citations"]) > 0:
                        original_title = cit_data.get("original_paper_title", "Unknown")
                        citations = cit_data["citations"]
                        
                        # Process in parallel batches
                        final_result = self._process_citations_parallel(original_title, citations)
                        yield final_result
                        return  # Done, no need to continue the loop
                    else:
                        # No citations or error, let the agent respond
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        })
                else:
                    # For other tools (e.g., get_author_papers_by_name), pass result back to agent
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
