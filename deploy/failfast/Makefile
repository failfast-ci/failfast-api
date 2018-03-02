ifeq ($(GOBIN),)
GOBIN :=${GOPATH}/bin
endif
env := overlay

all: inflate

kinflate:
	go get k8s.io/kubectl/cmd/kinflate

$(GOBIN)/kinflate: kinflate

new-overlay:
	cp -r instance $(env)

inflate:
	kinflate inflate -f $(env)


.PHONY: all inflate new-overlay
