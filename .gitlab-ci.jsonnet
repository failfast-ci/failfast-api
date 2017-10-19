local utils = import "jpy-utils.libsonnet";
local baseJobs = import ".gitlab-ci/jobs.libsonnet";
local vars = import ".gitlab-ci/vars.libsonnet";


local stages = utils.extStd.set([
  "build_image",
]);

local jobs = {
  // All the CI jobs

  build_image: baseJobs.dockerBuild(vars.images.failfast) +
               {
                 stage: stages.build_image,
               } + utils.gitlabCi.onlyMaster,

  build_image_branche: self.build_image +
                       utils.gitlabCi.onlyBranch +
                       { when: "manual" },
};


{

  variables: {
    FAILFASTCI_NAMESPACE: "failfast-ci",
  },

  stages: std.objectFields(stages),
  cache: { paths: ["cache"] },
} + jobs
