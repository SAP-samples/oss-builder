import os
import git
import shutil


def get_repo_at_commit(repo_url: str, repo_name: str, commit: str) -> git.Repo:
    path = os.path.join('repos', repo_name, commit)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    try:
        repo = git.Repo(path)
        repo.git.checkout(commit)
    except git.GitError:
        shutil.rmtree(path)
        os.makedirs(path)
        repo = git.Repo.clone_from(repo_url, path)
        repo.git.checkout(commit)
    return repo
