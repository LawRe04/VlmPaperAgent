import os
import re
from datetime import datetime
from dotenv import load_dotenv
from agent import PaperAgent


def build_output_path(user_input: str) -> str:
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", user_input.strip())[:40].strip("_")
    if not slug:
        slug = "query"
    return os.path.join(output_dir, f"{timestamp}_{slug}.txt")

def main():
    # Load API config from .env
    load_dotenv()
    
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("Error: API key not found in environment variables.")
        print("Please create a .env file and set OPENAI_API_KEY='your_api_key'")
        print("For backward compatibility, DASHSCOPE_API_KEY is also supported.")
        return

    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")

    agent = PaperAgent(api_key=api_key, base_url=base_url, model=model)
    
    print("Welcome to Qwen Paper Agent!")
    print("Example Queries:")
    print("1. 请帮我找一下论文 'Attention is all you need' 的引用文，列出作者和引用时的句子。")
    print("2. 帮我搜索 'Ilya Sutskever' 的所有论文。")
    print("Type 'exit' to quit.\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        if not user_input.strip():
            continue
            
        print("\nAgent is processing your request...")
        # Since run() is a generator handling tool call execution prints
        for output in agent.run(user_input):
            if output:  # The final string output
                print(f"\nQwen: {output}\n")
                
                # Save each query result to a separate text file
                output_file = build_output_path(user_input)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"--- Query: {user_input} ---\n\n")
                    f.write(f"{output}\n\n")
                print(f"[Info] Output has been saved to {output_file}\n")

if __name__ == "__main__":
    main()
