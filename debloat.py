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

disabled_packages = []

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

def package_check(pkg):
    return command(['adb', 'shell', f'pm list packages -e | grep "^package:{pkg}$"']) != ''

def disable_package(pkg):
    global disabled_packages

    if package_check(pkg) == False:
        log(f'Skipping package: {pkg}')
        return
    
    log(f'Disabling package: {pkg}...')
    command(['adb', 'shell', f'pm disable-user {pkg}'])

    disabled_packages.append(pkg)

def disable_packages(pkgs):
    for pkg in pkgs:
        disable_package(pkg)

def prepare_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)

def enumerate_packages():
    log('Enumerating packages...')
    packages = []
    for list in glob.glob(f'{DIR_BLOATLIST}/**/*.{LIST_TYPE}', recursive = True):
        log(f'Discovered list: {list}')
        with open(list) as file:
            for line in file.readlines():
                stripped_line = line.rstrip('\r\n')
                if stripped_line == '':             # Ignore whitespace
                    continue
                if stripped_line.startswith('#'):   # Ignore comments
                    continue

                log(f'Found bloatware: {stripped_line}')
                packages.append(stripped_line)
    return packages

def generate_disable_list():
    if disabled_packages == []:
        return

    with open(FILE_DISABLED, 'w') as file:
        file.writelines(disabled_packages)
    log(f'Logged disabled packages: {FILE_DISABLED}')

def main():
    adb_check()
    prepare_dir(DIR_BLOATLIST)
    pkgs = enumerate_packages()
    wait_for_device()
    disable_packages(pkgs)
    generate_disable_list()

main()