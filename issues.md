This document lists all issues that make it hard to create a dataset for MLVDS. Ideally with real examples to discuss impact.

* Long functions: https://github.com/mruby/mruby/commit/393aaada64a7ec77313ef2516fce1c2052b547c8?diff=split, https://osv.dev/vulnerability/OSV-2023-881
* Crash site (Location where the cash or Sanitizer issue manifests) is not equal bug site (where expectations/contract were violated). This is a hard one
* Missing context
    * Type definition missing
    * Behaviour of function calls unknown
    * Global variables, classes, unknown
    * Can this be solved by (weighted ?) language modelling on the target project?
* Missing build information: Fortify source, OS mitigations, libc versions ... can make a bug unexplainable. However I would still argue, that things that those mitigate are bugs, it might tough be a stretch to call them vulnerability.
* Missing application domain: Sure /bin/bash has arbitrary command injection. Sure the web admin interface can create an entry on the website that XSSes users, ...
* Missing source (and sink) definitions
* Infeasible vulnerability classes.
    * E.g., tor vulnerability that is a logic error in a complex algorithm that leads to anonymity issues CVE-2017-0377 in patchdb `tor_665baf5ed5c6186d973c46cdea165c0548027350__src_or_entrynodes.c_1_1.c`
    * Or even simpler the inner workings of XML parsing, https://github.com/GNOME/libxslt/commit/937ba2a3eb42d288f53c8adc211bd1122869f0bf present in DiverseVul
* Drive-by fixes mixed with a vulnerability fixing commit: https://github.com/gnutls/gnutls/commit/ed51e5e53cfbab3103d6b7b85b7ba4515e4f30c3 present in DiverseVul
