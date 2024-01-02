from ffci.github.models.check import CheckStatus


def test_checkstatus_pipeline_init(pipeline_hook_data):
    check = CheckStatus(pipeline_hook_data)
    assert check.object == pipeline_hook_data
    assert check.object_kind == "pipeline"
    assert check.conclusion == "failure"
    assert check.completed_at == "2017-12-02T15:49:27Z"
    assert check.object_id == 14650392


def test_checkstatus_build_init(build_hook_data):
    check = CheckStatus(build_hook_data)
    assert check.object == build_hook_data
    assert check.object_kind == "build"
    assert check.conclusion == "success"
    assert check.completed_at == "2018-08-28T14:57:26Z"


def test_checkstatus_build_title(build_hook_data):
    check = CheckStatus(build_hook_data)
    assert check.check_title() == "Build Succeeded"


def test_checkstatus_build_summary(build_hook_data):
    check = CheckStatus(build_hook_data)
    assert (
        check.check_summary()
        == "<img src='https://storage.googleapis.com/kubespray-ci-state/ci-icons/success-64.png'  height='25' style='max-width:100%;vertical-align: -7px;'/>  The <a href='https://gitlab.com/failfast-ci/failfast-ci_failfast-api/builds/92764974'>Build</a> **Succeeded**."
    )


def test_checkstatus_build_text(build_hook_data):
    check = CheckStatus(build_hook_data)
    assert isinstance(check.check_text(), str)


def test_checkstatus_pipeline_title(pipeline_hook_data):
    check = CheckStatus(pipeline_hook_data)
    assert check.check_pipeline_title() == "Pipeline Failed"


def test_checkstatus_pipeline_summary(pipeline_hook_data):
    check = CheckStatus(pipeline_hook_data)
    assert isinstance(check.check_pipeline_summary(), str)


def test_checkstatus_pipeline_text(pipeline_hook_data):
    check = CheckStatus(pipeline_hook_data)
    assert isinstance(check.check_pipeline_text(), str)


def test_checkstatus_pipeline2_text(pipeline_hook2_data):
    check = CheckStatus(pipeline_hook2_data)
    assert isinstance(check.check_pipeline_text(), str)
