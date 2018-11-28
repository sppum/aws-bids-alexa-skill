# VirtualEnv vars
SERVICE ?= users
VENV := ${SERVICE}/.venv
VENV_LIBS := $(VENV)/lib/python3.6/site-packages

# help credit (https://gist.github.com/prwhite/8168133)
help: ## Show this help

	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

target: help

	exit 0

clean: ## -> Deletes current virtual env environment

	$(info "[-] Who needs all that anyway? Destroying environment....")
	rm -rf ./$(VENV)
	rm -rf ./$(SERVICE)/dev
	rm -rf ./*.zip

build-dev: _check_service_definition ## -> creates dev folder and install dependencies (requirements.txt) into dev/ folder

	echo "[+] Cloning ${SERVICE} directory structure to ${SERVICE}/dev"
	rsync -a -f "+ */" -f "- *" -f "- dev/" ${SERVICE}/ ${SERVICE}/dev/
	echo "[+] Cloning source files from ${SERVICE} to ${SERVICE}/dev"
	find ${SERVICE} -type f \
			-not -name "*.pyc" \
			-not -name "*__pycache__" \
			-not -name "requirements.txt" \
			-not -name "event.json" \
			-not -name "dev" | cut -d '/' -f2- > .results.txt
	@while read line; do \
		ln -f ${SERVICE}/$$line ${SERVICE}/dev/$$line; \
	done < .results.txt
	echo "[+] Installing dependencies into dev/"
	pip3.6 install \
		--isolated \
		--disable-pip-version-check \
		-Ur $(SERVICE)/requirements.txt -t ${SERVICE}/dev/

_check_service_definition:

	echo "[*] Checking whether service $(SERVICE) exists..."

# SERVICE="<name_of_service>" must be passed as ARG for target or else fail
ifndef SERVICE
	echo "[!] SERVICE argument not defined...FAIL"
	echo "[*] Try running 'make <target> SERVICE=<service_name>'"
	exit 1
endif

ifeq ($(wildcard $(SERVICE)/.),)
	echo "[!] $(SERVICE) folder doesn't exist"
	exit 1
endif

ifeq ($(wildcard $(SERVICE)/requirements.txt),)
	echo "[!] Pip requirements file missing from $(SERVICE) folder..."
	exit 1
endif

run-dev: ## -> Run SAM Local API GW
	sam local start-api --skip-pull-image
