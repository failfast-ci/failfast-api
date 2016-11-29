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
      appname: "hub2lab-hook",
      namespace: 'default',
      image: "quay.io/ant31/hub2lab-hook:v0.0.1",
      svc_type: "LoadBalancer",
    },

    resources: [
      {
        file: "hub2lab-hook-dp.yaml",
        template: (importstr "templates/hub2lab-hook-dp.yaml"),
        name: "hub2lab-hook",
        type: "deployment",
      },

      {
        file: "hub2lab-hook-svc.yaml",
        template: (importstr "templates/hub2lab-hook-svc.yaml"),
        name: "hub2lab-hook",
        type: "service",
      }
      ],


    deploy: [
      {
        name: "$self",
      },
    ],


  }, params)
