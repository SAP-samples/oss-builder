import vuln_stream.vuln_stream as vuln_stream
import vuln_stream.gitextractor as gitextractor
from vuln_stream.gitextractor import Vulnerability
import builder
import multiprocessing as mp
import distutils.dir_util
import os
import signal
import codeql
from lizard import FunctionInfo
import rewrite_pipeline
import json
from typing import Optional

# for vuln in vuln_stream.process():
#     codeql_project = builder.DirectCodeQlProject(vuln.project_name,
#                                                  vuln.repo_url,
#                                                  vuln.commit)
#     codeql_project.build()


def get_db(project_name: str, commit: str,
           repo_url: str) -> Optional[codeql.Database]:
    codeql_project = None
    print("building", project_name, commit)
    codeql_project = builder.DirectCodeQlProject(
        project_name, repo_url, commit
    )
    try:
        codeql_project.build()
    except Exception as e:
        print("error building", project_name, commit)
        print(e)
        # remove databases/{project_name}/{commit} folder if it exists
        if codeql_project is not None \
           and os.path.exists(codeql_project.db_path):
            distutils.dir_util.remove_tree(codeql_project.db_path)
        return None
    print("done building", project_name, commit)
    db = codeql.Database(codeql_project.db_path)
    return db


def save(source: str, report_id: str, commit: str, project_name,
         suffix: str,
         functions: Optional[list[rewrite_pipeline.FileLocation]]=None) \
                 -> None:
    path = 'result/' + report_id + '_' + commit + '_' + project_name \
            + '_' + suffix
    with open(path + '.c', 'w') as f:
        f.write(source)
    if functions is not None:
        with open(path + '.json', 'w') as f:
            json.dump([loc.toDict() for loc in functions], f)


def rewrite_and_save(secure: bool, vuln: gitextractor.Vulnerability) -> bool:
    if secure:
        assert vuln.sec_commit is not None
        commit = vuln.sec_commit
    else:
        commit = vuln.vuln_commit

    database = get_db(vuln.project_name, commit, vuln.repo_url)

    if database is None:
        print('Failed to build database')
        return False

    print('continue to rewrite')
    diff = vuln.vuln_diff
    fi = list(diff.get_changed_functions(before=(not secure)))[0]
    print(f'Rewriting {fi.name} (secure={secure})')
    if secure:
        src = diff.file_after
    else:
        src = diff.file_before
    src = src.splitlines()[fi.start_line-1:fi.end_line]
    pipeline = rewrite_pipeline.RewritePipeline(src, fi, database)
    srcl = pipeline.rewrite()

    pre = 'secure_' if secure else 'vuln_'

    save('\n'.join(srcl), vuln.report_id, commit, vuln.project_name,
         pre + 'rewritten', functions=list(pipeline.included))
    save('\n'.join(src), vuln.report_id, commit, vuln.project_name,
         pre + 'unmodified', functions=list(pipeline.included))
    return True


def process_contrastive(vuln: gitextractor.Vulnerability) -> bool:
    if rewrite_and_save(False, vuln):
        rewrite_and_save(True, vuln)
    else:
        return False
    return True


def process_vuln_only(vuln: gitextractor.Vulnerability) -> bool:
    return rewrite_and_save(False, vuln)


def process_vuln(vuln: gitextractor.Vulnerability) -> tuple[bool, str]:
    if vuln.sec_commit is not None:
        return process_contrastive(vuln), vuln.project_name
    else:
        return process_vuln_only(vuln), vuln.project_name


# TOOO(liam) fix hacky signal handling 
pool = None


def signal_handler(sig, frame):
    print("Caught SIGNING signal")
    # kill all subprocesses
    if pool is None:
        exit(0)
    pool.terminate()
    print("terminated pool")
    pool.close()
    print("closed pool")
    children = mp.active_children()
    # send sigkill to all subprocesses
    for child in children:
        print("sending sigint to child")
        child.kill()
    exit(0)


signal.signal(signal.SIGINT, signal_handler)

failed_counts = {}
def should_be_ignored(project_name: str) -> bool:
    return project_name in failed_counts and failed_counts[project_name] >= 5

def store_result(x: tuple[bool, str]) -> None:
    global failed_counts
    if not x[0]:
        if x[1] not in failed_counts:
            failed_counts[x[1]] = 0
        failed_counts[x[1]] += 1


def main() -> None:
    num_processes = int(os.cpu_count() * 2/3)
    with mp.Pool(processes=num_processes) as ppool:
        global pool
        pool = ppool
        for i, vuln in enumerate(vuln_stream.process()):
            if should_be_ignored(vuln.project_name) or vuln.project_name != "ghostscript":
                print("ignoring", vuln.project_name)
                continue
            print("submitting", i, vuln.project_name)
            ppool.apply_async(process_vuln, args=(vuln,), callback=store_result)
        ppool.close()
        ppool.join()

if __name__ == "__main__":
    main()
