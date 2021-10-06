import os
import glob
import subprocess
import shutil

DIR_BLOATLIST =     'bloatlists'
FILE_DISABLED =     'disabled.txt'
LIST_TYPE =         'txt'
LOG_TAG =           '[*]'
ERR_TAG =           '[!]'

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

bloat_packages = []
disabled_packages = []
enabled_packages = []

def log(str):
    print(f'{LOG_TAG} {str}')

def err(str):
    print(f'{ERR_TAG} {str}')
    exit(1)

def command(str):
    out = subprocess.run(str, stdout = subprocess.PIPE).stdout
    return out.decode()

def adb_check():
    if shutil.which('adb') is None:
        err('adb binary not found!')

def wait_for_device():
    log('Waiting for device to be detected...')
    command(['adb', 'wait-for-device'])
    log('Device located')

def disable_package(pkg):
    if pkg in disabled_packages:
        log(f'Skipping package: {pkg}...')
        return

    log(f'Uninstall package: {pkg}...')
    command(['adb', 'shell', f'pm uninstall {pkg}'])

    log(f'Disabling package: {pkg}...')
    command(['adb', 'shell', f'pm disable-user {pkg}'])

def clear_package(pkg):
    log(f'Stopping package: {pkg}...')
    command(['adb', 'shell', f'am force-stop {pkg}'])

    log(f'Clearing package: {pkg}...')
    command(['adb', 'shell', f'pm clear {pkg}'])

    log(f'Disabling package again: {pkg}...')
    command(['adb', 'shell', f'pm disable-user {pkg}'])

def disable_bloatware():
    for pkg in bloat_packages:
        disable_package(pkg)

    log(f'Rebooting...')
    command(['adb', 'reboot'])
    wait_for_device()

    for pkg in bloat_packages:
        clear_package(pkg)

def prepare_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)

def enumerate_enabled_packages():
    global enabled_packages

    log('Enumerating enabled packages...')
    enabled_packages = command(['adb', 'shell', 'pm list packages -e']) \
        .replace('package:', '') \
        .strip() \
        .split('\n')
    
def enumerate_disabled_packages():
    global disabled_packages

    log('Enumerating disabled packages...')
    disabled_packages = command(['adb', 'shell', 'pm list packages -d']) \
        .replace('package:', '') \
        .strip() \
        .split('\n')

def enumerate_bloat_lists():
    global bloat_packages
    
    log('Enumerating disabled packages...')
    for list in glob.glob(f'{DIR_BLOATLIST}/**/*.{LIST_TYPE}', recursive = True):
        log(f'Discovered list: {list}')
        with open(list) as file:
            for line in file.readlines():
                stripped_line = line.rstrip('\r\n')
                if stripped_line == '':             # Ignore whitespace
                    continue
                if stripped_line.startswith('#'):   # Ignore comments
                    continue
                if stripped_line in bloat_packages:
                    continue
                if stripped_line not in enabled_packages and stripped_line not in disabled_packages:
                    continue

                log(f'Found bloatware: {stripped_line}')
                bloat_packages.append(stripped_line)

def generate_disable_list():
    if disabled_packages == []:
        return

    with open(FILE_DISABLED, 'w') as file:
        file.writelines(disabled_packages)
    log(f'Logged disabled packages: {FILE_DISABLED}')

def main():
    adb_check()
    prepare_dir(DIR_BLOATLIST)
    wait_for_device()
    enumerate_disabled_packages()
    enumerate_enabled_packages()
    enumerate_bloat_lists()
    disable_bloatware()
    generate_disable_list()

main()