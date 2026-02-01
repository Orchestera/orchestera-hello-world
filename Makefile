IMAGE_NAME ?= hello-world
ECR_REGISTRY ?= 
TAG ?= latest
AWS_PROFILE ?= orchestera-dev
DOCKER_ARGS ?=
GHCR_JUPYTER_IMAGE ?= ghcr.io/orchestera/docker-images/jupyter:latest

.PHONY: venv build push build-dev push-dev build-jupyter push-jupyter build-userapp push-userapp

venv:
	uv sync

build:
	cd .. && docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --load $(DOCKER_ARGS) -f hello-world/Dockerfile.spark .

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
	kubectl run jupyter --image=$(ECR_REGISTRY)/$(IMAGE_NAME):jupyter --port=8888 --image-pull-policy=Always --overrides='{"spec":{"serviceAccountName":"$(SERVICE_ACCOUNT)","nodeSelector":{"dedicated":"spark"},"tolerations":[{"key":"dedicated","operator":"Equal","value":"spark","effect":"NoSchedule"}],"containers":[{"name":"jupyter","image":"$(ECR_REGISTRY)/$(IMAGE_NAME):jupyter","env":[{"name":"ORCH_SPARK_K8S_NAMESPACE","value":"$(NAMESPACE)"}]}]}}' -n $(NAMESPACE)
	@echo "Run: kubectl port-forward pod/jupyter 8888:8888 -n $(NAMESPACE)"

# make port-forward-jupyter-notebook NAMESPACE=prod-app
port-forward-jupyter-notebook:
ifndef NAMESPACE
	$(error NAMESPACE is required. Usage: make port-forward-jupyter-notebook NAMESPACE=<namespace>)
endif
	@nohup kubectl port-forward pod/jupyter 8888:8888 -n $(NAMESPACE) > /dev/null 2>&1 &
	@echo "Port forward running in background. Access Jupyter at http://localhost:8888"
	@echo "Run 'make stop-port-forward' to stop"

# Stop port-forward for jupyter
stop-port-forward:
	-pkill -f "kubectl port-forward pod/jupyter 8888:8888"
	@echo "Port forward stopped"

# make launch-prebuilt-jupyter-notebook NAMESPACE=prod-app
launch-prebuilt-jupyter-notebook: delete-jupyter-notebook
	kubectl run jupyter --image=$(GHCR_JUPYTER_IMAGE) --port=8888 --image-pull-policy=Always --overrides='{"spec":{"serviceAccountName":"$(SERVICE_ACCOUNT)","nodeSelector":{"dedicated":"spark"},"tolerations":[{"key":"dedicated","operator":"Equal","value":"spark","effect":"NoSchedule"}],"containers":[{"name":"jupyter","image":"$(GHCR_JUPYTER_IMAGE)","env":[{"name":"ORCH_SPARK_K8S_NAMESPACE","value":"$(NAMESPACE)"}]}]}}' -n $(NAMESPACE)
	@echo "Run: kubectl port-forward pod/jupyter 8888:8888 -n $(NAMESPACE)"

build-userapp:
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):userapp --load $(DOCKER_ARGS) -f Dockerfile.userapp .

push-userapp:
ifndef ECR_REGISTRY
	$(error ECR_REGISTRY is required. Usage: make push-userapp ECR_REGISTRY=<registry>)
endif
	aws ecr get-login-password --region us-east-1 --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker tag $(IMAGE_NAME):userapp $(ECR_REGISTRY)/$(IMAGE_NAME):userapp
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):userapp
