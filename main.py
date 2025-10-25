import os
import tempfile
import subprocess
import requests
import random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from github import Github
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="LLM Deployment API", description="Auto-builds and deploys AI-generated web apps")

# ✅ Root route (prevents 404 on Render)
@app.get("/")
def home():
    return {"message": "🚀 LLM Deployment API is running successfully on Render!"}

# ✅ Step 0: Define JSON structure for Swagger and validation
class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str] = []
    evaluation_url: str
    attachments: List[Dict[str, Any]] = []

# ✅ Step 1: Main endpoint
@app.post("/handle_task")
async def handle_task(data: TaskRequest, request: Request = None):
    try:
        # Convert Pydantic model to dict
        data = data.dict()
        print("\n=== Incoming JSON ===")
        print(data)

        # Step 2: Validate secret
        student_secret = os.getenv("STUDENT_SECRET")
        if not student_secret:
            return JSONResponse(content={"error": "STUDENT_SECRET not set"}, status_code=500)
        if data.get("secret") != student_secret:
            return JSONResponse(content={"error": "Invalid secret"}, status_code=403)

        # Extract fields
        task_name = data.get("task", "default-task").replace(" ", "-")
        email = data.get("email")
        evaluation_url = data.get("evaluation_url")
        nonce = data.get("nonce")
        round_no = int(data.get("round", 1))
        brief = data.get("brief", "")

        # Step 3: Connect to GitHub
        gh_token = os.getenv("GITHUB_TOKEN")
        if not gh_token:
            return JSONResponse(content={"error": "GITHUB_TOKEN not set"}, status_code=500)

        g = Github(gh_token)
        user = g.get_user()
        repo_name = f"llm-{task_name}"

        # ================== ROUND 1: Create Repo ==================
        if round_no == 1:
            for attempt in range(3):
                try:
                    print(f"🚀 Creating repo: {repo_name}")
                    repo = user.create_repo(
                        repo_name, private=False, auto_init=False,
                        description=f"Auto-generated repo for {email}"
                    )
                    break
                except Exception as e:
                    if "name already exists" in str(e).lower():
                        suffix = random.randint(100, 999)
                        repo_name = f"{repo_name}-{suffix}"
                        print(f"⚠️ Repo already exists. Retrying as: {repo_name}")
                    else:
                        raise
            else:
                return JSONResponse(
                    content={"error": "Failed to create unique repo name after retries."},
                    status_code=500
                )

            temp_dir = tempfile.mkdtemp()

            # ✅ Step 4: Generate app code using AI Pipe (correct endpoint)
            ai_pipe_token = os.getenv("AI_PIPE_TOKEN")
            if ai_pipe_token:
                print("🧠 Using AI Pipe to generate code for:", brief)
                ai_pipe_url = "https://aipipe.org/openrouter/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {ai_pipe_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "openai/gpt-4.1-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert web app generator. Generate self-contained HTML+JS apps suitable for GitHub Pages."},
                        {"role": "user", "content": f"Create a single-page HTML+JS web app for this task: {brief}. Ensure it is fully self-contained and runnable in the browser."}
                    ]
                }

                ai_response = requests.post(ai_pipe_url, headers=headers, json=payload, timeout=60)
                if ai_response.status_code == 200:
                    result = ai_response.json()
                    
                    generated_code = result["choices"][0]["message"]["content"]

                    # 🧹 Clean up Markdown-style code fences if present
                    if generated_code.startswith("```"):
                        generated_code = generated_code.split("```", 2)[1]
                        generated_code = generated_code.replace("html\n", "").replace("html\r\n", "")
                        generated_code = generated_code.strip()

                else:
                    print("⚠️ AI Pipe failed:", ai_response.text)
                    generated_code = "<h1>AI generation failed</h1>"
            else:
                print("⚠️ AI_PIPE_TOKEN not found. Skipping AI generation.")
                generated_code = "<h1>No AI generation available</h1>"

            # Write files to repo
            with open(os.path.join(temp_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(generated_code)
            with open(os.path.join(temp_dir, "README.md"), "w", encoding="utf-8") as f:
                f.write(f"# {repo_name}\n\nGenerated using AI Pipe for {email}\n\n**Brief:** {brief}")
            with open(os.path.join(temp_dir, "LICENSE"), "w", encoding="utf-8") as f:
                f.write("MIT License")

            # Git setup and push
            subprocess.run(["git", "init"], cwd=temp_dir, check=True)
            subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=temp_dir, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", repo.clone_url.replace("https://", f"https://{gh_token}@")],
                cwd=temp_dir, check=True
            )
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=temp_dir, check=True)

        # ================== ROUND 2: Update Existing Repo ==================
        else:
            print(f"♻️ Round {round_no} detected. Updating existing repo: {repo_name}")
            clone_url = f"https://{gh_token}@github.com/{user.login}/{repo_name}.git"
            repo_dir = tempfile.mkdtemp()
            subprocess.run(["git", "clone", clone_url, repo_dir], check=True)

            # Update README.md
            readme_path = os.path.join(repo_dir, "README.md")
            with open(readme_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n### Update for Round {round_no}\n{brief}\n")

            # Re-generate HTML using AI Pipe for the new brief
            ai_pipe_token = os.getenv("AI_PIPE_TOKEN")
            if ai_pipe_token:
                ai_pipe_url = "https://aipipe.org/openrouter/v1/chat/completions"
                headers = {"Authorization": f"Bearer {ai_pipe_token}", "Content-Type": "application/json"}
                payload = {
                    "model": "openai/gpt-4.1-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert app updater. Modify the HTML+JS code as instructed."},
                        {"role": "user", "content": f"Update the previous app to include these improvements: {brief}. Output the full HTML+JS code."}
                    ]
                }

                ai_response = requests.post(ai_pipe_url, headers=headers, json=payload, timeout=60)
                if ai_response.status_code == 200:
                    result = ai_response.json()
                    new_code = result["choices"][0]["message"]["content"]
                    with open(os.path.join(repo_dir, "index.html"), "w", encoding="utf-8") as f:
                        f.write(new_code)
                    print("✨ AI Pipe: Updated app generated successfully.")
                else:
                    print("⚠️ AI update failed:", ai_response.text)

            # Commit and push changes
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"Round {round_no} update"], cwd=repo_dir, check=True)
            subprocess.run(["git", "push"], cwd=repo_dir, check=True)
            repo = g.get_repo(f"{user.login}/{repo_name}")

        # ================== Enable GitHub Pages ==================
        pages_url = f"https://{user.login}.github.io/{repo_name}/"
        print("⚙️ Enabling GitHub Pages...")

        api_url = f"https://api.github.com/repos/{user.login}/{repo_name}/pages"
        headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github+json"}
        payload = {"source": {"branch": "main", "path": "/"}}

        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code in [201, 204]:
                print(f"🌐 Pages enabled successfully at: {pages_url}")
            else:
                print(f"⚠️ GitHub Pages response: {response.status_code} {response.text}")
        except requests.Timeout:
            print("⏰ Timeout enabling GitHub Pages (skipping).")

        repo.edit(homepage=pages_url)

        # ================== Notify Evaluation Server ==================
        commits = repo.get_commits()
        latest_commit = commits[0].sha if commits.totalCount > 0 else None
        payload = {
            "email": email,
            "task": task_name,
            "round": round_no,
            "nonce": nonce,
            "repo_url": repo.html_url,
            "commit_sha": latest_commit,
            "pages_url": pages_url
        }
        print("📤 Sending notification to evaluation URL:", evaluation_url)
        try:
            response = requests.post(evaluation_url, json=payload,
                                     headers={"Content-Type": "application/json"}, timeout=10)
            print("✅ Evaluation server response:", response.status_code)
        except requests.Timeout:
            print("⏰ Timeout notifying evaluation URL (continuing).")

        return {
            "message": f"Round {round_no} completed successfully!",
            "repo_url": repo.html_url,
            "pages_url": pages_url
        }

    except Exception as e:
        print("❌ Error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
