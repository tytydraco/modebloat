import argparse
import os
import glob
import subprocess
import shutil
import time

DIR_BLOATLIST =     'bloatlists'
FILE_DISABLED =     'disabled.txt'
LIST_TYPE =         'txt'
DBG_TAG =           '[*]'
ERR_TAG =           '[!]'

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

bloat_packages = set()
disabled_packages = []
enabled_packages = []

def dbg(str):
    if args.verbose:
        print(f'{DBG_TAG} {str}')

def err(str):
    print(f'{ERR_TAG} {str}')
    exit(1)

def parse_args():
    global args

    parser = argparse.ArgumentParser(description='A modular Android debloating tool')
    parser.add_argument('-v', '--verbose', action='store_true', help='Log in verbose mode')
    parser.add_argument('-e', '--enum', action='store_true', help='Enumerate matching bloatware packages without making any changes')
    parser.add_argument('-i', '--interactive', action='store_true', help='Decide what to do with each bloat package')
    parser.add_argument('-n', '--noclear', action='store_true', help='Do not reboot and clear package data after')
    parser.add_argument('-N', '--nolog', action='store_true', help='Do not log disabled packages to a file')
    parser.add_argument('-c', '--clear', action='store_true', help='Clear disabled packages right away, skips disabling step')
    parser.add_argument('-f', '--force', action='store_true', help='Perform actions on all found packages, even already disabled ones')

    args = parser.parse_args()

def command(str):
    out = subprocess.run(str, stdout = subprocess.PIPE).stdout
    return out.decode().strip()

def adb_check():
    if shutil.which('adb') is None:
        err('adb binary not found!')

def wait_for_device():
    dbg('Waiting for device to be detected...')
    command(['adb', 'wait-for-device'])
    dbg('Device located')

    dbg('Waiting for boot to complete...')
    while command(['adb', 'shell', 'getprop', 'sys.boot_completed']) != '1':
        time.sleep(1)
    dbg('Boot completed')

def disable_package(pkg):
    if pkg in disabled_packages:
        dbg(f'Skipping package: {pkg}...')
        return

    if args.interactive:
        decision = input(f'INTERACTIVE [y/n]: {pkg}: ')
        if decision.lower() != 'y':
            return

    dbg(f'Uninstall package: {pkg}...')
    command(['adb', 'shell', f'pm uninstall {pkg}'])

    dbg(f'Disabling package: {pkg}...')
    command(['adb', 'shell', f'pm disable-user {pkg}'])

def clear_package(pkg):
    dbg(f'Stopping package: {pkg}...')
    command(['adb', 'shell', f'am force-stop {pkg}'])

    dbg(f'Clearing package: {pkg}...')
    command(['adb', 'shell', f'pm clear {pkg}'])

    dbg(f'Disabling package again: {pkg}...')
    command(['adb', 'shell', f'pm disable-user {pkg}'])

def disable_bloatware():
    if not args.clear:
        for pkg in bloat_packages:
            disable_package(pkg)

        if args.noclear:
            return

        dbg(f'Rebooting...')
        command(['adb', 'reboot'])
        wait_for_device()

    for pkg in bloat_packages:
        clear_package(pkg)

def prepare_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)

def enumerate_enabled_packages():
    global enabled_packages

    dbg('Enumerating enabled packages...')
    enabled_packages = command(['adb', 'shell', 'pm list packages -e']) \
        .replace('package:', '') \
        .strip() \
        .split('\n')
    
def enumerate_disabled_packages():
    global disabled_packages

    dbg('Enumerating disabled packages...')
    disabled_packages = command(['adb', 'shell', 'pm list packages -d']) \
        .replace('package:', '') \
        .strip() \
        .split('\n')

def enumerate_bloat_lists():
    global bloat_packages
    
    dbg('Enumerating bloat lists...')
    for list in glob.glob(f'{DIR_BLOATLIST}/**/*.{LIST_TYPE}', recursive = True):
        dbg(f'Discovered list: {list}')
        with open(list) as file:
            for line in file.readlines():
                stripped_line = line.strip()
                if stripped_line == '':             # Ignore whitespace
                    continue
                if stripped_line.startswith('#'):   # Ignore comments
                    continue
                if not args.force and stripped_line not in enabled_packages:
                    continue

                dbg(f'Found bloatware: {stripped_line}')
                bloat_packages.add(stripped_line)

def generate_disable_list():
    if disabled_packages == []:
        return

    with open(FILE_DISABLED, 'w') as file:
        file.write('\n'.join(disabled_packages))
    dbg(f'Logged disabled packages: {FILE_DISABLED}')

def main():
    parse_args()
    adb_check()
    prepare_dir(DIR_BLOATLIST)
    wait_for_device()
    enumerate_disabled_packages()
    enumerate_enabled_packages()
    enumerate_bloat_lists()

    if args.enum and bloat_packages != []:
        print('\n'.join(bloat_packages))
        exit()

    disable_bloatware()

    if not args.nolog:
        generate_disable_list()

main()
