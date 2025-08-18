import argparse
import os
import re
import subprocess
import sys
import time
from colorama import Fore, Style, init
from ddp_config import create_xml_5_1, create_xml_5_1_atmos, create_xml_7_1_atmos

init(autoreset=True)

# --- Helper functions ---
def check_executable(filename, display_name):
    path = os.path.join(os.getcwd(), filename)
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Verifying presence of {display_name}...")
    if not os.path.isfile(path):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Required tool not found: {filename}")
        sys.exit(1)
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Found {display_name} at: {path}")
    return path

def run_dee(xml_path, output_path="."):
    def format_time(seconds):
        return time.strftime("%H:%M:%S", time.gmtime(int(seconds)))

    def calculate_remaining_time(elapsed_time, progress):
        if progress == 0:
            return 0
        total_time = elapsed_time / (progress / 100)
        return int(total_time - elapsed_time)

    def print_progress_bar(progress, elapsed_time=0, remaining_time=0, length=40):
        filled_length = int(length * progress // 100)
        bar = '■' * filled_length + '-' * (length - filled_length)
        sys.stdout.write(
            f"\r[{bar}] {progress:.1f}% "
            f"(elapsed: {format_time(elapsed_time)}, remaining: {format_time(remaining_time)})"
        )
        sys.stdout.flush()

    xml_full_path = os.path.join(output_path, xml_path) if not os.path.isabs(xml_path) else xml_path
    command = ['dee.exe', '-x', xml_full_path]
    start_time = time.time()
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            match = re.search(r'Overall progress: (\d+\.\d+)', line)
            if match:
                progress = float(match.group(1))
                elapsed_time = time.time() - start_time
                remaining_time = calculate_remaining_time(elapsed_time, progress)
                print_progress_bar(progress, elapsed_time=elapsed_time, remaining_time=remaining_time)

        process.wait()
        bar = '■' * 40
        elapsed_time = time.time() - start_time
        sys.stdout.write(
            f"\r[{bar}] 100.0% (elapsed: {format_time(elapsed_time)}, remaining: 00:00:00)\n"
        )
        sys.stdout.flush()

    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to run dee.exe: {e}")
    finally:
        try:
            process.terminate()
        except:
            pass

# --- Argument parser ---
parser = argparse.ArgumentParser(description="Decode TrueHD and produce DDP outputs, with Dolby Atmos support")
parser.add_argument("-i", "--input", required=True, help="Path to the input TrueHD (.thd) file")  # Input file
parser.add_argument("-bd", "--bitrate-ddp", type=int, choices=[256, 384, 448, 640, 1024], default=1024, help="Set bitrate for DDP tracks (options: 256, 384, 448, 640, 1024; default: 1024)")  # DDP bitrate
parser.add_argument("-ba", "--bitrate-atmos-5-1", type=int, choices=[640, 768, 1024], default=1024, help="Set bitrate for Dolby Atmos 5.1 tracks (options: 640, 768, 1024; default: 768)")  # Atmos 5.1 bitrate
parser.add_argument("-b7", "--bitrate-atmos-7-1", type=int, choices=[1152, 1280, 1536, 1664], default=1536, help="Set bitrate for Dolby Atmos 7.1 tracks (options: 1152, 1280, 1536, 1664; default: 1536)")  # Atmos 7.1 bitrate
parser.add_argument("-w", "--warp-mode", choices=["normal", "warping", "prologiciix", "loro"], default="normal", help="Set the warp mode for decoding TrueHD (normal=Direct render, warping=Direct render with room balance, prologiciix=Dolby Pro Logic IIx, loro=Standard Lo/Ro)")  # Warp mode
args = parser.parse_args()

# --- Resolve input and output paths ---
input_file = os.path.abspath(args.input)
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Input file resolved: {input_file}")
if not os.path.isfile(input_file):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Input file does not exist: {input_file}")
    sys.exit(1)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "ddp_encode")
os.makedirs(output_path, exist_ok=True)
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Output directory: {output_path}")

# --- Check TrueHDD executable ---
truehdd_path = check_executable("truehdd.exe", "TrueHDD Decoder")

# --- Analyze TrueHD stream ---
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Running info command to analyze TrueHD stream...\n")
info_cmd = [truehdd_path, "info", input_file]

try:
    completed_process = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
    info_output = completed_process.stdout

    atmos_flag = None
    for line in info_output.splitlines():
        if "Dolby Atmos" in line:
            parts = line.split()
            atmos_flag = parts[-1].lower() if parts else None
            break

    if atmos_flag == "true":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos detected in the TrueHD stream.")
    elif atmos_flag == "false":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos not present in the TrueHD stream.")
    else:
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos information not found.")

except subprocess.CalledProcessError as e:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to run info command: {e}")
    sys.exit(1)

# --- Print selected settings ---
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Selected bitrates and warp mode:")
print(f"  5.1 bitrate: {args.bitrate_atmos_5_1 if atmos_flag=='true' else args.bitrate_ddp} kbps")
if atmos_flag == "true":
    print(f"  7.1 bitrate: {args.bitrate_atmos_7_1} kbps")
    print(f"  Warp mode: {args.warp_mode}")

# --- Build TrueHDD decode command ---
command = [truehdd_path, "decode", "--progress", input_file, "--output-path", output_path]

if atmos_flag == "true":
    command.extend(["--warp-mode", args.warp_mode])
else:
    command.extend(["--format", "pcm"])

# --- Execute decoding ---
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Launching decoding process...\n")
result = subprocess.run(command)
if result.returncode != 0:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding process failed.")
    sys.exit(1)

# --- Utility to build file paths ---
def path(filename):
    return os.path.join(output_path, filename)

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Decoding completed. Organizing files...\n")

# --- Organize decoded files ---
decoded_audio_file = None
decoded_atmos_file = None
decoded_mp4_file_5_1 = None
decoded_mp4_file_7_1 = None

for file in os.listdir(script_dir):
    file_path = os.path.join(script_dir, file)
    lower_file = file.lower()
    if os.path.commonpath([file_path, output_path]) == output_path:
        continue

    if lower_file.endswith(".pcm"):
        new_name = f"ddp_encode{os.path.splitext(file)[1]}"
        target_path = path(new_name)
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(file_path, target_path)
        decoded_audio_file = new_name
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Moved CAF to: {target_path}")

    elif lower_file.endswith((".atmos", ".atmos.metadata", ".atmos.audio")):
        if ".atmos" in lower_file:
            suffix = lower_file.split("atmos", 1)[1]
            new_name = f"ddp_encode.atmos{suffix}"
        else:
            new_name = "ddp_encode.atmos"
        target_path = path(new_name)
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(file_path, target_path)
        if new_name == "ddp_encode.atmos":
            decoded_atmos_file = new_name
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Moved ATMOS file to: {target_path}")

# --- Generate XMLs and run dee ---
input_base_filename = os.path.splitext(os.path.basename(input_file))[0]

if atmos_flag == "true":
    bitrate_5_1 = args.bitrate_atmos_5_1
    bitrate_7_1 = args.bitrate_atmos_7_1
    decoded_mp4_file_5_1 = "ddp_encode_atmos_5_1.mp4"
    decoded_mp4_file_7_1 = "ddp_encode_atmos_7_1.mp4"
    xml_filename_5_1 = "ddp_encode_atmos_5_1.xml"
    xml_filename_7_1 = "ddp_encode_atmos_7_1.xml"

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Generating 5.1 and 7.1 Atmos XMLs...")

    create_xml_5_1_atmos(output_path, decoded_atmos_file, decoded_mp4_file_5_1, bitrate_5_1, xml_filename_5_1)
    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Created: {xml_filename_5_1}")
    run_dee(xml_filename_5_1, output_path=output_path)
    os.rename(path("ddp_encode_atmos_5_1.mp4"), path(f"{input_base_filename}_atmos_5_1.mp4"))

    create_xml_7_1_atmos(output_path, decoded_atmos_file, decoded_mp4_file_7_1, bitrate_7_1, xml_filename_7_1)
    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Created: {xml_filename_7_1}")
    run_dee(xml_filename_7_1, output_path=output_path)
    os.rename(path("ddp_encode_atmos_7_1.mp4"), path(f"{input_base_filename}_atmos_7_1.mp4"))

    # Cleanup
    for file in os.listdir(output_path):
        if file.endswith((".atmos", ".atmos.metadata", ".atmos.audio")):
            os.remove(path(file))
    os.remove(path(xml_filename_5_1))
    os.remove(path(xml_filename_7_1))

else:
    bitrate_5_1 = args.bitrate_ddp
    decoded_mp4_file_5_1 = "ddp_encode_5_1.mp4"
    xml_filename_5_1 = "ddp_encode_5_1.xml"

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Generating 5.1 DDP XML only...")

    create_xml_5_1(output_path, decoded_audio_file, decoded_mp4_file_5_1, bitrate_5_1, xml_filename_5_1)
    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Created: {xml_filename_5_1}")
    run_dee(xml_filename_5_1, output_path=output_path)
    os.rename(path("ddp_encode_5_1.mp4"), path(f"{input_base_filename}_5_1.mp4"))

    # Cleanup
    for file in os.listdir(output_path):
        if file.endswith(".pcm"):
            os.remove(path(file))
    os.remove(path(xml_filename_5_1))