* Need to filter vulnerabilities where the fix is not c code, but e.g., config/Makefile
    * e.g., https://github.com/file/file/commit/c8ef8f414952634d217b2b5e19d38b92d0341bc2
* Need to be careful with non-vulnerability fix code in a fixing commit
    * e.g., file has version tracking in the c source: https://github.com/file/file/commit/8c16c9e3c9a82f859c3ed47c34c14eea6a3d7b18
```
#ifndef	lint
FILE_RCSID("@(#)$File: softmagic.c,v 1.239 2016/12/20 03:15:16 christos Exp $")
FILE_RCSID("@(#)$File: softmagic.c,v 1.240 2016/12/20 12:19:25 christos Exp $")
#endif	/* lint */
```
* There can be multiple introduced and fixed commits
    * e.g. OSV-2021-1451, OSV-2022-835
* Not all projects are hosted on GitHub
* A issue may be considered fixed, because something else in the code changed such that OSS-Fuzz can't reproduce the vulnerability.
* Even though there can be multiple fixed commits, fixes may still be incomplete
* Not every fix commit is listed in the dataset
    * https://github.com/libexif/libexif/commit/4f42b6ea0641aaad1bf9835988616c52ac111fc3
* One commit may fix multiple vulnerabilities
    * e.g. https://github.com/libexif/libexif/commit/eb452f533b2d906130a557ced3d6e38d7b064ff9, OSV-2021-1142, OSV-2021-1138
