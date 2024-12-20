To generate 'data/'
```
mkdir data/
gsutil cp gs://osv-vulnerabilities/OSS-Fuzz/all.zip .
unzip all.zip -d data/
rm all.zip
```

Download the schema from: https://github.com/ossf/osv-schema/blob/main/validation/schema.json
