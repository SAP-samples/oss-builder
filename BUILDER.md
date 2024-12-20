# Problematic cases:

## pdfbox

```
RUN git clone --depth 1 https://github.com/apache/pdfbox/ $SRC/project-parent/pdfbox
```

## spring-shell

```
RUN git clone --depth 1 https://github.com/spring-projects/spring-shell.git spring-shell     # or use other version control
```

# psqlparse

```
RUN git clone https://github.com/alculquicondor/psqlparse && \
    cd psqlparse && \
    git submodule update --init
```

## proj4

```
21:RUN git clone --depth 1 https://github.com/OSGeo/PROJ PROJ
23:RUN git clone --depth 1 https://github.com/curl/curl.git PROJ/curl
25:RUN git clone --depth 1 https://gitlab.com/libtiff/libtiff.git PROJ/libtiff
```
