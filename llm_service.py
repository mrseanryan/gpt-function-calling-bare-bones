import random
import boto3
from botocore.exceptions import EventStreamError
import json

from cornsnake import util_color, util_print, util_wait

import config

def _build_prompt(application_name, functions, user_prompt):
    return f"""
Human: Take the user prompt and generate a list of functions for the '{application_name}' application to perform.
User prompt: '{user_prompt}'.
The output MUST be as *valid* JSON only.

DO NOT write any text outside the ```json``` block.

FUNCTIONS:
```
{functions}
```

PROCESS:

1. Take the user prompt use the given functions to generate appropriate function calls.
2. Add appropriate values to match the function parameters.
3. Output the function calls in JSON format.

EXAMPLE OUTPUT: ```json
{{
    "functionCalls": [
        {{ "name":"my-function",
         "parameters": [ {{"name": "p1", "value": 5 }} ]
         }}
    ],
    "explanation": "These actions will ..."
}}
```

Assistant:
```json
"""

def _prompt_llm(prompt):
    generated_text = ""

    util_print.print_section("RESPONSE")

    body = json.dumps({
        "prompt": prompt,
         "max_tokens_to_sample": config.MAX_OUTPUT_TOKENS,
         "temperature": config.TEMPERATURE,
         "top_k": 250,
         "top_p": 1,
         "stop_sequences": ["\\n\\nHuman:"],
         "anthropic_version": "bedrock-2023-05-31"
    })

    session = boto3.Session(region_name=config.REGION_NAME, profile_name=config.AWS_PROFILE_NAME)
    brt = session.client('bedrock-runtime')

    response = brt.invoke_model_with_response_stream(
        modelId=config.ANTHROPIC_CLAUDE_MODEL,
        body=body
    )

    generated_text = ""

    stream = response.get('body')
    if stream:
        for event in stream:
            chunk = event.get('chunk')
            if chunk:
                rsp = json.loads(chunk.get('bytes').decode())
                generated_line_part = rsp['completion']
                generated_text += generated_line_part
                print(generated_line_part, end='')

    def _clean_text__assuming_gave_json_start_at_end_of_prompt(text):  # assumes prompt ended with ```json
        PRELIM_IF_CHAT = "```json"
        if PRELIM_IF_CHAT in text:
            text = text.split(PRELIM_IF_CHAT)[1]
        END = "```"
        if END in text:
            text = text.split(END)[0]
        return text

    generated_text = _clean_text__assuming_gave_json_start_at_end_of_prompt(generated_text)
    return generated_text


def _prompt_llm_with_retry_if_throttled(active_prompt):
    retries = 3
    while retries > 0:
        retries -= 1
        try:
            return _prompt_llm(active_prompt)
        except EventStreamError as ese:
            if "Too many requests" in str(ese) and retries > 0:
                print("  (throtttled) retrying...")
                util_wait.wait_seconds(random.randint(3, 10))
            else:
                raise


def _generate(application_name, functions, user_prompt, history_text):
    util_print.print_section(f"PROMPT")

    active_prompt = ""
    if not history_text:
        active_prompt = _build_prompt(application_name, functions, user_prompt)
        if config.IS_DEBUG:
            util_print.print_result(active_prompt)
        history_text = active_prompt
    else:
        history_text += "\n\nHuman: " + user_prompt + "\n\nAssistant:\n"
        active_prompt = history_text

    response = _prompt_llm_with_retry_if_throttled(active_prompt)

    util_print.print_with_color(f"\n\nUSER >>" + user_prompt, util_color.QUESTION_COLOR)
    util_print.print_result(f"\nPOST PROC >>" + response)

    history_text += response

    return (response, history_text)

def _user_wants_to_exit(user_prompt):
    BYE = ['quit', 'exit', 'close']
    for bye in BYE:
        if bye in user_prompt:
            return True
    return False

def call_llm(application_name, functions, user_prompt, is_chat):
    generated_text = ""
    if not is_chat:
        (generated_text, new_history) = _generate(application_name, functions, user_prompt, "")
    else:
        history_text = ""
        last_generated = ""
        while((user_prompt)):
            print(">> USER: " + (user_prompt))
            (generated_text, new_history) = _generate(application_name, functions, user_prompt, history_text)
            history_text += new_history
            if _user_wants_to_exit((user_prompt)):
                break
            last_generated = generated_text
            (user_prompt) = input("\n\nHow can I help? >>")
        generated_text = last_generated  # we don't want to capture the 'bye' text of the LLM

    return generated_text
