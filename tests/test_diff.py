import unittest
from vuln_stream.diff import Diff
import requests
import lizard

def get_file(org, repo, sha, path) -> str:
    base_url = 'https://raw.githubusercontent.com/'
    url = base_url + org + '/' + repo + '/' + sha + path
    r = requests.get(url)
    return r.text


class TestDiff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        org = 'openthread'
        repo = 'openthread'
        sha = '8bb50d4ccde667295f892f976ee5ff90ba4a4a2f'
        path = '/src/core/net/ip6_address.cpp'
        file_before = get_file(org, repo, sha, path)
        sha = '607f7711e60a3abb4257f510f13791b54045bdb8'
        file_after = get_file(org, repo, sha, path)
        cls.diff1 = Diff(path, file_before, file_after)

    def test__get_changed_lines_just_inserts(self):
        lines = self.diff1._get_changed_lines()
        expected = set([318])
        self.assertEqual(lines, expected)

    def test_get_changed_functions(self):
        changed_functions = self.diff1.get_changed_functions()
        for func in changed_functions:
            func: lizard.FunctionInfo
            print(func.name)
