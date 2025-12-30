IMAGE_NAME ?= hello-world
ECR_REGISTRY ?= 853027285987.dkr.ecr.us-east-1.amazonaws.com
TAG ?= latest
AWS_PROFILE ?= orchestera-dev
DOCKER_ARGS ?=

.PHONY: venv build push build-dev push-dev build-jupyter push-jupyter

venv:
	uv sync

build:
	cd .. && docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --load $(DOCKER_ARGS) -f hello-world/Dockerfile .

# make push AWS_PROFILE=some-other-profile
push:
	aws ecr get-login-password --region us-east-1 --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker tag $(IMAGE_NAME):$(TAG) $(ECR_REGISTRY)/$(IMAGE_NAME):$(TAG)
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):$(TAG)

build-jupyter:
	cd .. && docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):jupyter --load $(DOCKER_ARGS) -f hello-world/Dockerfile.jupyter .

push-jupyter:
	aws ecr get-login-password --region us-east-1 --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker tag $(IMAGE_NAME):jupyter $(ECR_REGISTRY)/$(IMAGE_NAME):jupyter
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):jupyter

SERVICE_ACCOUNT ?= spark

# make launch-jupyter-notebook NAMESPACE=prod-app
# make delete-jupyter-notebook NAMESPACE=prod-app
delete-jupyter-notebook:
ifndef NAMESPACE
	$(error NAMESPACE is required. Usage: make delete-jupyter-notebook NAMESPACE=<namespace>)
endif
	-kubectl delete pod jupyter -n $(NAMESPACE)

launch-jupyter-notebook: delete-jupyter-notebook
	kubectl run jupyter --image=$(ECR_REGISTRY)/$(IMAGE_NAME):jupyter --port=8888 --image-pull-policy=Always --overrides='{"spec":{"serviceAccountName":"$(SERVICE_ACCOUNT)","containers":[{"name":"jupyter","image":"$(ECR_REGISTRY)/$(IMAGE_NAME):jupyter","env":[{"name":"ORCH_SPARK_K8S_NAMESPACE","value":"$(NAMESPACE)"}]}]}}' -n $(NAMESPACE)
	@echo "Run: kubectl port-forward pod/jupyter 8888:8888 -n $(NAMESPACE)"

# make port-forward-jupyter-notebook NAMESPACE=prod-app
port-forward-jupyter-notebook:
ifndef NAMESPACE
	$(error NAMESPACE is required. Usage: make port-forward-jupyter-notebook NAMESPACE=<namespace>)
endif
	kubectl port-forward pod/jupyter 8888:8888 -n $(NAMESPACE)
