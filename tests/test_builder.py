import unittest
import builder
from dockerfile_parse import DockerfileParser
from dataclasses import dataclass


class TestMiscFunctions(unittest.TestCase):
    def test__repo_host(self):
        test_cases = [
                {'input': 'git://git.ghostscript.com/ghostpdl.git',
                 'output': 'git.ghostscript.com/ghostpdl'},
                {'input': 'https://github.com/Blosc/c-blosc2.git',
                 'output': 'github.com/Blosc/c-blosc2'},
                {'input': 'https://chromium.googlesource.com/chromiumos/\
third_party/adhd',
                 'output': 'chromium.googlesource.com/chromiumos/\
third_party/adhd'}
                 ]
        for test_case in test_cases:
            self.assertEqual(builder._repo_host(test_case['input']),
                             test_case['output'])

    def _target_dir(self):
        test_cases = [
                {'input': 'git clone https://github.com/liblouis/\
liblouis',
                 'output': 'liblouis'},
                {'input': 'git clone   https://github.com/liblouis/\
liblouis',
                 'output': 'liblouis'},
                {'input': 'git clone https://github.com/\
DavidKorczynski/hdf5-files $SRC/hdf5-files',
                 'output': '$SRC/hdf5-files'},
                {'input': 'git clone --single-branch --branch RC_2_0 \
--recurse-submodules https://github.com/arvidn/libtorrent.git',
                 'output': 'libtorrent'}
                 ]
        for test_case in test_cases:
            self.assertEqual(builder._target_dir(test_case['input']),
                             test_case['output'])


@dataclass
class DockerfileTestcase:
    project_name: str
    repo_url: str
    dockerfile: str
    expected: str
    commit: str


dockerfile_testcases = [
        DockerfileTestcase(project_name='pdfbox',
                           repo_url='https://github.com/apache/pdfbox.git',
                           commit='3c88d4436f6bcc26b42470dff34db61efc394e85',
                           dockerfile='''\
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

FROM gcr.io/oss-fuzz-base/base-builder-jvm

RUN curl -L https://archive.apache.org/dist/maven/maven-3/3.6.3/binaries/apache-maven-3.6.3-bin.zip -o maven.zip && \
    unzip maven.zip -d $SRC/maven && \
    rm -rf maven.zip

ENV MVN $SRC/maven/apache-maven-3.6.3/bin/mvn

RUN git clone --depth 1 https://github.com/google/fuzzing && \
    cp fuzzing/dictionaries/pdf.dict $SRC/PDFStreamParserFuzzer.dict && \
    cp fuzzing/dictionaries/pdf.dict $SRC/PDFWriteReadFuzzer.dict && \
    rm -rf fuzzing

# if not set python infra helper cannot be used for local testing

COPY project-parent $SRC/project-parent/

RUN rm -rf $SRC/project-parent/pdfbox
RUN git clone --depth 1 https://github.com/apache/pdfbox/ $SRC/project-parent/pdfbox

COPY build.sh $SRC/
WORKDIR $SRC/\
''',
                           expected='''\
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

FROM gcr.io/oss-fuzz-base/base-builder-jvm

RUN curl -L https://archive.apache.org/dist/maven/maven-3/3.6.3/binaries/apache-maven-3.6.3-bin.zip -o maven.zip && \
    unzip maven.zip -d $SRC/maven && \
    rm -rf maven.zip

ENV MVN $SRC/maven/apache-maven-3.6.3/bin/mvn

RUN git clone --depth 1 https://github.com/google/fuzzing && \
    cp fuzzing/dictionaries/pdf.dict $SRC/PDFStreamParserFuzzer.dict && \
    cp fuzzing/dictionaries/pdf.dict $SRC/PDFWriteReadFuzzer.dict && \
    rm -rf fuzzing

# if not set python infra helper cannot be used for local testing

COPY project-parent $SRC/project-parent/

RUN rm -rf $SRC/project-parent/pdfbox
RUN git clone https://github.com/apache/pdfbox/ $SRC/project-parent/pdfbox && \
cd pdfbox && git checkout 3c88d4436f6bcc26b42470dff34db61efc394e85 && \
cd ..

COPY build.sh $SRC/
WORKDIR $SRC/\
''')
        ]


class TestCompiledProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = 'https://github.com/alculquicondor/psqlparse'
        commit = '72decb854590f70cbc54c549cd033df4a256b68b'
        cls.project = builder.CompiledProject(name='psqlparse',
                                              repo_url=url,
                                              commit=commit)

    def test_local_repo(self):
        self.assertIsNotNone(builder.oss_fuzz_repo)

    def test__dockerfile_path(self):
        with open(self.project._dockerfile_path(), 'r') as f:
            contents = f.read()
        self.assertIn('FROM', contents)

    def dest__modify_dockerfile(self):
        for test_case in dockerfile_testcases:
            project = builder.CompiledProject(name=test_case.project_name,
                                              repo_url=test_case.repo_url,
                                              commit=test_case.commit)
            dockerfile = DockerfileParser()
            dockerfile.content = test_case.dockerfile
            project._modify_dockerfile(dockerfile)
            self.assertEqual(dockerfile.content, test_case.expected)
