# Deploy with [kinflate](https://github.com/kubernetes/kubectl/tree/master/cmd/kinflate)

## kinflate Installation

### Overview

`kinflate` is a command line interface to manage Kubernetes Application configuration.

### Installation

`kinflate` is written in Go and can be installed using `go get`:

<!-- @installKinflate @test -->
```shell
go get k8s.io/kubectl/cmd/kinflate
```

After running the above command, `kinflate` should get installed in your `GOPATH/bin` directory.

## Create an overlay

The common resources are in base-package.
The base-package doesn't include the `integration_pem` secret nor the `failfast-ci` configmap.

An example is provided.

```
cp -r instance prod
```
then edit:
 - `prod/configmaps/failfast-ci.yaml`
 - `prod/secrets/integration_pem`


## Deploy the resources
### Expand and verify resources

```
kinflate inflate -f prod
```

### Deploy

```
kinflate inflate -f prod | kubectl --namespace failfast-ci -f -
```
