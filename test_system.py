#!/usr/bin/env python3
"""
Windows AI Agent - Quick Test Script
Tests Ollama connection and basic tool functionality
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ollama_connection():
    """Test connection to Ollama"""
    print("=" * 50)
    print("Testing Ollama Connection...")
    print("=" * 50)
    
    from llm.client import OllamaClient
    
    client = OllamaClient(model="llama4")
    
    if client.is_available():
        print("✅ Ollama is running!")
        models = client.list_models()
        print(f"✅ Available models: {models}")
        
        # Check if llama4 is available
        llama4_models = [m for m in models if 'llama4' in m.lower() or 'llama-4' in m.lower() or 'llama:4' in m.lower()]
        if llama4_models:
            print(f"✅ LLaMA 4 found: {llama4_models}")
        else:
            print("⚠️  LLaMA 4 not found in model list. Available models:")
            for m in models:
                print(f"   - {m}")
            print("\n   You may need to adjust the model name in the config.")
        
        return True
    else:
        print("❌ Cannot connect to Ollama!")
        print("   Make sure Ollama is running: ollama serve")
        return False


def test_tool_server():
    """Test tool server functionality"""
    print("\n" + "=" * 50)
    print("Testing Tool Server...")
    print("=" * 50)
    
    from tools.registry import get_tool_server
    from core.types import ToolRequest
    
    server = get_tool_server()
    tools = server.get_tool_schemas()
    
    print(f"✅ Tool server initialized with {len(tools)} tools")
    print("\n   Available tools:")
    for tool in sorted(tools, key=lambda t: t.name):
        print(f"   - {tool.name}: {tool.description[:50]}...")
    
    # Test a simple tool (directory listing)
    print("\n   Testing 'directory_list' tool...")
    request = ToolRequest(
        tool="directory_list",
        arguments={"path": os.path.expanduser("~")}
    )
    
    result = server.execute(request)
    if result.status.value == "success":
        count = result.result.get("result", {}).get("count", 0)
        print(f"✅ Tool executed successfully! Found {count} items in home directory")
    else:
        print(f"❌ Tool failed: {result.error}")
    
    return True


def test_simple_chat():
    """Test a simple chat interaction"""
    print("\n" + "=" * 50)
    print("Testing Simple Chat...")
    print("=" * 50)
    
    from llm.client import OllamaClient
    
    client = OllamaClient(model="llama4")
    
    print("   Sending test message to LLM...")
    try:
        response = client.chat([
            {"role": "user", "content": "Say 'Hello, I am working!' in exactly those words."}
        ])
        print(f"✅ LLM Response: {response.content[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        return False


def test_agent():
    """Test the full agent"""
    print("\n" + "=" * 50)
    print("Testing Full Agent...")
    print("=" * 50)
    
    from orchestrator.agent import create_agent
    
    # Create agent with auto-confirm for testing
    agent = create_agent(
        model="llama4",
        verbose=True,
        confirmation_handler=lambda r: True  # Auto-confirm for testing
    )
    
    if not agent.is_ready():
        print("❌ Agent not ready - Ollama connection failed")
        return False
    
    print("✅ Agent initialized!")
    print(f"   Tools available: {len(agent.get_available_tools())}")
    
    # Test a simple query
    print("\n   Testing agent with: 'What is 2 + 2?'")
    try:
        response = agent.process("What is 2 + 2? Just give me the number.")
        print(f"✅ Agent response: {response[:200]}...")
    except Exception as e:
        print(f"❌ Agent error: {e}")
        return False
    
    return True


def run_interactive_demo():
    """Run a quick interactive demo"""
    print("\n" + "=" * 50)
    print("Interactive Demo")
    print("=" * 50)
    print("Type messages to chat with the agent.")
    print("Type 'quit' to exit.\n")
    
    from orchestrator.agent import create_agent
    
    agent = create_agent(model="llama4", verbose=True)
    
    if not agent.is_ready():
        print("❌ Cannot start demo - Ollama not available")
        return
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            if not user_input:
                continue
            
            print("\n🤖 Thinking...")
            response = agent.process(user_input)
            print(f"\n🤖 Agent: {response}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           Windows AI Agent - System Test                      ║
║           Testing Ollama + LLaMA 4 + Tools                    ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Run tests
    ollama_ok = test_ollama_connection()
    
    if not ollama_ok:
        print("\n⚠️  Ollama connection failed. Please ensure:")
        print("   1. Ollama is installed (https://ollama.ai)")
        print("   2. Ollama is running (ollama serve)")
        print("   3. LLaMA 4 is pulled (ollama pull llama4)")
        sys.exit(1)
    
    tool_ok = test_tool_server()
    chat_ok = test_simple_chat()
    
    if chat_ok:
        agent_ok = test_agent()
    else:
        agent_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"   Ollama Connection: {'✅ PASS' if ollama_ok else '❌ FAIL'}")
    print(f"   Tool Server:       {'✅ PASS' if tool_ok else '❌ FAIL'}")
    print(f"   LLM Chat:          {'✅ PASS' if chat_ok else '❌ FAIL'}")
    print(f"   Full Agent:        {'✅ PASS' if agent_ok else '❌ FAIL'}")
    
    if all([ollama_ok, tool_ok, chat_ok, agent_ok]):
        print("\n✅ All tests passed! The system is ready to use.")
        print("\nYou can now run:")
        print("   python main.py          - CLI interface")
        print("   python ui/gui.py        - GUI interface (requires PyQt6)")
        
        # Offer interactive demo
        print("\n" + "-" * 50)
        response = input("Would you like to try an interactive demo? (y/n): ")
        if response.lower() in ['y', 'yes']:
            run_interactive_demo()
    else:
        print("\n❌ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()
