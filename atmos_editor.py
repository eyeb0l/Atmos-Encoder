import os
from colorama import Fore, Style, init
from ruamel.yaml import YAML

init(autoreset=True)

def process_atmos_file(input_file):
    base_name, ext = os.path.splitext(input_file)
    output_file = f"{base_name}_temp{ext}"

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    yaml.boolean_representation = ['false', 'true']

    with open(input_file, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    presentations = data.get("presentations", [])
    if not presentations:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No presentations found in the file.")
        return False

    presentation = presentations[0]
    if presentation.get("warpMode") != "normal":
        print(f"{Fore.BLUE}[DEBUG]{Style.RESET_ALL} warpMode is not 'normal'. Proceeding with edit...")
        if "offset" in presentation:
            if isinstance(presentation["offset"], float) and presentation["offset"].is_integer():
                presentation["offset"] = f"{int(presentation['offset'])}.0"

        original_tool = presentation.get("creationTool", "")
        presentation["creationTool"] = f"{original_tool} Modified by DRX-Lab"
        presentation["warpMode"] = "normal" 

        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} File edited successfully (metadata and audio unchanged).")

        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        os.remove(input_file)
        os.rename(output_file, input_file)
        print(f"{Fore.CYAN}[SAVED]{Style.RESET_ALL} Changes applied. '{input_file}' has been updated.")
        print(f"{Fore.MAGENTA}[RESULT]{Style.RESET_ALL} The file was edited.")
        return True

    else:
        print(f"{Fore.BLUE}[DEBUG]{Style.RESET_ALL} warpMode is already 'normal'. No edit will be performed.")
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} No changes made. warpMode is already 'normal'.")
        print(f"{Fore.MAGENTA}[RESULT]{Style.RESET_ALL} The file was not edited.")
        return False