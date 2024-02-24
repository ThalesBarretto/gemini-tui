"""
A class to manage gemini interactions
"""
import os
import io
import mimetypes
import tempfile
import validators
import requests
import cairosvg
from rich.console import Console
from rich.markdown import Markdown
from PIL import Image

# only inside venv
import google.generativeai          as genai
import google.ai.generativelanguage as glm

# From MOST RESTRICTIVE -> TO LESS RESTRICTIVE
_SAFETY_LOW_AND_ABOVE = {
glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_LOW_AND_ABOVE',
glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_LOW_AND_ABOVE',
glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_LOW_AND_ABOVE',
glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_LOW_AND_ABOVE',
}
_SAFETY_MEDIUM_AND_ABOVE = {
glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_MEDIUM_AND_ABOVE',
glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_MEDIUM_AND_ABOVE',
glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_MEDIUM_AND_ABOVE',
glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_MEDIUM_AND_ABOVE',
}
_SAFETY_ONLY_HIGH = {
glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_ONLY_HIGH',
glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_ONLY_HIGH',
glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_ONLY_HIGH',
glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_ONLY_HIGH',
}
_SAFETY_NONE = {
glm.HarmCategory.HARM_CATEGORY_DANGEROUS.name         : 'BLOCK_NONE',
glm.HarmCategory.HARM_CATEGORY_SEXUAL.name            : 'BLOCK_NONE',
glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_NONE',
glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_NONE',
glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_NONE',
glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_NONE',
}

_DEFAULT_MODEL = 'gemini-pro'
_DEFAULT_CANDIDATE_COUNT = 1
_DEFAULT_TEMPERATURE = 1.0
_DEFAULT_MAX_OUTPUT_TOKENS = 9999999
_DEFAULT_TOP_K = 32
_DEFAULT_TOP_P = 1
_DEFAULT_STOP_SEQUENCES = []
_DEFAULT_SAFETY = _SAFETY_NONE
_DEFAULT_MESSAGES = []

class Gemini:
    _key:str                 # API Key
    _available_models:object # list available models
    _model:object            # model name
    _tools:list              # configured tools
    _candidate_count:int     # reponse candidate max count
    _config:glm.GenerationConfig # glm.GenerationConfig
    _stop_sequences:list     # stop sequcences
    _temperature:float       # model randomnes
    _max_output_tokens:int   # response max lenght, in tokens
    _top_k:int               # top candidates consideration
    _top_p:float             # max probability nucleus
    _safety:object
    _chats:[ genai.generative_models.ChatSession ]
    _questions:list          # questions history

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, api_key):
        if isinstance(api_key, str):
            if os.path.isfile(api_key):
                with open(api_key, 'r', errors='strict') as f:
                    self._key =  f.read().strip()
        self._key = api_key

    @property
    def available_models(self):
        return self._available_models

    @available_models.setter
    def available_models(self, available_models):
        self._available_models = available_models

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model_name):
        self._available = [ m for m in genai.list_models() ]

        if not model_name in { m.name.lstrip('models/') for m in self._available }:
            raise ValueError(f"Model '{model_name}' not found")
        current_model = None
        for model in self._available:
            if model.name.lstrip('models/') == model_name:
                current_model = model
                break
        if current_model is None:
            print("Model not found: {model_name}")
            raise ValueError
        try:
            new_model = genai.GenerativeModel( model_name = model_name)
            new_model.model_name
        except Exception as exc:
            print(f" Could not create model: {new_model.model_name}")
            raise exc
        else:
            self._model =  new_model
            self.candidate_count     = None
            self.max_output_tokens   = None
            self.temperature         = None
            self.top_p               = None
            self.top_k               = None
            return

    @model.deleter
    def model(self, new_model):
        self._model = None

    @property
    def tools(self):
        return self._tools

    @tools.setter
    def tools(self, tools):
        self._tools = tools

    @tools.deleter
    def tools(self):
        self._tools = []

    @property
    def candidate_count(self):
        return self._candidate_count

    @candidate_count.setter
    def candidate_count(self, candidate_count : int = 1):
        if candidate_count is None:
            self._candidate_count = 1
            return
        if candidate_count < 0:
            raise ValueError(f"candidate_count > 0 (given: {candidate_count})")
        self._candidate_count = candidate_count
        return

    @candidate_count.deleter
    def candidate_count(self):
        self._candidate_count = _DEFAULT_CANDIDATE_COUNT
        return

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, temperature : float):
        if temperature is None:
            for m in self.available_models:
                if m.name == self.model.model_name:
                    self._temperature = m.temperature
                    return
        if 0.0 > temperature or 1.0 < temperature:
            raise ValueError(f"Temperature range 0.0-1.0 (given: {value})")
        self._temperature = temperature
        return

    @temperature.deleter
    def temperature(self):
        self._temperature = _DEFAULT_TEMPERATURE
        return

    @property
    def top_k(self):
        return self._top_k

    @top_k.setter
    def top_k(self, top_k : int):
        if top_k is None:
            for m in self.available_models:
                if m.name == self.model.model_name:
                    self._top_k = m.top_k
                    return
        if top_k < 0.0:
            raise ValueError(f"top_k > 0 but given: {top_k}")
        self._top_k = top_k
        return

    @top_k.deleter
    def top_k(self):
        self._top_k = _DEFAULT_TOP_K
        return

    @property
    def top_p(self):
        return self._top_p

    @top_p.setter
    def top_p(self, top_p : float):
        if top_p is None:
            for m in self.available_models:
                if m.name == self.model.model_name:
                    self._top_p = m.top_p
                    return
        if top_p < 0.0 or 1.0 < top_p:
            raise ValueError(f"top_p must be 0.0 - 1.0 but was given {top_p}")
        self._top_p = top_p
        return

    @top_p.deleter
    def top_p(self):
        self._top_p = _DEFAULT_TOP_P
        return

    @property
    def max_output_tokens(self):
        return self._config.max_output_tokens

    @max_output_tokens.setter
    def max_output_tokens(self, max_output_tokens:int):
        if max_output_tokens is None:
            for m in self.available_models:
                if m.name == self.model.model_name:
                    self._max_output_tokens = m.output_token_limit
                    return
        if max_output_tokens < 0:
            raise ValueError(f"max out tokens must be > 0 (given: {max_output_tokens})")
        self._max_output_tokens = max_output_tokens
        return

    @max_output_tokens.deleter
    def max_output_tokens(self):
        self._max_output_tokens =  _DEFAULT_MAX_OUTPUT_TOKENS
        return

    @property
    def stop_sequences(self):
        return self._stop_sequences

    @stop_sequences.setter
    def stop_sequences(self, sequences:str|list):
        if sequences is None:
            self._stop_sequences = []
            return
        if isinstance(sequences,str):
            self._stop_sequences = [ sequences ]
            return
        return sequences

    @stop_sequences.deleter
    def stop_sequences(self):
        self._stop_sequences = _DEFAULT_STOP_SEQUENCES
        return

    @property
    def config(self):
        return  glm.GenerationConfig(
            candidate_count     = self.candidate_count,
            stop_sequences      = self.stop_sequences,
            max_output_tokenns  = self.max_output_tokens,
            temperature         = self.temperature,
            top_p               = self.top_p,
            tok_k               = self.top_k
        )

    @property
    def safety(self):
        return  self._safety

    @safety.setter
    def safety(self, safety_settings = None):
        if safety_settings is None:
            self._safety =  _SAFETY_NONE
            return
        self._safety = safety_settings
        return

    @safety.deleter
    def safety(self, safety_settings = None):
        self._safety = _DEFAULT_SAFETY
        return

    @property
    def messages(self):
        return self._messages

    @messages.setter
    def messages(self, message):
        self._messages.append(message)
        return

    @messages.deleter
    def messages(self):
        self._messages = _DEFAULT_MESSAGES
        return

    @property
    def questions(self):
        return self._questions

    @questions.setter
    def questions(self, question):
        if isinstance(question, list):
            self._questions.extend(question)
        else:
            self._questions.append(question)

    @questions.deleter
    def questions(self, question):
        self._questions.append(question)
        return

    def print_questions(self, selector: int = -1):
        """pretty print questions"""
        console = Console()
        for question in self. _questions[selector]:
            try:
                question.prompt_feedback # throws
                console.print(Markdown("### *ANSWER*:"))
            except:
                console.print(Markdown("### *QUESTION*:"))
            try: # user is guaranteed to have parts
                console.print(Markdown(question.text))
            except:
                qtext = ""
                for part in question.parts:
                    qtext += part.text
                console.print(Markdown(qtext))
        del console
        return

    def _get_url(self, url:str):
        r = requests.get(url, stream=True)
        r.raise_for_status()
        contenttype = r.headers.get('Content-Type')
        mimetype, _ = mimetypes.guess_type(url)
        print(f"MIME TYPES: {mimetype} {contenttype}")
        if mimetype.startswith('image/'):
            with tempfile.NamedTemporaryFile( delete = False ) as fp:
                try:
                    img = Image.open(io.BytesIO(r.content))
                    return img
                except Exception as exc:
                    print("CAUGTH OPENING : {exc.__name__} ")
                    pass
                try:
                    img = Image.open(cairosvg.svg2png(r.content))
                    return img
                except:
                    pass
        if mimetype.startswith('text/'):
            return r.text
        if mimetype.startswith('application/json'):
            return r.text
        print("UNSUPPPORTED, RAISING")
        raise ValueError(f"Unpported types MIME:{mimetype}:{contenttype} in url {url}")

    def _make_prompt(self, *args):
        prompt = []
        # cast to list for not splitting strings
        for arg in list(args):
            if Image.isImageType(arg):
                prompt.append(img)
                continue
            if isinstance(arg, str):
                if os.path.isfile(arg):
                    try:
                        img = Image.open(arg.strip())
                        prompt.append(img)
                        continue
                    except:
                        pass
                if validators.url(arg):
                    try:
                        cont = self._get_url(arg)
                        prompt.append(cont)
                        continue
                    except:
                        pass
                try:
                    prompt.append(arg)
                    continue
                except:
                    pass
                raise ValueError(f"Argument of invalid type: type({type(arg)}) : {arg}")
        return prompt

    def ask(self, *args):
        """Standalone questions"""
        prompt   = self._make_prompt(*args)
        response = self.model.generate_content( prompt )
        self._questions.append(prompt)
        self._questions.append(response)
        try:
            console = Console()
            console.print(Markdown(response.text))
            del console
        except ValueError:
            return response.prompt_feedback

    def start_chat(self):
        """Creates a new chat"""
        chat = self.model.start_chat()
        self._chats.append(chat)

    def chat(self, chat:int = -1):
        """Turns conversation"""
        console = Console()
        console.print(Markdown("---"))
        while True:
            console.print("[bold green]USER[/]:")
            try:
                text = input()
                prompt   = self._make_prompt(text)
            except (KeyboardInterrupt, EOFError):
                console.print(Markdown("---"))
                console.print(Markdown("# End of chat"))
                del console
                return
            response = self._chats[chat].send_message(prompt)
            try:
                console.print("\n[bold red]MODEL[/]:")
                console.print(Markdown(response.text))
                console.print(Markdown("---"))
            except ValueError:
                console.print(Markdown("## *RESPONSE REFUSED: SEE FEEDBACK*:"))
                console.print(Markdown(response.prompt_feedback))
                console.print(Markdown("---"))
            except (KeyboardInterrupt, EOFError):
                console.print(Markdown("---"))
                console.print(Markdown("# End of chat"))
                break
        del console
        return

    def reconfigure(self, kwargs:dict):
        print(f"RECONFIGURE:{kwargs}")
        if not {'candidate_count', 'stop_sequences', 'max_output_tokens',
                'temperature', 'top_p', 'top_k', 'config'}.issuperset(kwargs):
            raise KeyError(f"Use only supported types: {keywords}")
        if 'config' in kwargs:
            if len(kwargs) > 1:
                raise ValueError("Specifiy config or items, not both")
            if not type(kwargs['config']) == type(glm.GenerationConfig()):
                raise TypeError("config must be glm.GenerationConfig() type")
            return kwargs['config']
        # use setters to get default values
        try:
            self.candidate_count = kwargs['candidate_count']
        except IndexError("fail"):
            pass
        try:
            self.stop_sequences = kwargs['stop_sequences']
        except IndexError("fail"):
            pass
        try:
            self.max_output_tokens = kwargs['max_output_tokens']
        except IndexError("fail"):
            pass
        try:
            self.temperature = kwargs['temperature']
        except IndexError("fail"):
            pass
        try:
            self.top_p = kwargs['top_p']
        except IndexError("failed"):
            pass
        try:
            self.top_k = kwargs['top_k']
        except IndexError("fail"):
            pass

    def set_defaults(self):
        for m in self.available_models:
            if m.name == self.model.model_name:
                self.temperature = m.temperature
                self.top_k = m.top_k
                self.top_p = m.top_p
                self.max_output_tokens = m.output_token_limit
                self.temperature = m.temperature
                return
        raise ValueError("Model not configured")

    def __init__(self, *,
         key: str              = None,
         model: str            = None,
         temperature:float     = None,
         candidate_count:int   = None,
         stop_sequences:list   = None,
         max_output_tokens:int = None,
         top_p:float           = None,
         top_k:int             = None,
         safety:object         = None):
        self.key = key
        self.available_models = [ m for m in genai.list_models() ]
        self.model = model
        self.safety = safety
        self.temperature        = temperature
        self.candidate_count    = candidate_count
        self.stop_sequences     = stop_sequences
        self.max_output_tokens  = max_output_tokens
        self.top_p              = top_p
        self.top_k              = top_k
        self._questions = []
        self._messages  = []
        self._chats     = []
        self.start_chat()

