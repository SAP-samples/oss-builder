# OSS-Builder

This repository contains the source code for our tool OSS-Builder, that builds a training dataset for learning-based vulnerability discovery based on [OSS-fuzz](https://github.com/google/oss-fuzz). It uses CodeQL to find the changed function before and after a fix and annotates the function with extra context from the repository, such as the values of known constants, possibly attacker-controlled parameters and many more.

## Usage

### Requirements
- Python >= 3.10
- Pip packages listed in `requirements.txt`
- CodeQL CLI (needs to be on PATH)
- CodeQL (make sure to update `settings.py` with the correct _absolute_ path to the starter workspace)

### Preparation
If `vuln_stream/data` is not yet filled with data, follow the instructions under `vuln_stream/README.md`.

### Generating data
Please first test the correct installation using `query.py`

> python query.py

It should result in two files, `result/1.c` and `result/2.c`. The first file should contain only a single unannotated function, while the second file should contain an annotated function and possibly more relevant functions. If any issues occur during this step, check your installation before proceeding.

Next, you can run the full pipeline

> python main.py

## License
Copyright (c) 2023 SAP SE or an SAP affiliate company. All rights reserved. This project is licensed under the Apache Software License, version 2.0 except as noted otherwise in the [LICENSE](LICENSE) file.