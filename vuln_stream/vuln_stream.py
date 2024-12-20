import os
import json
from rich.progress import track
from typing import Iterable
from vuln_stream import gitextractor
from vuln_stream import stats
from vuln_stream.vulnerability_candidate import VulnerabilityCandidate
import os


this_dir = os.path.dirname(os.path.abspath(__file__))
vulnerability_dir = os.path.join(this_dir, 'data/')

def build_candidate(report: dict, fix_commit: str,
                    is_last: bool) -> VulnerabilityCandidate:
    return VulnerabilityCandidate(
        project_name=report['affected'][0]['package']['name'],
        fix_commit=fix_commit,
        is_last_fix_commit=is_last,
        report_id=report['id'],
        repo_url=report['affected'][0]['ranges'][0]['repo']
    )


def extract_suitable_vulns() -> Iterable[VulnerabilityCandidate]:
    report_paths = os.listdir(vulnerability_dir)
    description = 'Filtering for sufficient report information'
    for osv_path in track(report_paths, description=description):
        if stats.has_previous_error(osv_path.replace('.json', '')):
            # Already filtered in a previous run
            continue
        with open(os.path.join(vulnerability_dir, osv_path)) as f:
            report = json.load(f)
        affected = report['affected']
        if len(affected) != 1:
            stats.record_event(stats.Event.AFFECTED_NOT_SIZE_ONE, report['id'])
            continue
        if 'ranges' not in affected[0]:
            stats.record_event(stats.Event.NO_RANGE, report['id'])
            continue
        ranges = affected[0]['ranges']
        if len(ranges) != 1:
            stats.record_event(stats.Event.MULTIPLE_RANGES, report['id'])
            continue
        # convienience filter, if we really want we can implement other
        # VCS later
        if ranges[0]['type'] != 'GIT':
            stats.record_event(stats.Event.NOT_GIT, report['id'])
            continue
        events = ranges[0]['events']
        # TODO we should be able to handle them!
        # [{'fixed': 'a4647a5463102c4b0c5a02461edd4cc085dfc1b6'}]
        fix_commits = list(filter(lambda x: 'fixed' in x, events))
        if len(fix_commits) == 0:
            stats.record_event(stats.Event.NOT_FIXED, report['id'])
            continue
        # TODO(liam) check if commits are really ordered by time in the json
        for fix_commit in fix_commits:
            is_last =  fix_commit == fix_commits[-1]
            yield build_candidate(report, fix_commit['fixed'], is_last)


def process() -> Iterable[gitextractor.Vulnerability]:
    reports = list(extract_suitable_vulns())
    # for testing:
    # reports = list(filter(lambda x: x.project_name == 'libexif', reports))
    return gitextractor.get_info_for_commits(reports)
