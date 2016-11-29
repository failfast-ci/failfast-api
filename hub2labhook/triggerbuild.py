import os
import requests


def trigger_pipeline(gevent,
                     gitlab_api="https://gitlab.com",
                     gitlab_project=None,
                     gitlab_token=None,
                     trigger_token=None,
                     branch="master"):
    # curl -XPOST --header "PRIVATE-TOKEN: pTy2msgzueqJVjSyuQTv" "https://gitlab.com/api/v3/projects/2081797/trigger/builds" --form token=b2cdcaa47b8e5bee6d827b11e5ae4a --form ref=master --form 'variables[REF]'="da501968e0f778f840aee61274484a7f0b2d82da" --form 'variables[REF_NAME]'="jenkinsfiles" --form 'variables[TARGET_REPO_NAME]'='kubespray/kpm-api'
    variables = {'REF_NAME' => gevent.refname
                 'SOURCE_REPO_NAME' => gevent.repo,
                 'TARGET_REPO_NAME' => gevent.repo,
                 'SHA' => gevent.head_sha
                 }
    if gitlab_project is None:
        gitlab_project = os.environ['GITLAB_PROJECT']

    if gitlab_token is None:
        gitlab_token = os.environ['GITLAB_TOKEN']
    if trigger_token is None:
        trigger_token = os.environ['GITLAB_TRIGGER_TOKEN']
    headers = {"PRIVATE-TOKEN": gitlab_token}
    body = {"token" => trigger_token,
            "ref" => branch,
            "variables" => variables}

    namespace, name = gitlab_project.split("/")
    path = gitlab_api + "/api/v3/projects/%s%%2f%s" %
    project_id = requests.get(
    resp = requests.post(self._url(path),
                         params={"force": str(force).lower()},
                         data=json.dumps(body), headers=self.headers)
    requests.post(
