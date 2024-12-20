#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeQL for Python.
"""

from typing import Union

import codeql
from .common import temporary_file, run, temporary_query_file
import os


class Query:
    def __init__(self, path):
        """
        Arguments:
        path -- Location of the query file
        """
        # Temporaries will be cleaned up on destructor
        self.path = path

    def __del__(self):
        os.remove(self.path)

    # Helpers
    def run_command(self, command: str, options:list[str]=[],
                    post:list[str]=[]):
        run(['query', command] + options + [self.path] + post)

    @staticmethod
    def from_source(code):
        path = temporary_query_file()
        with open(path, mode='w') as f:
            f.write(code)
        return Query(path)

    @staticmethod
    def from_file(path):
        return Query(path)

    # Interface
    def compile(self):
        """
        Compile or check QL code.

        Compile one or more queries. Usually the main outcome of this command
        is that the compiled version of the query is written to a compilation
        cache where it will be found when the query is later executed.
        Other output options are mostly for debugging.
        """
        self.run('compile')

    def run(self, database: Union[str, codeql.Database], output=None):
        """
        Run a single query.

        This command runs single query against a CodeQL database or raw QL
        dataset.

        By default the result of the query will be displayed on the terminal in
        a human-friendly rendering. If you want to do
        further processing of the results, we strongly recommend using the
        --output option to write the results to a file in an
        intermediate binary format, which can then be unpacked into various
        more machine-friendly representations by CodeQL
        bqrs decode.

        If your query produces results in a form that can be interpreted as
        source-code alerts, you may find CodeQL database
        analyze a more convenient way to run it. In particular, CodeQL database
        analyze can produce output in the SARIF format, which can be used with
        an variety of alert viewers.
        """
        # Return temporary results if no output is specified
        if output is None:
            output = temporary_file(suffix='.bqrs')
        # Obtain actual path to database
        if isinstance(database, codeql.Database):
            database = database.path
        # Perform query and return results
        options = ['-o', output, '-d', database]
        self.run_command('run', options)
        return codeql.BQRS(output)
