import json
import os
import sys
import paramiko

APP_NAME = "FastPush"
WORKING_DIR = os.getcwd()

def connect(host, user, password, gateway=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sock = None
    if gateway:
        gw_client = connect(gateway, user, password)
        sock = gw_client.get_transport().open_channel(
            'direct-tcpip', (host, 22), ('', 0)
        )
    kwargs = dict(
        hostname=host,
        port=22,
        username=user,
        password=password,
        sock=sock,
    )
    client.connect(**kwargs)
    return client

def main():
    try:
        with open("./config.json", encoding="utf8") as json_file:
            obj = json.load(json_file)
    except Exception as e:
        print(f"Could not import {APP_NAME}'s Configuration file. Please check there is a config.json file in the current directory and try again.")
        print(e)
        sys.exit(1)
    
    hosts = obj["hosts"]
    sim_files = obj["worsecrossbars_sims"]
    
    if len(hosts) != len(sim_files):
        print(f"The number of hosts provided does not match the number of simulation files provided. Check config.json and try again.")
        sys.exit(1)
    
    user = input("Please enter your username: ")
    password = input("Please enter your password: ")
    gateway = obj["gateway"] if "gateway" in obj.keys() else None

    for index, host in enumerate(hosts.keys()):

        try:
            client = connect(host, user, password, gateway)
        except Exception as e:
            print(f"The host {host} cannot be reached. The error was {e}. Please try again.")
            print("Exiting...")
            sys.exit(1)
        
        horovod_cmd = f"horovodrun -np {hosts[host]} -H localhost:{hosts[host]} python -m worsecrossbars.compute_horovod {sim_files[index]}"

        _, _, _ = client.exec_command(f"mkdir ~/{APP_NAME}") 
        ftp_client = client.open_sftp()
        ftp_client.put(f"{WORKING_DIR}/{sim_files[index]}", f"{sim_files[index]}")
        ftp_client.close()
        _, _, _ = client.exec_command(f"mv {sim_files[index]} ~/{APP_NAME}/{sim_files[index]}")
        stdin, stdout, stderr = client.exec_command(f"cd ~/{APP_NAME} && {horovod_cmd} & ")
        print(stdout.readlines())
        client.close()


if __name__ == "__main__":
    main()