# Getting started

## Create virtualenvironment

```aiignore
python3 -m venv .venv
source .venv/bin/activate
```

## Install nearai

```aiignore
pip install nearai
```

## Run locally

```aiignore
nearai agent interactive -v -a ./0.0.1 --local 
```

## Deploy on agent hub

```aiignore
nearai registry upload ./0.0.1
```