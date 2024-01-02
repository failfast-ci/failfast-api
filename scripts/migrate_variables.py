import sys

from ffci.gitlab.client import GitlabClient


def migrate_variables(project_source_id, project_target_id):
    client = GitlabClient()
    variables = client.get_variables(project_source_id)


if __name__ == "__main__":
    src = int(sys.argv[1])
    target = int(sys.argv[2])
    migrate_variables(src, target)
