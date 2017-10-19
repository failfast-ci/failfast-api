local utils = (import "jpy-utils.libsonnet");
local docker = utils.docker;

{
  local job_tags = { tags: ['kubernetes'] },
  dockerBuild(image, cache=false, args={}, extra_opts=[]):: {
    // base job to manage containers (build / push)
    image: "docker:git",
    services: ["docker:dind"],
    variables: {
      DOCKER_DRIVER: "overlay2",
      DOCKER_HOST: "tcp://localhost:2375",
    },
    before_script: ["docker info"] +
                   docker.login(image.creds.host, image.creds.username, image.creds.password),
    script: docker.build_and_push(image.name,
                                  cache=cache,
                                  args=args,
                                  extra_opts=extra_opts),

  } + job_tags,

}
