# template_repo
The purpose of this repo is to simply give a template for future repos

## Setup
Add dependencies in pyproject.toml
Also change project name in here
Change the package-folder (template_repo) to the same name

## Create conda environment
- Have miniconda installed as your environment manager
- Create new environment: conda create -n <env_name> python=3.13
- Acticate environment: conda activate <env_name>
- Deactivate: conda deactivate
- Download all packages defined by pyproject.toml: pip install -e.