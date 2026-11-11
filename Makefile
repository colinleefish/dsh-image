IMAGE ?= ghcr.io/colinleefish/dsh-image
DSH_VERSION ?= 0.2.2-rc.1
IMAGE_VERSION ?= $(DSH_VERSION)-r1
NODE_IMAGE ?= docker.io/library/node:24-trixie
PNPM_VERSION ?= 10.15.1
UV_VERSION ?= 0.9.7
PLATFORMS ?= linux/amd64

.PHONY: help build push pull version-check verify smoke up down logs

help:
	@echo "build          Build the local platform image"
	@echo "push           Build and push $(IMAGE):$(IMAGE_VERSION) (refuses overwrite)"
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
		--tag $(IMAGE):$(IMAGE_VERSION) .

push: version-check
	@if docker buildx imagetools inspect $(IMAGE):$(IMAGE_VERSION) >/dev/null 2>&1; then \
		echo "refusing to overwrite existing image tag: $(IMAGE):$(IMAGE_VERSION)" >&2; exit 1; \
	fi
	docker buildx build --platform $(PLATFORMS) \
		--build-arg DSH_VERSION=$(DSH_VERSION) \
		--build-arg IMAGE_VERSION=$(IMAGE_VERSION) \
		--build-arg IMAGE_REVISION=$$(git describe --always --dirty 2>/dev/null || echo unknown) \
		--build-arg NODE_IMAGE=$(NODE_IMAGE) \
		--build-arg PNPM_VERSION=$(PNPM_VERSION) \
		--build-arg UV_VERSION=$(UV_VERSION) \
		--tag $(IMAGE):$(IMAGE_VERSION) --push .

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
