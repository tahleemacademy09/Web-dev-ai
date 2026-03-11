import os
import subprocess
import requests
import openai

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}
MODEL = "gpt-4o"
MAX_CHARS_PER_FILE = 8000

def get_changed_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1...HEAD"],
        capture_output=True, text=True
    )
    files = result.stdout.strip().splitlines()
    return [f for f in files if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS and os.path.isfile(f)]

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:MAX_CHARS_PER_FILE]
    except Exception as e:
        return "[Could not read file: " + str(e) + "]"

def review_file(path, code):
    client = openai.OpenAI()
    prompt = (
        "You are a senior software engineer doing a code review.\n"
        "Review this file: " + path + "\n\n"
        "Focus on bugs, security issues, performance, and readability.\n"
        "Be concise. Use markdown bullet points.\n\n"
        "Code:\n" + code
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()

def post_github_comment(body):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["REPO"]
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    url = "https://api.github.com/repos/" + repo + "/commits/" + sha + "/comments"
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
    }
    response = requests.post(url, json={"body": body}, headers=headers)
    response.raise_for_status()
    print("Comment posted!")

def main():
    changed_files = get_changed_files()
    if not changed_files:
        print("No supported files changed. Skipping.")
        return
    sections = ["## AI Code Review\n"]
    for path in changed_files:
        code = read_file(path)
        review = review_file(path, code)
        sections.append("### " + path + "\n" + review + "\n")
    sections.append("---\nAutomated review. Use your own judgment.")
    post_github_comment("\n".join(sections))

if __name__ == "__main__":
    main()
