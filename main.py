import sys

from cornsnake import util_json, util_print, util_log

import llm_service


def print_usage():
    util_print.print_section(f"function-caller")
    print(f"USAGE: <path to functions JSON file> <user prompt> [--chat]")


def validate_usage():
    path_to_functions_json_file = ""
    user_prompt = ""
    is_chat = False
    len_args = len(sys.argv)
    is_valid_args = False
    if len_args == 3 or len_args == 4:
        path_to_functions_json_file = sys.argv[1]
        user_prompt = sys.argv[2]
        if len_args == 4:
            if sys.argv[3] == "--chat":
                is_chat = True
                is_valid_args = True
        else:
            is_valid_args = True
    if not is_valid_args:
        print_usage()
        sys.exit(44)

    return (path_to_functions_json_file, user_prompt, is_chat)

def _read_from_functions_file(path_to_functions_json_file):
    json_data = util_json.read_from_json_file(path_to_functions_json_file)
    return (json_data['application'], json_data['functions'])

if __name__ == "__main__":
    (path_to_functions_json_file, user_prompt, is_chat) = validate_usage()
    try:
        (application_name, functions) = _read_from_functions_file(path_to_functions_json_file)
        result = llm_service.call_llm(application_name, functions, user_prompt, is_chat)
        util_print.print_result(f"Final result:")
        util_print.print_result(result)
    except Exception as e:
        util_log.log_exception(e)
        exit_code = 43
