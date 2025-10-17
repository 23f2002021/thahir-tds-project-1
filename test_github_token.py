from github import Github
import os

token = os.getenv("GITHUB_TOKEN")
print("Loaded token:", token[:8] + "..." if token else "None")

if not token:
    print("❌ Token not found. Run setx GITHUB_TOKEN again.")
else:
    g = Github(token)
    try:
        user = g.get_user()
        print("✅ Authenticated as:", user.login)
    except Exception as e:
        print("❌ Error:", e)
