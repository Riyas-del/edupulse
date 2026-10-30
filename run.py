import os
import sys
import webbrowser
import time
import uvicorn

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "backend"))

from database import init_db, seed_demo_data

def main():
    print("=" * 70)
    print("EDUPULSE: SMART STUDENT MONITORING & ALARM SYSTEM")
    print("=" * 70)
    print("Initializing SQLite Database & Academic Rules...")
    init_db()
    seed_demo_data(reset=False)
    print("Database verified with 20 tables and active student profile.")

    port = int(os.environ.get("PORT", 8000))
    url = f"http://localhost:{port}"
    print(f"Starting EduPulse Server on port {port}...")
    print("Core Product Principle: Never let a student miss a deadline or low attendance!")

    # Only open browser on desktop environments (not headless cloud servers like Render)
    if not os.environ.get("RENDER") and not os.environ.get("PORT"):
        def open_browser():
            time.sleep(1.5)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("app:app", host="0.0.0.0", port=port, app_dir=os.path.join(CURRENT_DIR, "backend"), reload=False)

if __name__ == '__main__':
    main()
