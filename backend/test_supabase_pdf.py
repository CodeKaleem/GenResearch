import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.supabase_client import get_supabase
from services.pdf_renderer import render_markdown_to_pdf

def test():
    session_id = "4357509b-2746-4033-86f5-285cad25fca9"
    sb = get_supabase()
    res = sb.table("research_reports").select("topic, completion_guide").eq("session_id", session_id).execute()
    
    if not res.data:
        print("No report found in database.")
        return
        
    report = res.data[0]
    topic = report.get("topic", "Research Draft")
    completion_guide = report.get("completion_guide", "")
    
    print(f"Topic: {topic}")
    print(f"Completion Guide Length: {len(completion_guide)}")
    print("--- Completion Guide Preview ---")
    print(completion_guide[:500])
    print("--------------------------------")
    
    try:
        pdf_bytes = render_markdown_to_pdf(completion_guide, title=f"Guide: {topic}")
        print(f"Success! PDF bytes length: {len(pdf_bytes)}")
    except Exception as e:
        import traceback
        print("FAILED to render PDF:")
        traceback.print_exc()

if __name__ == "__main__":
    test()
