import os
import io
import cairosvg
import pathlib
import textwrap
import mimetypes
import validators
import tempfile
import requests
from urllib.parse import urlsplit
from rich.console import Console
from rich.markdown import Markdown
from enum import Enum
from PIL import Image
import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.cloud import storage

class Gemini:
    """
    A class to manage gemini-pro interaction
    """
    __key:str               # API Key
    __model:object          # model name
    __available:object      # list available models
    __temperature:float     # model temperature
    __candidate_count:int   # reponse candidate max count
    __stop_sequences:list   # stop sequcences
    __max_output_tokens:int # max response lenght in tokes
    __top_k:int             # top_k setting
    __top_p:float           # top_p setting
    __safety:dict           # safety settings
    __chats:[genai.generative_models.ChatSession]
    __questions:list        # questions history
    __tools:list            # configured tools
    __SAFETY_LOW_AND_ABOVE = {
    glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_LOW_AND_ABOVE',
    glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_LOW_AND_ABOVE',
    glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_LOW_AND_ABOVE',
    glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_LOW_AND_ABOVE',
    }
    __SAFETY_MEDIUM_AND_ABOVE = {
    glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_MEDIUM_AND_ABOVE',
    glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_MEDIUM_AND_ABOVE',
    glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_MEDIUM_AND_ABOVE',
    glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_MEDIUM_AND_ABOVE',
    }
    __SAFETY_ONLY_HIGH = {
    glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_ONLY_HIGH',
    glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_ONLY_HIGH',
    glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_ONLY_HIGH',
    glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_ONLY_HIGH',
    }
    __SAFETY_NONE = {
    glm.HarmCategory.HARM_CATEGORY_DANGEROUS.name         : 'BLOCK_NONE',
    glm.HarmCategory.HARM_CATEGORY_SEXUAL.name            : 'BLOCK_NONE',
    glm.HarmCategory.HARM_CATEGORY_HARASSMENT.name        : 'BLOCK_NONE',
    glm.HarmCategory.HARM_CATEGORY_HATE_SPEECH.name       : 'BLOCK_NONE',
    glm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.name : 'BLOCK_NONE',
    glm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.name : 'BLOCK_NONE',
    }

    @property
    def key(self):
        """Return API key"""
        return self.__key
    @property
    def model(self):
        """Return model"""
        return self.__model
    @property
    def available_models(self):
        """Return model"""
        return self.__available
    @property
    def temperature(self):
        """Return model temperature setting"""
        return self.__temperature
    @property
    def top_k(self):
        """Return model top_k setting"""
        return self.top_k
    @property
    def top_p(self):
        """Return model top_p setting"""
        return self.__top_p
    @property
    def tools(self):
        """Return model tools"""
        return self.__tools
    @property
    def max_output_tokens(self):
        """Return max output tokens setting"""
        return self.__max_output_tokens
    @property
    def candidate_count(self):
        """Return candidate response count setting"""
        return self.__candidate_count
    @property
    def stop_sequences(self):
        """Return stop sequences setting"""
        return self.__stop_sequences
    @property
    def config(self):
        """Return configuration structure"""
        return self.__config
    @property
    def safety(self):
        """Return safety settings"""
        return  self.__safety
    @property
    def messages(self):
        """Return model"""
        return self.__messages
    @property
    def questions(self, *, raw=True):
        """Return model"""
        if raw:
            return self. __questions
    @property
    def print_questions(self, selector = [-1] ):
        """pretty print questions"""
        console = Console()
        for question in self. __questions[selctor]:
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

    def __init_key(self, **kwargs):
        self.__key = None
        try:
            self.__key = key
        except NameError:
            pass
        try:
            self.__key  = os.environ[var]
        except (NameError, KeyError):
            pass
        try:
            with open(file, 'r', errors='strict') as f:
                self.__key = f.read().strip()
        except (NameError, FileNotFoundError):
            pass
        try:
            self.__key  = os.environ['google_api_key']
        except KeyError:
            pass
        try:
            with open('/home/thales/.ssh/GOOGLE_GENAI_API_KEY', 'r') as f:
                self.__key = f.read().strip()
        except FileNotFoundError:
            pass
        try:
            genai.configure(api_key=self.__key)
        except:
            raise ValueError(f"could not setup API keys")


    def __init_temperature(self, value : float):
        """ The randomness of the output """
        if 0.0 > value or 1.0 < value:
            raise ValueError(f"temperature must be float() in range 0.0 to 1.0")
        self.__temperature = value

    def __init_max_output_tokens(self, max_output_tokens:int):
        """ The response lenght setting in tokens"""
        if max_output_tokens < 0:
            raise ValueError(f"max tokens > 0 but given: {max_output_tokens}")
        self.__max_output_tokens = max_output_tokens

    def __init_candidate_count(self, candidate_count : int):
        """ The number of response candidates to generate """
        if candidate_count < 0:
            raise ValueError(f"candidate_count > 0 but given: {candidate_count}")
        self.__candidate_count = candidate_count

    def __init_stop_sequences(self, *sequences:str|list):
        """ The stop sequences setting"""
        if isinstance(sequences,str):
            self.__stop_sequences = []
            self.__stop_sequences.append(sequences)
            return
        self.__stop_sequences = [ seq for seq in  sequences ]

    def __init_top_k(self, k : int):
        """ The maximum number of tokens to consider when sampling.
            Top-k sampling considers the set of top_k most probable tokens.
        """
        if k < 0.0:
            raise ValueError(f"k > 0 but given: {k}")
        self.__top_k = k

    def __init_top_p(self, top_p : float):
        """ The cumulative probability of tokens to consider when sampling.
        """
        if top_p < 0.0 or 1.0 < top_p:
            raise ValueError(f"top_p must be 0.0 - 1.0 but was given {top_p}")
        self.__top_p = top_p

    def __init_model(self, *,
                      model : str             = 'gemini-pro',
                      temperature : float     = None,
                      candidate_count : int   = None,
                      stop_sequences:str|list = None,
                      max_output_tokens : int = None,
                      top_k : int             = None,
                      top_p : float           = None,
                      safety: object          = None):

        self.__available = [ m for m in genai.list_models() ]

        if not model in { m.name.lstrip('models/') for m in self.__available }:
            raise ValueError(f"Model '{model}' not found")

        for m in self.__available:
            if m.name.lstrip('models/') == model:
                current_model = m
                break

        if not candidate_count :
            candidate_count    = 1
        if not temperature :
            temperature        = float(current_model.temperature)
        if not max_output_tokens :
            max_output_tokens  = int(current_model.output_token_limit)
        if not top_k :
            top_k              = int(current_model.top_k)
        if not top_p :
            top_p              = float(current_model.top_p)
        if not safety:
            safety             = self.__SAFETY_NONE
        if isinstance(stop_sequences, str):
            stop_sequences = [ stop_sequences ]
        if not stop_sequences:
            stop_sequences = []
        self.__init_temperature(temperature)
        self.__init_candidate_count(candidate_count)
        self.__init_max_output_tokens(max_output_tokens)
        self.__init_stop_sequences(stop_sequences)
        self.__init_top_k(top_k)
        self.__init_top_p(top_p)
        self.__config = glm.GenerationConfig(
                    temperature         = self.__temperature,
                    candidate_count     = self.__candidate_count,
                    max_output_tokens   = self.__max_output_tokens,
                    top_k               = self.__top_k,
                    top_p               = self.__top_p
                    )
        self.__init_safety( safety_settings = safety)
        self.__model     = genai.GenerativeModel(
            model_name        = current_model.name,
            safety_settings   = self.safety,
            generation_config = self.config,
        )

    def __init_safety(self, safety_settings : glm.SafetySetting = None):
        if not safety_settings:
            self.__safety = self.__SAFETY_NONE
            return
        self.__safety = safety_settings

    def __get_url(self, url:str):
        r = requests.get(url, stream=True)
        r.raise_for_status()
        contenttype = r.headers.get('Content-Type')
        mimetype, _ = mimetypes.guess_type(url)
        print(f"MIME TYPES: {mimetype} {contenttype}")
        if mimetype.startswith('image/'):
            print("IMAGE DETECTED")
            with tempfile.NamedTemporaryFile( delete = False ) as fp:
                try:
                    print("IMAGE OPENING")
                    img = Image.open(io.BytesIO(r.content))
                    print("IMAGE RETURNED")
                    return img
                except Exception as exc:
                    print("CAUGTH OPENING : {exc.__name__} ")
                    pass
                try:
                    img = Image.open(cairosvg.svg2png(r.content))
                    print("IMAGE RETURNED")
                    return img
                except:
                    print("CAUGTH OPENING : {exc.__name__} ")
                    pass
        if mimetype.startswith('text/'):
            print("TEXT DECTECTED, RETURNING")
            return r.text
        if mimetype.startswith('application/json'):
            print("JSON DECTECTED, RETURNING")
            return r.text
        print("UNSUPPPORTED, RAISING")
        raise ValueError(f"Unpported types MIME:{mimetype}:{contenttype} in url {url}")

    def __make_prompt(self, *args):
        prompt = []
        for arg in list(*args):
            if Image.isImageType(arg):
                    prompt.append(img)
                    continue
            if isinstance(arg, str):
                if os.path.isfile(arg):
                    print("PATH DETECTED")
                    try:
                        img = Image.open(arg.strip())
                        prompt.append(img)
                        print("IMAGE APPENDED")
                        continue
                    except:
                        pass
                if validators.url(arg):
                    print("URL DETECTED")
                    try:
                        cont = self.__get_url(arg)
                        prompt.append(cont)
                        continue
                    except:
                        print("URL FETCH FAILED")
                        pass
                try:
                    print("APPENDING TEXT")
                    prompt.append(arg)
                    continue
                except:
                    pass
                    print("NOT TEXT")
                raise ValueError(f"Argument of invalid type: type({type(arg)}) : {arg}")
        print("EXITING MAKE PROMPT")
        return prompt

    def ask(self, *args):
        """Standalone questions"""
        print("CALLING MAKE PROMPT")
        prompt   = self.__make_prompt(args)
        print("CALLING GENERATE CONTENT")
        response = self.__model.generate_content( prompt )
        self.__questions.append(prompt)
        self.__questions.append(response)
        try:
            console = Console()
            console.print(Markdown(response.text))
            del console
        except ValueError:
            return response.prompt_feedback

    def start_chat(self):
        """Creates a new chat"""
        chat = self.model.start_chat()
        self.__chats.append(chat)

    def chat(self, *args, chat=-1):
        """Turns conversation"""
        prompt  = self.__make_prompt(args)
        history = self.__messages
        history.append({'role':'user' ,'parts': prompt.parts  })
        response = self.__make_response(history)
        try:
            Console.print(Markdown(response.text))
            self.__messages.append({'role':'model','parts': response.text })
            self.__messages.append({'role':'user' ,'parts': prompt.parts  })
        except ValueError:
            return response.prompt_feedback

    def __init__(self, *,
                 key: dict = None,
                 model: str = None,
                 temperature:float = None,
                 candidate_count:int = None,
                 stop_sequences:list = None,
                 max_output_tokens:int = None,
                 top_p:float = None,
                 top_k:int = None,
                 safety:object = None):
        self.__init_key( key = key )
        self.__init_model(
            model = model,
            temperature = temperature,
            candidate_count = candidate_count,
            max_output_tokens = max_output_tokens,
            stop_sequences = stop_sequences,
            top_p = top_p,
            top_k = top_k,
            safety = safety
        )
        self.__questions = []
        self.__messages  = []


