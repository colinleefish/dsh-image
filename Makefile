# Default local/dev tag; CI also pushes Docker Hub + Aliyun ACR.
IMAGE ?= registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image
DOCKERHUB_IMAGE ?= docker.io/colinleefish/dsh-image
ACR_IMAGE ?= registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image
DSH_VERSION ?= 0.2.2-rc.1
IMAGE_VERSION ?= $(DSH_VERSION)-r5
NODE_IMAGE ?= docker.io/library/node:24-trixie
PNPM_VERSION ?= 10.15.1
UV_VERSION ?= 0.9.7
NPM_REGISTRY ?= https://registry.npmmirror.com
PIP_INDEX_URL ?= https://mirrors.aliyun.com/pypi/simple/
PLATFORMS ?= linux/amd64

.PHONY: help build push pull version-check verify smoke up down logs

help:
	@echo "build          Build the local platform image"
	@echo "push           Build and push ACR + Docker Hub (refuses overwrite)"
	@echo "pull           Pull $(IMAGE):$(IMAGE_VERSION)"
	@echo "version-check  Verify pinned versions across files"
	@echo "verify         version-check"
	@echo "smoke          Run smoke.sh against a local tag"
	@echo "up / down / logs  Compose helpers (needs .env)"

build:
	docker build --pull \
		--build-arg DSH_VERSION=$(DSH_VERSION) \
		--build-arg IMAGE_VERSION=$(IMAGE_VERSION) \
		--build-arg IMAGE_REVISION=$$(git describe --always --dirty 2>/dev/null || echo unknown) \
		--build-arg NODE_IMAGE=$(NODE_IMAGE) \
		--build-arg PNPM_VERSION=$(PNPM_VERSION) \
		--build-arg UV_VERSION=$(UV_VERSION) \
		--build-arg NPM_REGISTRY=$(NPM_REGISTRY) \
		--build-arg PIP_INDEX_URL=$(PIP_INDEX_URL) \
		--tag $(IMAGE):$(IMAGE_VERSION) .

push: version-check
	@if docker buildx imagetools inspect $(ACR_IMAGE):$(IMAGE_VERSION) >/dev/null 2>&1; then \
		echo "refusing to overwrite existing image tag: $(ACR_IMAGE):$(IMAGE_VERSION)" >&2; exit 1; \
	fi
	@if docker buildx imagetools inspect $(DOCKERHUB_IMAGE):$(IMAGE_VERSION) >/dev/null 2>&1; then \
		echo "refusing to overwrite existing image tag: $(DOCKERHUB_IMAGE):$(IMAGE_VERSION)" >&2; exit 1; \
	fi
	docker buildx build --platform $(PLATFORMS) \
		--provenance=false --sbom=false \
		--build-arg DSH_VERSION=$(DSH_VERSION) \
		--build-arg IMAGE_VERSION=$(IMAGE_VERSION) \
		--build-arg IMAGE_REVISION=$$(git describe --always --dirty 2>/dev/null || echo unknown) \
		--build-arg NODE_IMAGE=$(NODE_IMAGE) \
		--build-arg PNPM_VERSION=$(PNPM_VERSION) \
		--build-arg UV_VERSION=$(UV_VERSION) \
		--build-arg NPM_REGISTRY=$(NPM_REGISTRY) \
		--build-arg PIP_INDEX_URL=$(PIP_INDEX_URL) \
		--tag $(ACR_IMAGE):$(IMAGE_VERSION) \
		--tag $(DOCKERHUB_IMAGE):$(IMAGE_VERSION) \
		--push .

pull:
	docker pull $(IMAGE):$(IMAGE_VERSION)

version-check:
	./scripts/check-version-consistency.sh \
		$(DSH_VERSION) $(IMAGE_VERSION) $(PNPM_VERSION) $(UV_VERSION)

verify: version-check

smoke:
	./scripts/smoke.sh $(IMAGE):$(IMAGE_VERSION) $(DSH_VERSION)

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100
