import git
import tempfile
import distutils.dir_util
import urllib.parse
from dockerfile_parse import DockerfileParser
from typing import Any
import os
import subprocess
from abc import ABC, abstractmethod
import shutil
from gitcache import get_repo_at_commit


oss_fuzz_repo_url = 'https://github.com/google/oss-fuzz.git'
oss_fuzz_repo = None


def _repo_host(repo_url: str) -> str:
    """
    removes protocol and ".git" from the repo url

    repo_url: the url of the repo to get the reduced repo url of

    returns: the reduced repo url
    """
    parsed = urllib.parse.urlparse(repo_url)
    return parsed.netloc + (parsed.path[:-len('.git')]
                            if parsed.path.endswith('.git')
                            else parsed.path)


def _target_dir(clone_command: str) -> str:
    """
    gets the target directory of a clone command
    e.g. git clone --depth 1 https://github.com/liblouis/liblouis
    -> liblouis
    git clone --depth 1 https://github.com/DavidKorczynski/hdf5-files \
$SRC/hdf5-files
    -> $SRC/hdf5-files
    git clone --depth 1 https://github.com/taylorhakes/promise-polyfill.git
    -> promise-polyfill
    git clone --depth 1 --single-branch --branch RC_2_0 --recurse-submodules \
https://github.com/arvidn/libtorrent.git
    -> libtorrent

    clone_command: the clone command to get the target directory of

    returns: the target directory
    """
    def is_url(clone_command: str) -> bool:
        return clone_command.startswith('http')\
               or clone_command.startswith('git:')

    def extract_name_from_url(url: str) -> str:
        p = urllib.parse.urlparse(url)
        return os.path.basename(p.path).replace('.git', '')

    command_parts = clone_command.split()
    if is_url(command_parts[-1]):
        return extract_name_from_url(command_parts[-1])
    else:  # assume it is the path
        return command_parts[-1]


class Project(ABC):
    @abstractmethod
    def __init__(self, name: str, repo_url: str, commit: str):
        pass

    @abstractmethod
    def build(self):
        pass


class DirectCodeQlProject(Project):
    name: str
    repo_url: str
    commit: str
    db_path: str

    def __init__(self, name: str, repo_url: str, commit: str):
        self.name = name
        self.repo_url = repo_url
        self.commit = commit
        self.db_path = os.path.abspath(os.path.join('databases',
                                                    self.name, self.commit))

    def build(self):
        repo_at_commit = get_repo_at_commit(self.repo_url,
                                            self.name,
                                            self.commit)\
                .working_dir
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path)
        os.makedirs(self.db_path)
        p = None
        try:
            p = subprocess.check_output(['codeql', 'database', 'create',
                                         self.db_path, '--language', 'cpp'],
                                        cwd=repo_at_commit)

        except subprocess.CalledProcessError as e:
            print(e.stderr)
            print(e.stdout)
            os.rename(self.db_path, self.db_path + '.error')
            with open(os.path.join(self.db_path + '.error', 'error.txt'), 'w') as f:
                f.write(e.output.decode('utf-8'))
                if p is not None:
                    f.write(p.decode('utf-8'))


class CompiledProject(Project):
    name: str
    repo_url: str
    commit: str

    def __init__(self, name: str, repo_url: str, commit: str):
        self.name = name
        self.repo_url = repo_url
        self.commit = commit
        global oss_fuzz_repo
        if oss_fuzz_repo is None:
            tmp_dir = tempfile.mkdtemp()
            oss_fuzz_repo = git.Repo.clone_from(oss_fuzz_repo_url, tmp_dir)
        self.oss_project_dir = os.path.join(oss_fuzz_repo.working_dir,
                                            'projects',
                                            self.name)
        self.build_dir = tempfile.mkdtemp()
        distutils.dir_util.copy_tree(self.oss_project_dir, self.build_dir)

    def _dockerfile_path(self) -> str:
        return os.path.join(self.build_dir, 'Dockerfile')

    def _build_sh_path(self) -> str:
        return os.path.join(self.build_dir, 'build.sh')

    def _is_clone_project_directive(self, directive: dict[str, Any]) -> bool:
        return directive['instruction'] == 'RUN' and \
               directive['value'].startswith('git clone') \
               and _repo_host(self.repo_url) in directive['value']

    def _modify_dockerfile(self,
                           dockerfile: DockerfileParser) -> str:
        # find clone command of project
        for directive in dockerfile.structure:
            if self._is_clone_project_directive(directive):
                value = directive['value']
                start, end = directive['startline'], directive['endline']
                break
        else:
            raise Exception('Could not find clone command of project')
        value = value.replace('\\\n', ' ')
        subcommands = [v.strip() for v in value.split('&&')]
        idx = [i for i, v in enumerate(subcommands)
               if _repo_host(self.repo_url) in v][0]
        subcommands[idx] = subcommands[idx].replace('--depth 1', '')
        target_dir = _target_dir(subcommands[idx])
        new_next_subcommands = [f'cd {target_dir}',
                                f'git checkout {self.commit}',
                                'cd ..']
        subcommands = subcommands[:idx+1] + new_next_subcommands \
            + subcommands[idx+1:]
        new_value = 'RUN ' + ' && \\\n\t'.join(subcommands) + '\n'
        lines = dockerfile.lines
        lines[start:end+1] = [new_value]
        return ''.join(lines)

    def _modify_to_use_commit(self) -> None:
        """
        Modify a Dockerfile to use a specific commit of the project.
        This is done by modifying the Dockerfile in the build directory on
        disk.
        """
        # rewrite the Dockerfile to use the commit
        dockerfile_path = self._dockerfile_path()
        dockerfile = DockerfileParser(dockerfile_path)
        content = self._modify_dockerfile(dockerfile)
        # TODO it is not a good idea to write to the original Dockerfile
        # because it will be messed up for multiple commits
        # but probalby docker layer caching will make this not a big problem
        with open(self._dockerfile_path(), 'w') as f:
            f.write(content)

    def _modify_to_set_fuzzing_env(self) -> None:
        with open(self._dockerfile_path(), 'r') as f:
            content = f.read()
        content += """
ENV 'FUZZING_LANGUAGE'='c++'
ENV 'FUZZING_ENGINE'='afl'
ENV 'ARCHITECTURE'='x86_64'
        """
        with open(self._dockerfile_path(), 'w') as f:
            f.write(content)

    def _build_modifications(self):
        self._modify_to_use_commit()
        self._modify_to_set_fuzzing_env()

    def build(self):
        self._build_modifications()
        current_dir = os.getcwd()
        os.chdir(self.build_dir)
        subprocess.run(['podman', 'build', '-t', self.name, self.build_dir])
        subprocess.run(['podman', 'run', self.name])
        os.chdir(current_dir)


class BuildCodeQLProject(CompiledProject):
    """
    Build the project and build the CodeQL database.
    Right now we are just appending to the current Dockerfile.
    For caching and performance reasons we should probably create a new
    Image and inherit from it.
    """
    def __init__(self, name: str, repo_url: str, commit: str):
        super().__init__(name, repo_url, commit)

    def _inster_after_from(self, to_insert: str) -> None:
        if not to_insert.endswith('\n'):
            to_insert += '\n'
        dockerfile_path = self._dockerfile_path()
        dockerfile = DockerfileParser(dockerfile_path)
        # get the FROM directive
        from_directive = next(filter(lambda x: x['instruction'] == 'FROM',
                                     dockerfile.structure))
        with open(self._dockerfile_path(), 'r') as f:
            content = f.readlines()
        content.insert(from_directive['endline'] + 1, to_insert)
        with open(self._dockerfile_path(), 'w') as f:
            f.write(''.join(content))

    def _modify_to_install_codeql(self) -> None:
        to_insert = """\
RUN curl -L -O https://github.com/github/codeql-cli-binaries/releases/download\
/v2.15.1/codeql-linux64.zip
RUN unzip codeql-linux64.zip
RUN mv codeql /codeql
ENV PATH=$PATH:/codeql
"""
        self._inster_after_from(to_insert)

    def _modify_to_build_codeql_db(self) -> None:
        with open(self._build_sh_path(), 'r') as f:
            content = f.read()
        content = content.replace('$CXX ', '/compiler_mock.py $CXX ')
        content = content.replace('$CC ', '/compiler_mock.py $CC ')
        with open(self._build_sh_path(), 'w') as f:
            f.write(content)
        # TODO is this correct API usage?
        # also distutils is deprecated and should be replaced
        distutils.file_util.copy_file('compiler_mock.py', self.build_dir)
        to_insert = """\
COPY compiler_mock.py /compiler_mock.py
RUN chmod +x /compiler_mock.py
"""
        self._inster_after_from(to_insert)

    def _build_modifications(self):
        super()._build_modifications()
        self._modify_to_install_codeql()
        self._modify_to_build_codeql_db()

    def build(self):
        self._build_modifications()
        current_dir = os.getcwd()
        os.chdir(self.build_dir)
        subprocess.run(['podman', 'build', '-t', self.name, self.build_dir])
        # print docker file
        with open(self._dockerfile_path(), 'r') as f:
            print(f.read())
        subprocess.run(['podman', 'run', '-v', f'{current_dir}/result:/result',
                        self.name])
        os.chdir(current_dir)

# p = CompiledProject(name='libexif',
#                     repo_url='https://github.com/libexif/libexif',
#                     commit='4bd5cd63390731a1473205f9346cd4fcc1b0f668')
# p.build()


# p = DirectCodeQlProject(name='libexif',
#                         repo_url='https://github.com/libexif/libexif',
#                         commit='4bd5cd63390731a1473205f9346cd4fcc1b0f668')
# p.build()
