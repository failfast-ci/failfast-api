
# Failfast-ci API server

Trigger gitlab build from github events

## Installation

### GitHub Configuration

To configure GitHub to use failfast-ci, add an application through _"Developer Settings"_, _"GitHub Apps"_.

1. Create _"New GitHub App"_
1. Give the app a name.
1. Add a homepage url. I use the url for our fork of failfast-ci.
1. Set the _"Webhook URL"_ to `http[s]://<your api server hostname>/api/v1/github_event`.
1. Add permissions:
   * Repository Administration: Read
   * Commit statuses: Read and Write
   * Deployments: Read and Write
   * Issues: Read and Write
   * Pull Requests: Read and Write
   * Repository Contents: Read and Write
   * Organization Members: Read
1. Subscribe to events:
   * Label
   * Repository
   * Deployment
   * Pull Request
   * Commit comment
   * Delete
   * Push
   * Public
   * Status
   * Deployment status
   * Pull request review
   * Pull request review comment
   * Create
   * Release
1. _"Where can this GitHub App be installed?"_

   Unless you want to make this app and its connected services available to the entirety of GitHub, set this to _"Only on this account"_.

1. Click _"Create GitHub app"_
1. Click _"Generate Private Key"_. This will download a PEM file. Make a note of its filename and download location.
1. Make a note of the GitHub Application ID found under the _"About"_ header labeled _"ID"_.

_Note:_ If you're going to install failfast-api via helm, you'll need to double base64 encode the PEM file downloaded above, eg.:

   ```
   base64 -w0 <filename.pem> | base64 -w0 > /tmp/pemb64.b64
   ```

### GitLab Configuration

To configure GitLab to use failfast-ci, add a robot user, a group, and make the robot a maintainer of the group.

1. From the _"Users"_ section of the _Admin Area_ create a _"New User"_.
1. Give it a _"Name"_, _"User Name"_, and _"Email"_.

   Note: with many email systems you can use an existing email address with the "+" notation for adding additional "sub-email" addresses, eg. `gitlab_admin+robot1@domain.dom`.

1. Uncheck _"Can Create Group"_.
1. _"Create User"_
1. Click on the _"Impersonation Tokens"_ heading.
1. Add a name for the application that will use this token, eg. `failfast-ci`. This name is an arbitrary string.
1. Check both _"api"_ and _"read_user"_.
1. Click _"Create impersonation token"_.
1. Save the Token shown for configuration.

## Features

## Contribute

### Code-style

The project is using flake8, pylint, yapf and mypy.
To automatically format and lint run the commands:

```bash
make prepare
```

or only lint:

```bash
make check
```

### Modify the CI jobs

The `.gitlab-ci.yml` is generated from the `.gitlab-ci.jsonnet`

To add or modify the jobs edit the `.gitlab-ci.jsonnet` or the files in the `.gitlab-ci` directory and generate the yaml file it requires https://github.com/failfast-ci/ffctl

``` bash
pip install ffctl
make gen-ci
```
