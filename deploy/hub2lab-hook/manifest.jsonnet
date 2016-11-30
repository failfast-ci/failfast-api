local kpm = import "kpm.libjsonnet";

function(
  params={}
)

kpm.package({
   package: {
      name: "ant31/hub2lab-hook",
      expander: "jinja2",
      author: "Antoine Legrand",
      version: "0.0.1-1",
      description: "hub2lab-hook",
      license: "Apache 2.0",
    },

    variables: {
      ingress_class: "nginx",
      ingress_host: "hub2lab-hook.kpmhub.com",
      namespace: 'default',
      image: "quay.io/ant31/hub2lab-hook:master",
      svc_type: "LoadBalancer",
      appname: "hub2lab-hook",
      svc_port: 5000,

      trigger: "changeme",
      token: "changeme",
      repo: "changeme",
    },

    resources: [
      {
        file: "hub2lab-hook-dp.yaml",
        template: (importstr "templates/hub2lab-hook-dp.yaml"),
        name: $.variables.appname,
        type: "deployment",
      },

      {
        file: "hub2lab-hook-svc.yaml",
        template: (importstr "templates/hub2lab-hook-svc.yaml"),
        name: $.variables.appname,
        type: "service",
      },

      {
        file: "hub2lab-hook-ingress.yaml",
        template: (importstr "templates/ingress.yaml"),
        name: $.variables.appname,
        type: "ingress",
      }
      ],


    deploy: [
      {
        name: "$self",
      },
    ],


  }, params)
