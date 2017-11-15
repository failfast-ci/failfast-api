
# Failfast-ci API server

Trigger gitlab build from github events

## Features


## Contribute

### Code-style

The project is using flake8, pylint, yapf and mypy.
To automatically format and lint run the commands:

```
make prepare
```

or only lint:
```
make check
```

### Modify the CI jobs
The `.gitlab-ci.yml` is generated from the `.gitlab-ci.jsonnet`

To add or modify the jobs edit the `.gitlab-ci.jsonnet` or the files in the `.gitlab-ci` directory and generate the yaml file it requires https://github.com/failfast-ci/ffctl

```
# pip install ffctl
make gen-ci
```
