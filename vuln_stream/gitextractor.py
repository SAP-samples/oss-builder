import git
from rich.progress import track
from typing import Iterable, Union, Any, Optional

from vuln_stream import diff
from gitcache import get_repo_at_commit
from vuln_stream import stats
from vuln_stream.vulnerability_candidate import VulnerabilityCandidate


def group_by_repo(candidates: list[VulnerabilityCandidate]) \
        -> dict[str, list[VulnerabilityCandidate]]:
    """
    return a dictionary of repo_url to list of VulnerabilityCandidates
    """
    repos = {}
    for report in candidates:
        repo = report.repo_url
        if repo not in repos:
            repos[repo] = []
        repos[repo].append(report)
    return repos


def get_commit(report: dict) -> str:
    events: list[dict] = report['affected'][0]['ranges'][0]['events']
    return next(filter(lambda x: 'fixed' in x, events))['fixed']


def get_changed_files(commit: git.Commit) -> list[str]:
    return list(map(str, commit.stats.files.keys()))


def filter_interesting_files(files: Iterable[str]) -> list[str]:
    interesting_extensions = ('.c', '.cpp', '.h', '.hpp', 'cc', 'cxx', 'hxx')
    return list(
            filter(
                   lambda x: x.endswith(interesting_extensions) and
                   'test' not in x,
                   files
                  )
            )


def get_previous_commit(commit: git.Commit) -> str:
    # fix commits are unlikely to be merge commits
    return commit.parents[0].hexsha


def get_source_code_file(commit: git.Commit, file: str) -> str:
    return commit.tree[file].data_stream.read().decode() or ''


# TODO(liam) change commit to vuln_commit and optional fix commit
# TODO(liam) include report id
class Vulnerability:
    project_name: str
    vuln_commit: str
    sec_commit: Optional[str]
    affected_files: list[str]
    repo_url: str
    report_id: str
    vuln_diff: diff.Diff

    def __init__(self, project_name: str, vuln_commit: str,
                 sec_commit: Optional[str], affected_files: list[str],
                 repo_url: str, report_id: str, vuln_diff: diff.Diff):
        self.project_name = project_name
        self.vuln_commit = vuln_commit
        self.sec_commit = sec_commit
        self.affected_files = affected_files
        self.repo_url = repo_url
        self.report_id = report_id
        self.vuln_diff = vuln_diff

    def __str__(self):
        d = {k: v for k, v in self.__dict__.items()}
        return str(d)


def get_report_info(report: VulnerabilityCandidate) -> Optional[Vulnerability]:
    def get_interesting_files(commit: git.Commit,
                                  interesting_files) -> dict[str, str]:
        return {file: get_source_code_file(commit, file) for file in
                interesting_files}


    try:
        repo = get_repo_at_commit(report.repo_url, report.project_name,
                                  report.fix_commit)

        commit = repo.commit(report.fix_commit)
        changed_files = get_changed_files(commit)
        interesting_files = filter_interesting_files(changed_files)
        fix_commit_files = {}
        last_commit = commit.parents[0]
        last_commit_files = get_interesting_files(last_commit,
                                                  interesting_files)
        fix_commit_files = get_interesting_files(commit, interesting_files)

    except Exception as e:
        print(f"Git extraction error {e}")
        stats.record_event(stats.Event.GIT_EXTRACTION_ERROR, report.report_id)
        return None
    if len(interesting_files) == 0:
        stats.record_event(stats.Event.NO_SOURCE_CHANGE, report.report_id)
        return None
    vuln_commit = get_previous_commit(commit) \
            if report.is_last_fix_commit else report.fix_commit
    fix_commit = report.fix_commit if report.is_last_fix_commit else None

    # TODO(liam) is there any way to process multiple changed functions
    # print('Commit: ' + repo.remotes.origin.url + '/commit/' + commit.hexsha)
    diffs: list[diff.Diff] = []
    for file in interesting_files:
        fixed_content = fix_commit_files[file]
        last_content = last_commit_files[file]
        d = diff.Diff(file, last_content, fixed_content)
        diffs.append(d)
    # print('----------')
    if len(diffs) != 1 or len(diffs[0].get_changed_functions()) != 1:
        stats.record_event(stats.Event.MULTIPLE_CHANGES, report.report_id)
        return None
    return Vulnerability(report.project_name, vuln_commit, fix_commit,
                         interesting_files, report.repo_url, report.report_id,
                         diffs[0])


# TODO(liam) simply control/exeption flow
def get_info_for_commits(reports_in_repo: list[VulnerabilityCandidate])\
                                 -> Iterable[Vulnerability]:
    grouped = group_by_repo(reports_in_repo)
    desc = 'Extracting information from repositories'
    for _, reports_in_repo in track(grouped.items(), description=desc):
        repo_report_infos: list[Vulnerability] = []
        for report in reports_in_repo:
            r = None
            try:
                r = get_report_info(report)
            except KeyError:
                stats.record_event(stats.Event.GIT_EXTRACTION_ERROR,
                                   report.report_id)
            if r is not None:
                repo_report_infos.append(r)

        yield from repo_report_infos
