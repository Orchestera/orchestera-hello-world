IMAGE_NAME ?= hello-world
ECR_REGISTRY ?= 853027285987.dkr.ecr.us-east-1.amazonaws.com
TAG ?= latest
AWS_PROFILE ?= orchestera-dev

.PHONY: venv build push build-dev push-dev build-jupyter push-jupyter

venv:
	uv sync

build:
	cd .. && docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --load -f hello-world/Dockerfile .

# make push AWS_PROFILE=some-other-profile
push:
	aws ecr get-login-password --region us-east-1 --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker tag $(IMAGE_NAME):$(TAG) $(ECR_REGISTRY)/$(IMAGE_NAME):$(TAG)
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):$(TAG)

build-jupyter:
	cd .. && docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):jupyter --load -f hello-world/Dockerfile.jupyter .

push-jupyter:
	aws ecr get-login-password --region us-east-1 --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker tag $(IMAGE_NAME):jupyter $(ECR_REGISTRY)/$(IMAGE_NAME):jupyter
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):jupyter
