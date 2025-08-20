import os
import sys
import re
import time
import argparse
import subprocess
import platform
from colorama import Fore, Style, init
from ddp_config import create_xml_5_1, create_xml_5_1_atmos, create_xml_7_1_atmos

init(autoreset=True)

# -------------------- Utilities -------------------- #

def get_executable_name(name):
    return f"{name}.exe" if platform.system().lower() == "windows" else name

def build_path(filename):
    return os.path.join(output_path, filename)

def check_tool(executable, display_name):
    location = os.path.join(os.getcwd(), executable)
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Checking for {display_name}...")
    if not os.path.isfile(location):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Missing tool: {executable}")
        sys.exit(1)
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Found {display_name}: {executable}")
    return location

def remove_files(folder, extensions):
    for f in os.listdir(folder):
        if f.endswith(extensions):
            os.remove(build_path(f))

def run_dee(xml_file, output_path="."):
    def format_time(seconds):
        return time.strftime("%H:%M:%S", time.gmtime(int(seconds)))

    def estimate_remaining(elapsed, progress):
        if progress == 0:
            return 0
        total = elapsed / (progress / 100)
        return int(total - elapsed)

    def show_progress(progress, elapsed=0, remaining=0, length=40):
        filled = int(length * progress // 100)
        bar = '■' * filled + '-' * (length - filled)
        sys.stdout.write(
            f"\r[{bar}] {progress:.1f}% "
            f"(elapsed: {format_time(elapsed)}, remaining: {format_time(remaining)})"
        )
        sys.stdout.flush()

    xml_full = os.path.join(output_path, xml_file) if not os.path.isabs(xml_file) else xml_file
    dee_exec = get_executable_name("dee")
    command = [dee_exec, "-x", xml_full]

    start = time.time()
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            match = re.search(r"Overall progress: (\d+\.\d+)", line)
            if match:
                progress = float(match.group(1))
                elapsed = time.time() - start
                remaining = estimate_remaining(elapsed, progress)
                show_progress(progress, elapsed, remaining)

        process.wait()
        bar = '■' * 40
        elapsed = time.time() - start
        sys.stdout.write(f"\r[{bar}] 100.0% (elapsed: {format_time(elapsed)}, remaining: 00:00:00)\n")
        sys.stdout.flush()

    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to run {dee_exec}: {e}")
    finally:
        try:
            process.terminate()
        except:
            pass

# -------------------- Arguments -------------------- #

parser = argparse.ArgumentParser(description="TrueHD to DDP encoder with Atmos support")
parser.add_argument("-i", "--input", required=True, help="Input TrueHD (.thd) file path")
parser.add_argument("-bd", "--bitrate-ddp", type=int, choices=[256, 384, 448, 640, 1024], default=1024, help="Bitrate for DDP 5.1 (default: 1024)")
parser.add_argument("-ba", "--bitrate-atmos-5-1", type=int, choices=[384, 448, 576, 640, 768, 1024], default=1024, help="Bitrate for Atmos 5.1 (default: 1024)")
parser.add_argument("-b7", "--bitrate-atmos-7-1", type=int, choices=[1152, 1280, 1536, 1664], default=1536, help="Bitrate for Atmos 7.1 (default: 1536)")
parser.add_argument("-am", "--atmos-mode", choices=["5.1", "7.1", "both"], default="both", help="Select Atmos output mode")
parser.add_argument("-w", "--warp-mode", choices=["normal", "warping", "prologiciix", "loro"], default="normal", help="Warp mode (default: normal)")
parser.add_argument("-bc", "--bed-conform", action="store_true", default=True, help="Enable bed conform for Atmos (default: enabled)")
args = parser.parse_args()

# -------------------- Input Validation -------------------- #

input_file = os.path.abspath(args.input)
input_name = os.path.basename(input_file)

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Input file: {input_name}")
if not os.path.isfile(input_file):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File does not exist: {input_name}")
    sys.exit(1)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "ddp_encode")
os.makedirs(output_path, exist_ok=True)
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Output directory: {os.path.basename(output_path)}")

truehdd_exec = get_executable_name("truehdd")
truehdd_path = check_tool(truehdd_exec, "TrueHDD Decoder")

# -------------------- Analyze Stream -------------------- #

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Analyzing TrueHD stream...\n")
atmos_flag = None

try:
    result = subprocess.run([truehdd_path, "info", input_file], capture_output=True, text=True, check=True)
    for line in result.stdout.splitlines():
        if "Dolby Atmos" in line:
            atmos_flag = line.split()[-1].lower()
            break

    if atmos_flag == "true":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos detected.")
    elif atmos_flag == "false":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos not present.")
    else:
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Atmos information unavailable.")

except subprocess.CalledProcessError as e:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Info command failed: {e}")
    sys.exit(1)

# -------------------- Settings -------------------- #

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Selected bitrates and warp mode:")
if atmos_flag != "true":
    print(f"  DDP 5.1 bitrate: {args.bitrate_ddp} kbps")
else:
    if args.atmos_mode in ["5.1", "both"]:
        print(f"  Atmos 5.1 bitrate: {args.bitrate_atmos_5_1} kbps")
    if args.atmos_mode in ["7.1", "both"]:
        print(f"  Atmos 7.1 bitrate: {args.bitrate_atmos_7_1} kbps")
print(f"  Warp mode: {args.warp_mode}")

# -------------------- Decoding -------------------- #

decode_cmd = [
    truehdd_exec,
    "decode",
    "--loglevel", "off",
    "--progress", input_file,
    "--output-path", output_path
]
if atmos_flag == "true":
    decode_cmd.extend(["--warp-mode", args.warp_mode])
    if args.bed_conform:
        decode_cmd.append("--bed-conform")
else:
    decode_cmd.extend(["--format", "pcm"])

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting decoding...\n")
decode_result = subprocess.run(decode_cmd)
if decode_result.returncode != 0:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding failed.")
    sys.exit(1)

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Decoding completed. Organizing files...\n")

# -------------------- File Organization -------------------- #

decoded_audio_file = None
decoded_atmos_file = None
decoded_mp4_file_5_1 = None
decoded_mp4_file_7_1 = None

for f in os.listdir(script_dir):
    f_path = os.path.join(script_dir, f)
    f_lower = f.lower()
    if os.path.commonpath([f_path, output_path]) == output_path:
        continue

    if f_lower.endswith(".pcm"):
        new_name = "ddp_encode.pcm"
        target = build_path(new_name)
        if os.path.exists(target):
            os.remove(target)
        os.rename(f_path, target)
        decoded_audio_file = new_name
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} PCM moved to {os.path.join(os.path.basename(output_path), new_name)}")

    elif f_lower.endswith((".atmos", ".atmos.metadata", ".atmos.audio")):
        if ".atmos" in f_lower:
            suffix = f_lower.split("atmos", 1)[1]
            new_name = f"ddp_encode.atmos{suffix}"
        else:
            new_name = "ddp_encode.atmos"
        target = build_path(new_name)
        if os.path.exists(target):
            os.remove(target)
        os.rename(f_path, target)
        if new_name == "ddp_encode.atmos":
            decoded_atmos_file = new_name
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Atmos file moved to {os.path.join(os.path.basename(output_path), new_name)}")

# -------------------- Encoding -------------------- #

base_name = os.path.splitext(os.path.basename(input_file))[0]

if atmos_flag == "true":
    cleanup_targets = []

    if args.atmos_mode in ["5.1", "both"]:
        decoded_mp4_file_5_1 = "ddp_encode_atmos_5_1.mp4"
        xml_5_1 = "ddp_encode_atmos_5_1.xml"
        cleanup_targets.append(xml_5_1)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 5.1 XML...")
        create_xml_5_1_atmos(output_path, decoded_atmos_file, decoded_mp4_file_5_1, args.bitrate_atmos_5_1, xml_5_1)
        run_dee(xml_5_1, output_path=output_path)
        os.rename(build_path(decoded_mp4_file_5_1), build_path(f"{base_name}_atmos_5_1.mp4"))

    if args.atmos_mode in ["7.1", "both"]:
        decoded_mp4_file_7_1 = "ddp_encode_atmos_7_1.mp4"
        xml_7_1 = "ddp_encode_atmos_7_1.xml"
        cleanup_targets.append(xml_7_1)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 7.1 XML...")
        create_xml_7_1_atmos(output_path, decoded_atmos_file, decoded_mp4_file_7_1, args.bitrate_atmos_7_1, xml_7_1)
        run_dee(xml_7_1, output_path=output_path)
        os.rename(build_path(decoded_mp4_file_7_1), build_path(f"{base_name}_atmos_7_1.mp4"))

    remove_files(output_path, (".atmos", ".atmos.metadata", ".atmos.audio"))
    for x in cleanup_targets:
        os.remove(build_path(x))

else:
    decoded_mp4_file_5_1 = "ddp_encode_5_1.mp4"
    xml_5_1 = "ddp_encode_5_1.xml"
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating DDP 5.1 XML...")
    create_xml_5_1(output_path, decoded_audio_file, decoded_mp4_file_5_1, args.bitrate_ddp, xml_5_1)
    run_dee(xml_5_1, output_path=output_path)
    os.rename(build_path(decoded_mp4_file_5_1), build_path(f"{base_name}_5_1.mp4"))
    remove_files(output_path, (".pcm",))
    os.remove(build_path(xml_5_1))