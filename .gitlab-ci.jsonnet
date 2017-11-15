local utils = import "jpy-utils.libsonnet";
local baseJobs = import ".gitlab-ci/jobs.libsonnet";
local vars = import ".gitlab-ci/vars.libsonnet";
local images = vars.images;
local docker = utils.docker;
local stagelist = ["build_image", "tests", "docker_release"];

local stages = {
  "code-style": stagelist[1],
  tests: stagelist[1],
  build_image: stagelist[0],
  docker_release: stagelist[2],
};

local jobs = {
  // All the CI jobs


  'container-release': baseJobs.dockerBuild(images.release.failfast) + utils.gitlabCi.onlyMaster {
    stage: stages.docker_release,
    script: docker.rename(images.ci.failfast.name, images.release.failfast.name) +
            docker.rename(images.ci.failfast.name, images.release.failfast.get_name('alpha')),
  },

  'build-image': baseJobs.dockerBuild(images.ci.failfast) +
                 {
                   stage: stages.build_image,
                 },

  pylint: baseJobs.job {
    before_script+: [
      "pip install pylint",
    ],
    stage: stages["code-style"],
    script: [
      "make pylint",
    ],
  },

  flake8: baseJobs.job {
    before_script+: [
      "pip install flake8",
    ],
    stage: stages["code-style"],
    script: [
      "make flake8",
    ],
  },

  mypy_compile: baseJobs.job {
    before_script+: [
      "pip install mypy",
    ],
    stage: stages["code-style"],
    script: [
      "make mypy",
    ],
  },

  yapf: baseJobs.job {
    before_script+: [
      "pip install yapf",
    ],
    stage: stages["code-style"],
    script: [
      "make yapf-diff",
    ],
  },

  'unit-tests': baseJobs.job {
    before_script+: [
      "pip install -r requirements_test.txt",
    ],
    stage: stages.tests,
    script: [
      "make test",
    ],
  },
};


{

  variables: {
    FAILFASTCI_NAMESPACE: "failfast-ci",
  },

  stages: stagelist,
  cache: { paths: ["cache"] },
} + jobs
