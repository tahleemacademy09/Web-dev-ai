import os
import subprocess
import requests
import openai

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".rs"}
MODEL = "gpt-4o"
MAX_CHARS_PER_FILE = 8_000

def get_changed_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        capture_output=True, text=True
    )
    files = result.stdout.strip().splitlines()
    return [f for f in files if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS and os.path.isfile(f)]

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:MAX_CHARS_PER_FILE]
    except Exception as e:
        return f"[Could not read file: {e}]"

def review_file(path, code):
    client = openai.OpenAI()
    prompt = f"""You are a senior software engineer doing a code review.
Review the following file: `{path}`

Focus on:
- Bugs or logic errors
- Security issues
- Performance improvements
- Readability and naming
- Missing error handling

Format your response as a concise markdown list. If the code looks good, say so briefly.
Do NOT rewrite the whole file — only point out specific issues with line references where possible.
{code}
response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()

def post_pr_comment(body):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.post(url, json={"body": body}, headers=headers)
    response.raise_for_status()
    print(f"Comment posted: {response.json()['html_url']}")

def main():
    changed_files = get_changed_files()
    if not changed_files:
        print("No supported files changed. Skipping review.")
        return
    sections = ["## 🤖 AI Code Review\n"]
    sections.append(f"Reviewed **{len(changed_files)}** changed file(s).\n---\n")
    for path in changed_files:
        code = read_file(path)
        review = review_file(path, code)
        sections.append(f"### `{path}`\n{review}\n")
    sections.append("---\n*This is an automated review. Always use your own judgment before merging.*")
    post_pr_comment("\n".join(sections))

if __name__ == "__main__":
    main()
