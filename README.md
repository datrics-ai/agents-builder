# Getting started

This project aims to create a meta-agent that can help you generate and deploy other AI agents using conversation. 
The meta-agent can interact with both public and private APIs, guiding you through the authentication process and securely storing API keys if needed.
Current version can be found on [NEAR AI Hub](https://app.near.ai/agents/kirikiri.near/agents-builder/latest)

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