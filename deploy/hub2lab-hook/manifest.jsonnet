local kpm = import "kpm.libsonnet";

function(
  params={}
)

  kpm.package({
    package: {
      name: "ant31/hub2lab-hook",
      expander: "jinja2",
      author: "Antoine Legrand",
      version: "0.1.2-1",
      description: "hub2lab-hook",
      license: "Apache 2.0",
    },

    variables: {
      ingress_class: "nginx",
      ingress_host: "events.failfast-ci.io",
      namespace: 'default',
      image: "quay.io/ant31/hub2lab-hook:v0.1.2",
      svc_type: "ClusterIP",
      appname: "failfast-ci",
      svc_port: 5000,

      gitlab_user: "failfastci-bot",
      gitlab_token: "azSYob1pZ_cyAgZkjbe-",
      gitlab_namespace: "failfast-ci",
      github_context: "gitlab-ci",
      integration_id: "743",

      celery_broker: "redis://redis.%s.svc.cluster.local:6379" % $.variables.namespace,
      celery_backend: $.variables.celery_broker,

      storage_class: "heketi",
    },

    resources: [
      {
        file: "redis-server.yaml",
        template: (importstr "templates/redis.yaml"),
        name: "redis",
        type: "deployment",
      },
      {
        file: "redis-server-svc.yaml",
        template: (importstr "templates/redis-svc.yaml"),
        name: "redis",
        type: "svc",
      },

      {
        file: "failfast-server.yaml",
        template: (importstr "templates/failfast-server.yaml"),
        name: $.variables.appname,
        type: "deployment",
      },

      {
        file: "failfast-worker.yaml",
        template: (importstr "templates/failfast-worker.yaml"),
        name: $.variables.appname + "-worker",
        type: "deployment",
      },

      {
        file: "failfast-svc.yaml",
        template: (importstr "templates/failfast-svc.yaml"),
        name: $.variables.appname,
        type: "service",
      },
      {
        file: "failfast-flower-svc.yaml",
        template: (importstr "templates/failfast-flower-svc.yaml"),
        name: "ff-flower",
        type: "service",
      },
      {
        file: "failfast-flower.yaml",
        template: (importstr "templates/failfast-flower.yaml"),
        name: "ff-flower",
        type: "deployment",
      },

      {
        file: "failfast-ingress.yaml",
        template: (importstr "templates/ingress.yaml"),
        name: $.variables.appname,
        type: "ingress",
      },
      {
        file: "failfast-ff-ingress.yaml",
        template: (importstr "templates/ingress-flower.yaml"),
        name: "ff-flower",
        type: "ingress",
      },

      {
        file: "failfast-secret.yaml",
        template: (importstr "templates/failfast-secret.yaml"),
        expander: "none",
        name: $.variables.appname,
        type: "secret",
      },
    ],


    deploy: [
      {
        name: "base/persistent-volume-claims",
        shards: [{ name: "redis-1" }, { name: "flower-1" }],
        variables: {
          storage_class: $.variables.storage_class,
        },
      },

      {
        name: "$self",
      },
    ],


  }, params)
