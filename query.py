import sys
import time
from vuln_stream import vuln_stream
from vuln_stream import gitextractor
import codeql
import builder
from lizard import FunctionInfo
import rewrite_pipeline



reports_iter = vuln_stream.extract_suitable_vulns()
commit = '13a2d9e34ffc4170720ce417c73e396d0ac1471a'
test_report = next(filter(
    lambda x: x.project_name == 'lz4'
    and x.fix_commit == commit,
    reports_iter
    ))


info = gitextractor.get_report_info(test_report)
if info is None:
    print("info is None")
    exit(1)

print(f"FOUND test_report {test_report.fix_commit},{info.vuln_commit}")

build_project = builder.DirectCodeQlProject(info.project_name,
                                            info.repo_url,
                                            info.vuln_commit)
build_project.build()
database = codeql.Database(build_project.db_path)

diff = info.vuln_diff
function_infos = diff.get_changed_functions()
for i in function_infos:
    i: FunctionInfo
    print(f"{i.start_line}@{i.filename}")
    start = time.time()
    src = diff.file_before.splitlines()[i.start_line-1:i.end_line]
    with open("result/1.c", "w", encoding="utf8") as f:
        f.write("\n".join(src))
    srcl = rewrite_pipeline.RewritePipeline(src, i, database).rewrite()
    with open("result/2.c", "w", encoding="utf8") as f:
        f.write("\n".join(srcl))
    finished = time.time()
    print(f"finished in {finished - start:.2}s")
    sys.exit(0)