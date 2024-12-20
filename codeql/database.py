#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeQL for Python.
"""

import os
import shutil
import settings
from typing import Union

import codeql
from .common import run, search_path, temporary_dir

# Constants
CODEQL_QLPACK = '''
name: codeql-python
version: 0.0.0
libraryPathDependencies: {}
'''


class Database(object):
    def __init__(self, path, temp=False):
        """
        Arguments:
        path -- Path of the database
        temp -- Remove database path in destructor
        """
        self.path = path
        self.temp = temp
        self.qldir = settings.query_home
        self.query_results_cache = {}

    def __del__(self):
        if self.temp:
            shutil.rmtree(self.path)

    # Helpers
    def run_command(self, command, options=[], post=[]):
        run(['database', command] + options + [self.path] + post)

    @staticmethod
    def from_cpp(code, command: Union[list[str], None]=None):
        # Get default compiler
        compilers = ['cxx', 'clang++', 'g++', 'cc', 'clang', 'gcc']
        if command is None:
            for compiler in compilers:
                if shutil.which(compiler) is not None:
                    command = [compiler, '-c']
                    break
            else:
                raise RuntimeError('No compiler found')
        # Create database
        directory = temporary_dir()
        fpath = os.path.join(directory, 'source.cpp')
        with open(fpath, 'w') as f:
            f.write(code)
        command.append(fpath)
        return Database.create('cpp', directory, command)

    def query(self, ql: str) -> list[list[str]]:
        """
        Syntactic sugar to execute a CodeQL snippet and parse the results.
        """
        # check if result is already avaiable in cache
        if ql not in self.query_results_cache:
            # need to compute query result
            # unique query path
            query_file = os.path.join(self.qldir, f'query_{id(self)}.ql')
            with open(query_file, mode='w') as f:
                f.write(ql)
            query = codeql.Query(query_file)
            bqrs = query.run(database=self)
            self.query_results_cache[ql] = bqrs.parse()
        return self.query_results_cache[ql]

    # Interface
    @staticmethod
    def create(language, source, command=None, location=None):
        """
        Create a CodeQL database instance for a source tree that can be
        analyzed using one of the CodeQL products.

        Arguments:
        language -- The language that the new database will be used to analyze.
        source -- The root source code directory.
            In many cases, this will be the checkout root. Files within it are
            considered to be the primary source files for this database.
            In some output formats, files will be referred to by their relative
            path from this directory.
        command -- For compiled languages, build commands that will cause the
            compiler to be invoked on the source code to analyze. These
            commands will be executed under an instrumentation environment that
            allows analysis of generated code and (in some cases) standard
            libraries.
        location -- Path to generated database
        """
        # Syntactic sugar: Default location to temporary directory
        if location is None:
            location = temporary_dir()

        # Create and submit command
        args = ['database', 'create', '-l', language, '-s', source]
        if command is not None:
            if isinstance(command, list):
                command = ' '.join(map(lambda x: f'"{x}"' if ' ' in x else x,
                                       command))
            args += ['-c', command]
        args.append(location)
        print(command)
        print(' '.join(args))
        run(args)

        # Return database instance
        return Database(location)

    def analyze(self, queries, format, output):
        """
        Analyze a database, producing meaningful results in the context of the
        source code.

        Run a query suite (or some individual queries) against a CodeQL
        database, producing results, styled as alerts or paths, in SARIF or
        another interpreted format.

        This command combines the effect of the codeql database run-queries
        and codeql database interpret-results commands. If you want to run
        queries whose results don't meet the requirements for being interpreted
        as source-code alerts, use codeql database run-queries or codeql query
        run instead, and then codeql bqrs decode to convert the raw results to
        a readable notation.
        """
        # Support single query or list of queries
        if type(queries) is not list:
            queries = [queries]
        # Prepare options
        options = [f'--format={format}', '-o', output]
        if search_path is not None:
            options += ['--search-path', search_path]
        # Dispatch command
        self.run_command('analyze', options, post=queries)

    def upgrade(self):
        """
        Upgrade a database so it is usable by the current tools.

        This rewrites a CodeQL database to be compatible with the QL libraries
        that are found on the QL pack search path, if necessary.

        If an upgrade is necessary, it is irreversible. The database will
        subsequently be unusable with the libraries that were current when it
        was created.
        """
        self.run_command('upgrade')

    def cleanup(self):
        """
        Compact a CodeQL database on disk.

        Delete temporary data, and generally make a database as small as
        possible on disk without degrading its future usefulness.
        """
        self.run_command('cleanup')

    def bundle(self, output):
        """
        Create a relocatable archive of a CodeQL database.

        A command that zips up the useful parts of the database. This will only
        include the mandatory components, unless the user specifically requests
        that results, logs, TRAP, or similar should be included.
        """
        options = ['-o', output]
        self.run_command('bundle', options)
