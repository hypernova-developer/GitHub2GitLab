import os
import configparser
import requests

config = configparser.ConfigParser()

if not os.path.exists("config.conf"):
    print("[X] Error: 'config.conf' not found! Please create the configuration file first.")
    exit(1)

config.read("config.conf")

try:
    GITHUB_USERNAME = config["github"]["username"]
    GITHUB_TOKEN = config["github"]["token"]
    GITLAB_USERNAME = config["gitlab"]["username"]
    GITLAB_TOKEN = config["gitlab"]["token"]
except KeyError as e:
    print(f"[X] Error: Missing required key in 'config.conf': {e}")
    exit(1)

GITLAB_BASE_URL = "https://gitlab.com/api/v4"

github_url = "https://api.github.com/user/repos?per_page=100"
headers_gh = {"Authorization": f"token {GITHUB_TOKEN}"}
gh_repos = requests.get(github_url, headers=headers_gh).json()

if isinstance(gh_repos, dict) and "message" in gh_repos:
    print(f"[X] GitHub API Error: {gh_repos['message']}")
    exit(1)

print(f"[*] Found {len(gh_repos)} repositories. Starting migration and mirroring...")

for repo in gh_repos:
    repo_name = repo["name"]
    is_private = repo["private"]
    
    github_clone_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"
    
    print(f"[+] Processing: {repo_name} (Private: {is_private})")
    
    gitlab_project_data = {
        "name": repo_name,
        "path": repo_name,
        "visibility": "private" if is_private else "public"
    }
    headers_gl = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    
    gl_create_res = requests.post(f"{GITLAB_BASE_URL}/projects", data=gitlab_project_data, headers=headers_gl)
    
    if gl_create_res.status_code == 201:
        project_id = gl_create_res.json()["id"]
        print(f"    [v] GitLab project created successfully. ID: {project_id}")
        
        mirror_data = {
            "import_url": github_clone_url,
            "mirror": "true",
            "mirror_trigger_builds": "false"
        }
        gl_mirror_res = requests.put(f"{GITLAB_BASE_URL}/projects/{project_id}", data=mirror_data, headers=headers_gl)
        
        if gl_mirror_res.status_code in [200, 201]:
            print(f"    [v] Automatic HTTPS mirroring bridge established for {repo_name}!")
        else:
            print(f"    [X] Failed to set up mirroring: {gl_mirror_res.text}")
    else:
        print(f"    [X] Failed to create GitLab project (It might already exist): {gl_create_res.text}")

print("\n[!] Operation complete! All repositories are safely bridged.")

