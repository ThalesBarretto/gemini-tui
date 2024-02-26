# TUI client for google genai

NOTICE: This is a **simple toy project**.

This project is a simple module in python to interact with Google's generative ai modules.

The purpose is to make it friendly for pythonists that work in the terminal.

If you like it comment, give a thumbs up or send a message.

## How to use it:

You need a google cloud project, see oficial documentation:

- Install create a google cloud project, install gcloud-cli
- Setup gcloud default project, login, defaul-app login
- Get gemini API keys, activate the API in google cloud console

1. Prepare:

- Create a python environment, install dependencies
    ```shell
    cd repository
    python -m venv gemini
    cd gemini
    source bin/activate
    python -m pip install --upgrade pip
    python -m pip install validators requests rich cairosvg pillow
    python -m pip install google \
                          google-cloud \
                          google-generativeai \
                          google-ai-generativelanguage \
                          google-api-core \
                          google-cloud-core \
                          google-auth \
                          google-auth-httplib2 


    ```

The `geminy.py` module should be moved to the virtual folder, like this:

```data
.
└── repository
    └── geminy
        ├── geminy.py
```

2. Inside the virtual environment you've just created, run the python IDLE shell:

```python
from gemini import Gemini
mymodel = Gemini(model='gemini-pro', key='YOUR API KEY HERE')
# To start a chat session:
mymodel.chat() 
# To ask a standalonde question:
mymodel.ask("Your prompt here")
# To change the model
mymodel.model = 'gemini-pro-vision'
# To change the model parameters
mymodel.temperature = 0.7
mymodel.top_k = 24
mymodel.top_p = 0.9
```


