# -*- coding: utf-8 -*-
"""
Griffin LLM Extension for IPython.
This extension adds the %griffin magic command to interact with LLM APIs.
"""

import json
import requests
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.display import display, Markdown

# API key for ArliAI
ARLIAI_API_KEY = "80f1d6aa-f48b-4028-bf90-19edfefead8d"

@magics_class
class GriffinLLMMagics(Magics):
    """Magics for interacting with LLM APIs."""

    @line_magic
    def griffin(self, line):
        """
        Send a query to the LLM API and display the response.
        
        Usage:
            %griffin What is the capital of France?
        """
        if not line.strip():
            print("Usage: %griffin <your question>")
            return
        
        response = self._call_llm_api(line)
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            # Only print the content directly to ensure it's visible in the console
            # We're not using display(Markdown(content)) to avoid showing the Markdown object
            print("\n" + content + "\n")
        elif 'error' in response:
            print(f"Error: {response['error']}")
        else:
            print(f"Unexpected response format: {response}")
    
    @cell_magic
    def griffin_cell(self, line, cell):
        """
        Send a multi-line query to the LLM API and display the response.
        
        Usage:
            %%griffin_cell
            What is the capital of France?
            And what is its population?
        """
        if not cell.strip():
            print("Usage: %%griffin\\n<your multi-line question>")
            return
        
        # If line is provided, use it as a system prompt
        system_prompt = line.strip() if line.strip() else "You are a helpful assistant."
        
        response = self._call_llm_api(cell, system_prompt)
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            # Only print the content directly to ensure it's visible in the console
            # We're not using display(Markdown(content)) to avoid showing the Markdown object
            print("\n" + content + "\n")
        elif 'error' in response:
            print(f"Error: {response['error']}")
        else:
            print(f"Unexpected response format: {response}")
    
    def _call_llm_api(self, question, system_prompt="You are a helpful assistant."):
        """Call the ArliAI API with the given question."""
        url = "https://api.arliai.com/v1/chat/completions"
        
        payload = json.dumps({
            "model": "Mistral-Nemo-12B-Instruct-2407",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            "repetition_penalty": 1.1,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 1024,
            "stream": False
        })
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {ARLIAI_API_KEY}"
        }
        
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse API response"}


def load_ipython_extension(ipython):
    """
    Register the magic when the extension is loaded.
    """
    ipython.register_magics(GriffinLLMMagics)
    print("Griffin LLM magic commands loaded. Use %griffin or %%griffin_cell to query the LLM.")
